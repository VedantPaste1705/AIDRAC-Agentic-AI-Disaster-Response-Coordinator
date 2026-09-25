import logging
import re
import asyncio
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.models.location import Location
from app.services.disaster_sources.base import AlertData

logger = logging.getLogger("aidrac.services.location_resolver")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.INFO)
    _sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_sh)
    logger.propagate = False

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "AIDRAC/1.0 (aidrac@example.com)"
NOMINATIM_TIMEOUT = 10.0
NOMINATIM_RATE_LIMIT_DELAY = 1.0

_INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
    "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    "andaman and nicobar islands", "chandigarh", "dadra and nagar haveli and daman and diu",
    "delhi", "jammu and kashmir", "ladakh", "lakshadweep", "puducherry"
}

_COMMON_ALIASES = {
    "pune": ["Poona"],
    "mumbai": ["Bombay"],
    "chennai": ["Madras"],
    "kolkata": ["Calcutta"],
    "bengaluru": ["Bangalore"],
    "kochi": ["Cochin"],
    "thiruvananthapuram": ["Trivandrum"],
    "guwahati": ["Gauhati"],
    "vijayawada": ["Bezwada"],
    "visakhapatnam": ["Vizag"],
}


@dataclass
class ResolvedLocation:
    name: str
    latitude: float
    longitude: float
    location_source: str
    location_type: str | None = None
    state: str | None = None
    district: str | None = None
    radius: float | None = None
    order: int = 0


def _normalize_name(name: str) -> str:
    """Normalize a location name for lookup."""
    if not name:
        return ""
    normalized = name.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized


def _extract_location_parts(area_desc: str) -> list[str]:
    """Extract individual location names from a CAP areaDesc string."""
    if not area_desc:
        return []

    parts = [p.strip() for p in area_desc.split(",")]
    cleaned_parts = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        part_lower = part.lower()

        for suffix in ["district", "division", "city", "municipal corporation", "taluk", "taluka", "block", "tehsil"]:
            if part_lower.endswith(f" {suffix}") or part_lower == suffix:
                part = part.rsplit(" ", 1)[0].strip()
                part_lower = part.lower()
                break

        if part_lower in _INDIAN_STATES or part_lower in {"india", "all", "entire", "whole", "nationwide"}:
            continue

        if part:
            cleaned_parts.append(part)

    return cleaned_parts


def _expand_with_aliases(name: str) -> list[str]:
    """Expand a location name with known aliases."""
    normalized = _normalize_name(name)
    results = [name]
    for canonical, aliases in _COMMON_ALIASES.items():
        if normalized == _normalize_name(canonical):
            results.extend(aliases)
        elif normalized in [_normalize_name(a) for a in aliases]:
            results.append(canonical)
    return results


class LocationResolver:
    def __init__(self):
        self._nominatim_last_call = 0.0
        self._nominatim_client: httpx.AsyncClient | None = None

    async def _get_nominatim_client(self) -> httpx.AsyncClient:
        if self._nominatim_client is None:
            self._nominatim_client = httpx.AsyncClient(
                timeout=NOMINATIM_TIMEOUT,
                headers={"User-Agent": NOMINATIM_USER_AGENT}
            )
        return self._nominatim_client

    async def close(self):
        if self._nominatim_client:
            await self._nominatim_client.aclose()
            self._nominatim_client = None

    async def resolve_from_polygon(self, polygons: list[str]) -> ResolvedLocation | None:
        """Derive centroid from first polygon."""
        if not polygons:
            return None
        try:
            coords_str = polygons[0].strip().replace(",", " ")
            parts = coords_str.split()
            if len(parts) < 6:
                return None
            lats = [float(parts[i]) for i in range(0, len(parts), 2)]
            lngs = [float(parts[i+1]) for i in range(0, len(parts), 2)]
            if not lats or not lngs:
                return None
            lat = sum(lats) / len(lats)
            lng = sum(lngs) / len(lngs)
            logger.info("Resolved polygon centroid: lat=%.4f, lng=%.4f", lat, lng)
            return ResolvedLocation(name="polygon_centroid", latitude=lat, longitude=lng, location_source="polygon", order=0)
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse polygon: %s", e)
            return None

    async def resolve_from_circle(self, circle: str) -> ResolvedLocation | None:
        """Parse circle center coordinates."""
        if not circle:
            return None
        try:
            parts = circle.strip().split()
            if len(parts) >= 3:
                lat = float(parts[0])
                lng = float(parts[1])
                radius = float(parts[2])
                logger.info("Resolved circle center: lat=%.4f, lng=%.4f, radius=%.1f", lat, lng, radius)
                return ResolvedLocation(name="circle_center", latitude=lat, longitude=lng, location_source="circle", radius=radius, order=0)
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse circle: %s", e)
        return None

    async def resolve_from_point(self, point: str) -> ResolvedLocation | None:
        """Parse point coordinates."""
        if not point:
            return None
        try:
            coords = point.strip().replace(",", " ").split()
            if len(coords) >= 2:
                lat = float(coords[0])
                lng = float(coords[1])
                logger.info("Resolved point: lat=%.4f, lng=%.4f", lat, lng)
                return ResolvedLocation(name="point", latitude=lat, longitude=lng, location_source="point", order=0)
        except (ValueError, IndexError) as e:
            logger.warning("Failed to parse point: %s", e)
        return None

    async def _resolve_single_location(
        self,
        db: AsyncSession,
        part: str,
        order: int
    ) -> ResolvedLocation | None:
        """Resolve a single location part using local DB then Nominatim."""
        for candidate in _expand_with_aliases(part):
            normalized = _normalize_name(candidate)
            result = await db.execute(
                select(Location).where(Location.normalized_name == normalized).limit(1)
            )
            location = result.scalar_one_or_none()
            if location:
                logger.info("Resolved '%s' via local DB: lat=%.4f, lng=%.4f", part, location.latitude, location.longitude)
                return ResolvedLocation(
                    name=part,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    location_source="local_database",
                    location_type=location.type,
                    state=location.state,
                    district=location.district,
                    order=order
                )

        # Fallback to Nominatim
        try:
            await self._respect_rate_limit()
            client = await self._get_nominatim_client()
            params = {
                "q": f"{part}, India",
                "format": "json",
                "limit": 1,
                "countrycodes": "in",
                "addressdetails": 1,
            }
            resp = await client.get(NOMINATIM_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                logger.info("Resolved '%s' via Nominatim: lat=%.4f, lng=%.4f", part, lat, lng)
                return ResolvedLocation(
                    name=part,
                    latitude=lat,
                    longitude=lng,
                    location_source="geocoder",
                    order=order
                )
        except Exception as e:
            logger.warning("Nominatim lookup failed for '%s': %s", part, e)

        return None

    async def resolve_all_locations(self, db: AsyncSession, alert_data: AlertData) -> list[ResolvedLocation]:
        """
        Resolve ALL locations for an alert following priority:
        1. Polygon (centroid) - single
        2. Circle (center) - single
        3. Point - single
        4. areaDesc -> resolve each part via local DB then Nominatim
        Returns list of ResolvedLocation (empty if none resolved)
        """
        locations: list[ResolvedLocation] = []

        # Priority 1: Polygon
        if alert_data.polygons:
            result = await self.resolve_from_polygon(alert_data.polygons)
            if result:
                locations.append(result)
                return locations

        # Priority 2: Circle
        if alert_data.circle:
            result = await self.resolve_from_circle(alert_data.circle)
            if result:
                locations.append(result)
                return locations

        # Priority 3: Point
        if alert_data.point:
            result = await self.resolve_from_point(alert_data.point)
            if result:
                locations.append(result)
                return locations

        # Priority 4: areaDesc - resolve each part
        if alert_data.area:
            location_parts = _extract_location_parts(alert_data.area)
            for order, part in enumerate(location_parts):
                result = await self._resolve_single_location(db, part, order)
                if result:
                    locations.append(result)

        if not locations:
            logger.info("Could not resolve any location for alert %s (area: %s)", alert_data.external_id, alert_data.area)

        return locations

    async def _respect_rate_limit(self):
        now = asyncio.get_event_loop().time()
        elapsed = now - self._nominatim_last_call
        if elapsed < NOMINATIM_RATE_LIMIT_DELAY:
            await asyncio.sleep(NOMINATIM_RATE_LIMIT_DELAY - elapsed)
        self._nominatim_last_call = asyncio.get_event_loop().time()

    # Backwards compatible method
    async def resolve(self, db: AsyncSession, alert_data: AlertData) -> tuple[float | None, float | None, float | None, str | None]:
        """
        Resolve primary location for backwards compatibility.
        Returns: (latitude, longitude, radius, location_source)
        """
        locations = await self.resolve_all_locations(db, alert_data)
        if locations:
            primary = locations[0]
            return (primary.latitude, primary.longitude, primary.radius, primary.location_source)
        return (None, None, None, None)


async def get_location_resolver() -> LocationResolver:
    return LocationResolver()