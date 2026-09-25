import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.alert import Alert
from app.models.alert_location import AlertLocation
from app.services.disaster_sources.cap_provider import CapProvider
from app.services.disaster_sources.base import canonical_alert_id
from app.services.disaster_sources.normalizer import alert_data_to_dict
from app.services.location_resolver import LocationResolver, get_location_resolver
from app.config.settings import settings

logger = logging.getLogger("aidrac.disaster_sources.background_refresh")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setLevel(logging.INFO)
    _sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_sh)
    logger.propagate = False


class BackgroundIngestion:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._cap = CapProvider()
        self._location_resolver: LocationResolver | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def _get_location_resolver(self) -> LocationResolver:
        if self._location_resolver is None:
            self._location_resolver = await get_location_resolver()
        return self._location_resolver

    async def start(self) -> None:
        logger.info("Starting background alert ingestion every %d seconds", settings.REFRESH_INTERVAL_SECONDS)
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Background refresh scheduled (initial ingestion skipped to preserve resolved locations)")

    async def stop(self) -> None:
        logger.info("Stopping background alert ingestion")
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(settings.REFRESH_INTERVAL_SECONDS)
                logger.info("Background refresh cycle starting")
                await self._cap.clear_cache()
                await self._ingest()
                logger.info("Background refresh cycle complete")
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Background refresh cycle failed — will retry")

    async def _ingest(self) -> None:
        try:
            cap_alerts = await self._cap.get_alerts()
        except Exception:
            logger.exception("Failed to fetch CAP alerts in background task")
            return

        if not cap_alerts:
            logger.warning("Background ingestion: no CAP alerts returned")
            return

        async with self._session_factory() as db:
            try:
                await self._sync_alerts(db, cap_alerts)
                await self._expire_old(db)
                await self._purge_old_history(db)
                await db.commit()
                logger.info("Background ingestion: commit successful (%d alerts)", len(cap_alerts))
            except Exception:
                await db.rollback()
                logger.exception("Background ingestion: transaction rolled back")

    async def _sync_alerts(self, db: AsyncSession, cap_alerts: list) -> None:
        result = await db.execute(
            select(Alert).where(Alert.external_id.isnot(None))
        )
        existing_rows = result.scalars().all()
        existing = {
            canonical_alert_id(r.external_id): r
            for r in existing_rows
            if r.external_id
        }

        inserted = 0
        updated = 0

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
                from sqlalchemy import delete
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

        await db.flush()
        logger.info("Background sync: %d inserted, %d updated", inserted, updated)

    async def _expire_old(self, db: AsyncSession) -> None:
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
            logger.info("Expired %d alerts (soft-delete)", len(expired))

    async def _purge_old_history(self, db: AsyncSession) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.ALERT_RETENTION_DAYS)
        result = await db.execute(
            select(Alert).where(
                Alert.is_active.is_(False),
                Alert.expired_at.isnot(None),
                Alert.expired_at < cutoff,
            )
        )
        stale = list(result.scalars().all())
        for row in stale:
            await db.delete(row)
        if stale:
            await db.flush()
            logger.info("Purged %d alerts older than %d days", len(stale), settings.ALERT_RETENTION_DAYS)
