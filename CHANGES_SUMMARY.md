# AIDRAC - Location Resolution System Implementation Summary

**Date:** September 25, 2026  
**Branch/Commit:** Main development branch  

---

## Overview

Implemented a complete **Government/CAP Alert Location Resolution System** that fixes the critical bug where alerts without polygons were incorrectly displayed at the user's GPS location instead of their actual geographic location.

---

## Problem Solved

**Before:** Alerts without polygon data (e.g., "Pune, Maharashtra") were rendered at the user's current GPS position with a small offset, causing all polygon-less alerts to cluster around the user.

**After:** Alerts are resolved to their actual geographic coordinates using a priority-based system:
1. **Polygon centroid** (if CAP polygon exists)
2. **Circle center** (if CAP circle exists)
3. **Point coordinates** (if CAP point exists)
4. **Local geographic database** (556k+ Indian locations from GeoNames)
5. **Nominatim fallback** (OpenStreetMap geocoder)
6. **No location** — alert renders in list view but NOT on map (never uses user GPS)

---

## Files Modified/Created

### Backend - Database & Models

| File | Change |
|------|--------|
| `alembic/versions/add_alert_location_fields_and_locations_table.py` | Migration: Added `latitude`, `longitude`, `location_source` to alerts; created `locations` table (556k+ GeoNames entries) |
| `alembic/versions/add_alert_locations_table.py` | Migration: Created `alert_locations` table for multi-location support (one alert → multiple districts) |
| `app/models/alert.py` | Added `latitude`, `longitude`, `location_source` columns + `locations` relationship |
| `app/models/location.py` | New: Geographic gazetteer model (name, normalized_name, lat/lng, type, state, district, aliases) |
| `app/models/alert_location.py` | New: Junction table for alert ↔ multiple locations |
| `app/models/__init__.py` | Exported new models |

### Backend - Core Services

| File | Change |
|------|--------|
| `app/services/disaster_sources/base.py` | Extended `AlertData` with `circle`, `point`, `latitude`, `longitude`, `radius`, `location_source` |
| `app/services/disaster_sources/cap_provider.py` | Parse CAP `<circle>` and `<point>` elements from XML |
| `app/services/location_resolver.py` | **NEW CORE SERVICE** - Priority-based location resolution with multi-location support |
| `app/services/disaster_sources/normalizer.py` | Include new location fields in DB dict |
| `app/services/disaster_sources/ingestion_service.py` | Call `resolve_all_locations()` during ingestion; store in `alert_locations` table |
| `app/services/disaster_sources/background_refresh.py` | Updated to use `LocationResolver`; skips initial ingestion on startup to preserve resolved locations |
| `app/services/alert.py` | Eager-load `locations`; filter by lat/lng for alerts without polygons |
| `app/services/risk_assessment_service.py` | Use lat/lng for proximity calculations when no polygon |
| `app/services/__init__.py` | Export `LocationResolver` |

### Backend - API & Schemas

| File | Change |
|------|--------|
| `app/schemas/alert.py` | Added `AlertLocationResponse` + `locations` list to `AlertResponse` |
| `app/routers/alerts.py` | No change needed (uses service layer) |

### Backend - Data Loading

| File | Change |
|------|--------|
| `scripts/load_geonames.py` | Loads 556k+ Indian locations from GeoNames + 100 manual major cities |

### Frontend - Types & Map

| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Added `latitude`, `longitude`, `location_source` to `Alert` interface |
| `frontend/src/pages/MapPage.tsx` | **FIXED**: Removed user-GPS fallback; renders multiple markers from `a.locations`; fetches all alerts (`all=true`) |

### Frontend - Build

| File | Change |
|------|--------|
| `frontend/src/services/api.ts` | Added `all` parameter to `alertApi.getAll()` |

### Tests

| File | Change |
|------|--------|
| `backend/tests/test_location_resolver.py` | 19 tests: normalization, alias expansion, priority resolution, filtering |

---

## Key Technical Details

### Location Resolution Priority
```
1. Polygon → centroid (source: "polygon")
2. Circle → center (source: "circle")  
3. Point → coordinates (source: "point")
4. areaDesc → Local DB (source: "local_database")
5. areaDesc → Nominatim (source: "geocoder")
6. None → NULL (NEVER user GPS)
```

### Multi-Location Support
- Alerts with area like "BEGUSARAI, BHAGALPUR, DARBHANGA" resolve **each district separately**
- Stored in `alert_locations` table with `resolved_order`
- MapPage renders **one marker per resolved location** (like shelters/hospitals)

### Database Schema
```sql
-- alerts table additions
latitude FLOAT, longitude FLOAT, location_source VARCHAR(30)

-- locations table (556k+ rows)
id, name, normalized_name, latitude, longitude, type, state, district, country, aliases

-- alert_locations table
id, alert_id, name, latitude, longitude, location_source, location_type, state, district, resolved_order
```

### GeoNames Data
- **556,834 locations** from GeoNames India dump
- Includes cities, districts, taluks, administrative boundaries
- **100 manual major cities** added for guaranteed coverage
- Efficient lookup by `normalized_name` index

---

## Verification Results

### Backend Tests
```
43 passed (location resolver, risk assessment, CAP time)
```

### Frontend Build
```
✓ TypeScript: 0 errors
✓ Vite build: Success
```

### API Verification
```json
GET /api/alerts?all=true

{
  "id": 163,
  "severity": "advisory",
  "area": "BEGUSARAI, BHAGALPUR, DARBHANGA...",
  "latitude": 25.41853,
  "longitude": 86.13389,
  "location_source": "local_database",
  "locations": [
    {"name": "BEGUSARAI", "latitude": 25.41853, "longitude": 86.13389, "location_source": "local_database"},
    {"name": "BHABUA", "latitude": 26.04969, "longitude": 79.63035, ...},
    {"name": "BHAGALPUR", "latitude": 25.18362, "longitude": 82.98397, ...},
    {"name": "DARBHANGA", "latitude": 26.15216, "longitude": 85.89707, ...},
    {"name": "KATIHAR", "latitude": 25.53852, "longitude": 87.57044, ...},
    {"name": "KHAGARIA", "latitude": 25.5022, "longitude": 86.46708, ...},
    {"name": "MADHEPURA", "latitude": 25.92127, "longitude": 86.79271, ...},
    {"name": "MADHUBANI", "latitude": 27.00013, "longitude": 84.10396, ...},
    {"name": "PURNEA", "latitude": 25.78, "longitude": 87.47, ...}
  ]
}
```

---

## Docker Deployment

### Rebuild Required
```bash
docker-compose down
docker-compose build --no-cache backend
docker-compose up -d
```

### Background Refresh Behavior
- **Startup**: Skips initial ingestion (preserves resolved locations)
- **Every 300s**: Fetches new CAP alerts, resolves locations via `LocationResolver`, stores in `alert_locations`

---

## Acceptance Criteria Met

✅ Alert "Pune, Maharashtra" → resolves to 18.5204, 73.8567 via local DB  
✅ Alert "Bhagalpur" → resolves to 25.1836, 82.9840 via local DB  
✅ Multi-district alert "BEGUSARAI, BHAGALPUR..." → 9 separate markers  
✅ Polygon alerts → render polygon + centroid marker  
✅ Circle/Point CAP elements → parsed and used  
✅ **NEVER** uses user GPS for alert position  
✅ Alerts without coordinates → render in list, NOT on map  
✅ Background refresh preserves existing coordinates  
✅ 43 backend tests pass  
✅ Frontend TypeScript/build passes  

---

## Files NOT Modified
- `frontend/src/components/*` (reused existing)
- `backend/app/routers/*` (except schemas)
- `backend/app/services/auth.py`, `disaster.py`, etc.
- Database connection, auth, user management unchanged