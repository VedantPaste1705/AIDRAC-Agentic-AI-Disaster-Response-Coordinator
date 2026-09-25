import asyncio
from app.services.location_resolver import LocationResolver
from app.models.alert import Alert
from app.models.alert_location import AlertLocation
from app.services.disaster_sources.base import AlertData
from sqlalchemy import select
from app.database.connection import async_session_factory

async def reprocess():
    async with async_session_factory() as db:
        resolver = LocationResolver()
        result = await db.execute(select(Alert).where(Alert.source == 'ndma', Alert.is_active == True))
        alerts = list(result.scalars().all())
        print(f'Processing {len(alerts)} alerts...')
        
        for alert in alerts:
            existing = await db.execute(select(AlertLocation).where(AlertLocation.alert_id == alert.id))
            if existing.scalars().first():
                continue
            
            alert_data = AlertData(
                external_id=alert.external_id or str(alert.id),
                event=alert.event or '',
                headline=alert.title or '',
                description=alert.message or '',
                severity=alert.severity or 'info',
                urgency=alert.urgency or 'unknown',
                certainty=alert.certainty or 'unknown',
                area=alert.area or '',
                polygons=alert.polygons.split(';') if alert.polygons else None,
            )
            
            resolved = await resolver.resolve_all_locations(db, alert_data)
            
            if resolved:
                primary = resolved[0]
                alert.latitude = primary.latitude
                alert.longitude = primary.longitude
                alert.radius = primary.radius
                alert.location_source = primary.location_source
                
                for loc in resolved:
                    alert_loc = AlertLocation(
                        alert_id=alert.id,
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
                print(f'Alert {alert.id}: {len(resolved)} locations (primary: {primary.name})')
            else:
                print(f'Alert {alert.id}: NO LOCATIONS RESOLVED for "{alert.area[:60]}..."')
        
        await db.commit()
        print('Done!')

asyncio.run(reprocess())