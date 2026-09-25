import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.disaster_sources.base import AlertData
from app.services.location_resolver import (
    LocationResolver,
    _normalize_name,
    _extract_location_parts,
    _expand_with_aliases,
    _INDIAN_STATES,
)


class TestLocationNormalization:
    def test_normalize_name_basic(self):
        assert _normalize_name("Pune") == "pune"
        assert _normalize_name("PUNE") == "pune"
        assert _normalize_name("  Pune  ") == "pune"
        assert _normalize_name("Pune City") == "pune city"
        assert _normalize_name("Poona") == "poona"

    def test_normalize_name_special_chars(self):
        assert _normalize_name("Pune, Maharashtra") == "pune maharashtra"
        assert _normalize_name("Pune District, Maharashtra") == "pune district maharashtra"
        assert _normalize_name("Mumbai (Bombay)") == "mumbai bombay"

    def test_extract_location_parts_simple(self):
        parts = _extract_location_parts("Pune")
        assert parts == ["Pune"]

    def test_extract_location_parts_multiple(self):
        parts = _extract_location_parts("Pune, Nashik, Ahmednagar")
        assert "Pune" in parts
        assert "Nashik" in parts
        assert "Ahmednagar" in parts

    def test_extract_location_parts_with_state(self):
        parts = _extract_location_parts("Pune, Maharashtra")
        assert "Pune" in parts
        assert "Maharashtra" not in parts

    def test_extract_location_parts_with_district(self):
        parts = _extract_location_parts("Pune District, Maharashtra")
        assert "Pune" in parts

    def test_extract_location_parts_with_admin_suffixes(self):
        parts = _extract_location_parts("Pune City, Maharashtra")
        assert "Pune" in parts

    def test_expand_aliases_pune(self):
        expanded = _expand_with_aliases("Pune")
        assert "Pune" in expanded
        assert "Poona" in expanded

    def test_expand_aliases_mumbai(self):
        expanded = _expand_with_aliases("Mumbai")
        assert "Mumbai" in expanded
        assert "Bombay" in expanded

    def test_expand_aliases_chennai(self):
        expanded = _expand_with_aliases("Chennai")
        assert "Chennai" in expanded
        assert "Madras" in expanded

    def test_expand_aliases_unknown(self):
        expanded = _expand_with_aliases("UnknownPlace")
        assert expanded == ["UnknownPlace"]


class TestLocationResolver:
    @pytest.fixture
    def resolver(self):
        return LocationResolver()

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_resolve_polygon_priority(self, resolver, mock_db):
        """Polygon should have highest priority."""
        alert = AlertData(
            external_id="test1",
            event="Heavy Rain",
            headline="Heavy Rain Warning",
            description="Heavy rain expected",
            severity="warning",
            urgency="immediate",
            certainty="observed",
            area="Pune, Maharashtra",
            polygons=["18.50 73.80 18.60 73.90 18.55 73.85"],
            circle="18.52 73.85 25",
            point="18.52 73.85",
        )
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "polygon"
        assert lat is not None
        assert lng is not None
        assert abs(lat - 18.55) < 0.01
        assert abs(lng - 73.85) < 0.01

    @pytest.mark.asyncio
    async def test_resolve_circle_priority(self, resolver, mock_db):
        """Circle should have second priority when no polygon."""
        alert = AlertData(
            external_id="test2",
            event="Cyclone",
            headline="Cyclone Warning",
            description="Cyclone approaching",
            severity="severe",
            urgency="immediate",
            certainty="likely",
            area="Mumbai, Maharashtra",
            circle="19.0760 72.8777 50",
            point="19.0760 72.8777",
        )
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "circle"
        assert lat == 19.0760
        assert lng == 72.8777
        assert radius == 50.0

    @pytest.mark.asyncio
    async def test_resolve_point_priority(self, resolver, mock_db):
        """Point should have third priority when no polygon/circle."""
        alert = AlertData(
            external_id="test3",
            event="Earthquake",
            headline="Earthquake Alert",
            description="Earthquake detected",
            severity="moderate",
            urgency="expected",
            certainty="possible",
            area="Delhi",
            point="28.6139 77.2090",
        )
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "point"
        assert lat == 28.6139
        assert lng == 77.2090
        assert radius is None

    @pytest.mark.asyncio
    async def test_resolve_local_db(self, resolver, mock_db):
        """Local database should be used when no polygon/circle/point."""
        mock_location = MagicMock()
        mock_location.latitude = 18.5204
        mock_location.longitude = 73.8567

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_location
        mock_db.execute.return_value = mock_result

        alert = AlertData(
            external_id="test4",
            event="Flood",
            headline="Flood Warning",
            description="Flood expected",
            severity="warning",
            urgency="future",
            certainty="likely",
            area="Pune, Maharashtra",
        )
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "local_database"
        assert lat == 18.5204
        assert lng == 73.8567

    @pytest.mark.asyncio
    async def test_resolve_no_location(self, resolver, mock_db):
        """Should return None when nothing can be resolved."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        alert = AlertData(
            external_id="test5",
            event="Unknown",
            headline="Unknown Alert",
            description="Unknown area",
            severity="info",
            urgency="unknown",
            certainty="unknown",
            area="SomeUnknownPlaceXYZ",
        )
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert lat is None
        assert lng is None
        assert radius is None
        assert source is None

    @pytest.mark.asyncio
    async def test_resolve_priority_order(self, resolver, mock_db):
        """Verify exact priority order: polygon > circle > point > local_db > geocoder."""
        mock_location = MagicMock()
        mock_location.latitude = 19.0760
        mock_location.longitude = 72.8777
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_location
        mock_db.execute.return_value = mock_result

        # Test with all fields - polygon should win
        alert = AlertData(
            external_id="test_priority",
            event="Test",
            headline="Test",
            description="Test",
            severity="info",
            urgency="unknown",
            certainty="unknown",
            area="Mumbai, Maharashtra",
            polygons=["19.0 72.8 19.1 72.9 19.05 72.85"],
            circle="19.0760 72.8777 25",
            point="19.0760 72.8777",
        )
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "polygon"

        # Test without polygon - circle should win
        alert.polygons = None
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "circle"

        # Test without circle - point should win
        alert.circle = None
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "point"

        # Test without point - local_db should win
        alert.point = None
        lat, lng, radius, source = await resolver.resolve(mock_db, alert)
        assert source == "local_database"


class TestAlertServiceFiltering:
    """Test that alert filtering works with lat/lng coordinates."""

    def test_haversine_distance(self):
        from app.services.alert import _haversine
        # Distance between Pune and Mumbai ~ 120km
        dist = _haversine(18.5204, 73.8567, 19.0760, 72.8777)
        assert 115 < dist < 125

    def test_point_in_polygon(self):
        from app.services.alert import _point_in_polygon
        # Square around Pune
        polygon = [(18.0, 73.0), (18.0, 74.0), (19.0, 74.0), (19.0, 73.0)]
        assert _point_in_polygon(18.5204, 73.8567, polygon) is True
        assert _point_in_polygon(20.0, 75.0, polygon) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])