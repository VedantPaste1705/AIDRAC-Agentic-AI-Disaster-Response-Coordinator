import logging
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_location import AlertLocation
from app.services.disaster_sources.cap_provider import CapProvider
from app.services.disaster_sources.normalizer import alert_data_to_dict
from app.services.disaster_sources.base import canonical_alert_id
from app.services.location_resolver import LocationResolver, get_location_resolver

logger = logging.getLogger("aidrac.disaster_sources.ingestion_service")


class IngestionService:
    def __init__(self) -> None:
        self._cap = CapProvider()
        self._location_resolver: LocationResolver | None = None

    async def _get_location_resolver(self) -> LocationResolver:
        if self._location_resolver is None:
            self._location_resolver = await get_location_resolver()
        return self._location_resolver

    async def ingest(self, db: AsyncSession) -> list[Alert]:
        try:
            return await self._ingest(db)
        except Exception:
            await db.rollback()
            logger.exception("CAP ingestion failed — transaction rolled back")
            return []

    async def _ingest(self, db: AsyncSession) -> list[Alert]:
        cap_alerts = await self._cap.get_alerts()

        if not cap_alerts:
            logger.warning("No CAP alerts returned from provider — skipping ingestion")
            return []

        existing = await self._load_existing_by_external_id(db)
        logger.debug("Existing CAP alerts in DB: %d", len(existing))

        inserted = 0
        updated = 0
        ingested: list[Alert] = []

        resolver = await self._get_location_resolver()

        for alert_data in cap_alerts:
            # Resolve all locations for this alert
            resolved_locations = await resolver.resolve_all_locations(db, alert_data)

            # Set primary location for backwards compatibility
            if resolved_locations:
                primary = resolved_locations[0]
                alert_data.latitude = primary.latitude
                alert_data.longitude = primary.longitude
                alert_data.radius = primary.radius
                alert_data.location_source = primary.location_source
            else:
                alert_data.latitude = None
                alert_data.longitude = None
                alert_data.radius = None
                alert_data.location_source = None

            fields = alert_data_to_dict(alert_data)
            dedup_key = canonical_alert_id(alert_data.external_id)
            row = existing.get(dedup_key)

            if row is not None:
                for key, value in fields.items():
                    setattr(row, key, value)
                if not row.is_active:
                    row.is_active = True
                    row.expired_at = None
                # Delete old locations and insert new ones
                await db.execute(delete(AlertLocation).where(AlertLocation.alert_id == row.id))
                updated += 1
            else:
                row = Alert(**fields)
                db.add(row)
                await db.flush()  # Get the ID
                existing[dedup_key] = row
                inserted += 1

            # Insert resolved locations
            if resolved_locations:
                for loc in resolved_locations:
                    alert_loc = AlertLocation(
                        alert_id=row.id,
                        name=loc.name,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        location_source=loc.location_source,
                        location_type=loc.location_type,
                        state=loc.state,
                        district=loc.district,
                        resolved_order=loc.order,
                    )
                    db.add(alert_loc)

            logger.info(
                "Alert %s: area=%s, primary_lat=%s, primary_lng=%s, primary_source=%s, num_locations=%d",
                alert_data.external_id, alert_data.area,
                alert_data.latitude, alert_data.longitude, alert_data.location_source,
                len(resolved_locations)
            )

            ingested.append(row)

        await db.flush()
        logger.info("Inserted: %d  Updated: %d", inserted, updated)

        expired_count = await self._soft_expire(db)
        logger.info("Soft-expired: %d", expired_count)

        await db.commit()
        logger.info("Database Commit Successful")

        return ingested

    async def _load_existing_by_external_id(
        self, db: AsyncSession
    ) -> dict[str, Alert]:
        result = await db.execute(
            select(Alert).where(Alert.external_id.isnot(None))
        )
        rows = result.scalars().all()
        return {
            canonical_alert_id(r.external_id): r
            for r in rows
            if r.external_id
        }

    async def _soft_expire(self, db: AsyncSession) -> int:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Alert).where(
                Alert.is_active.is_(True),
                Alert.expires_at.isnot(None),
                Alert.expires_at < now,
            )
        )
        expired = list(result.scalars().all())
        for row in expired:
            row.is_active = False
            row.expired_at = now
        if expired:
            await db.flush()
        return len(expired)
