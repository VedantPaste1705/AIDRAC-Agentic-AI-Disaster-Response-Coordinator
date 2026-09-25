# Architecture

## Overview

AIDRAC follows a three-tier architecture: a React frontend communicates with a FastAPI backend over HTTP, which connects to PostgreSQL for persistence and external APIs for live data.

## System Flow

```
Browser
   │
   ▼
┌─────────────────────────────────────────────┐
│              Frontend (React)               │
│                                             │
│  Pages ──► Components ──► Context/Hooks    │
│                │                            │
│                ▼                            │
│          API Client (Axios)                 │
│          baseURL: /api                      │
│          JWT interceptor                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│              Backend (FastAPI)              │
│                                             │
│  Routers ──► Services ──► LangGraph        │
│               │            Agents           │
│               │                             │
│    ┌──────────┼──────────────┐              │
│    ▼          ▼              ▼              │
│  SQLAlchemy  External     AI (Gemini)      │
│  (async)     APIs                          │
│    │          │              │              │
│    ▼          ▼              ▼              │
│  PostgreSQL  Overpass      Gemini API      │
│              OSM           ──────────       │
│              OpenWeather   Deterministic    │
│              OSRM          Fallback         │
│              IMD/NDMA CAP                   │
└─────────────────────────────────────────────┘
```

## Frontend

### Routing

React Router v6 with the following structure:

- Public routes: `/`, `/login`, `/register`
- Protected routes (wrapped in `ProtectedRoute` → `AppLayout`): `/dashboard`, `/map`, `/shelters`, `/hospitals`, `/alerts`
- Admin-only route: `/admin` (guarded by `requireAdmin` prop)
- 404 catch-all: `*`

### Context Providers

- **AuthContext** — authentication state (user, token, loading), login/register/logout functions, `isAdmin` derived from user role
- **SettingsContext** — user preferences (theme, accent, notifications, radius, map type, accessibility), persisted to localStorage and backend

### Custom Hooks

- **useApi** — generic async data fetching with loading/error/refetch states; dependency-based re-fetching
- **useGeolocation** — browser Geolocation API wrapper with watchPosition support; exposes position, error, loading, permissionDenied, unsupported, refresh
- **useWeather** — weather data fetching with 5-minute auto-refresh interval

### MapPage — Alert Rendering Logic

`pages/MapPage.tsx` renders government alerts with correct geographic positioning:

- **Fetch**: Calls `GET /api/alerts?all=true` (bypasses 200km distance filter)
- **Polygon alerts**: Renders polygon + centroid marker
- **Resolved coordinates**: Renders marker at `alert.latitude`/`alert.longitude`
- **Multi-location alerts**: Renders one marker per entry in `alert.locations[]` (like shelters/hospitals)
- **No coordinates**: Skips map marker entirely — **never falls back to user GPS**
- **Filter**: Respects `settings.min_alert_severity` and `settings.show_gov_alerts`

### Styling

- Tailwind CSS with CSS custom properties for theming
- CSS variables control: colors (`--card-bg`, `--sidebar-bg`, `--section-bg`, etc.), borders, shadows, glass effects
- Theme classes: `.light`, `.dark` (default), `.system-theme`
- Accent data attributes: `[data-theme="sapphire"]`, `[data-theme="amber"]`, `[data-theme="emerald"]`
- Accessibility classes: `.larger-text`, `.reduced-motion`, `.reduced-motion-system`

## Backend

### FastAPI Application

Entry point: `app/main.py`
- CORS: fully open (`allow_origins=["*"]`)
- Lifespan: creates tables on startup, starts background CAP ingestion
- All routers prefixed with `/api`

### Routers

| Router | Prefix | Tag |
|--------|--------|-----|
| `auth.py` | `/api/auth` | Authentication |
| `users.py` | `/api/users` | Users |
| `shelters.py` | `/api/shelters` | Shelters (full CRUD) |
| `hospitals.py` | `/api/hospitals` | Hospitals (GET, POST only) |
| `disasters.py` | `/api/disasters` | Disasters (GET, GET /active, POST only) |
| `alerts.py` | `/api/alerts` | Alerts (GET, POST, GET /history) |
| `routes.py` | `/api/routes` | Routes (GET, POST) |
| `weather.py` | `/api/weather` | Weather |
| `location.py` | `/api/location` | Location / OSM |
| `ai.py` | `/api/ai` | AI |

### Services

Business logic is isolated in `app/services/`:

- **auth.py** — user creation, password hashing, JWT token generation
- **weather.py** — OpenWeatherMap API client (raises ValueError if no API key; no mock fallback)
- **alert.py** — CAP alert CRUD, polygon-based location filtering, history
- **shelter.py** / **hospital.py** / **disaster.py** — CRUD operations
- **location_service.py** — Overpass API queries for nearby infrastructure with 10-minute TTL cache
- **overpass_service.py** — HTTP client with 3-server retry chain (configurable primary + 2 fallbacks)
- **routing_service.py** — OSRM routing with Haversine straight-line fallback (used by LangGraph Route Agent)
- **incident_service.py** — LangGraph checkpoint management via MemorySaver
- **location_resolver.py** — **NEW**: Priority-based location resolution for CAP alerts (polygon → circle → point → local GeoNames DB → Nominatim); supports multi-location resolution; caches 556k+ Indian locations from GeoNames

### CAP Ingestion

Located in `app/disaster_sources/`:
- **CapProvider** — fetches RSS feeds, parses CAP XML 1.2, extracts alerts with polygon, circle, and point data
- **LocationResolver** — resolves alert coordinates using priority: polygon centroid → circle center → point → local GeoNames DB (556k+ Indian locations) → Nominatim fallback; supports multi-location resolution for comma-separated area strings
- **BackgroundIngestion** — asyncio background task polling every 300 seconds; uses LocationResolver for new alerts; **skips initial ingestion on startup** to preserve already-resolved coordinates
- **CacheService** — in-memory TTL cache for RSS feeds and CAP XML files
- Multi-source: IMD (primary) and NDMA (secondary, frequently rate-limited), merged by `external_id`

### LangGraph Agents

Located in `app/langgraph/`:
- **Weather Agent** — fetches weather from WeatherService, infers risk level from temperature and description
- **Alert Agent** — loads active CAP alerts from database with severity analysis
- **Infrastructure Agent** — queries Overpass for 7 facility categories in parallel via asyncio.gather
- **Route Agent** — picks nearest facility via distance ranking, computes walking ETA via RoutingService
- **Coordinator Agent** — Gemini-powered reasoning with deterministic fallback
- All 3 upstream agents (weather, alert, infrastructure) fan out in parallel; route agent waits for all; coordinator runs last

## Database

### PostgreSQL Schema

- **users** — id, full_name, email, password (hashed), role (enum: admin/user)
- **user_settings** — id, user_id (FK, unique), theme, accent_color, notifications_enabled, email_notifications, push_notifications, sound_alerts, emergency_radius, min_alert_severity, default_map_type, auto_locate, show_gov_alerts, show_user_disasters, larger_text, reduced_motion
- **shelters** — id, name, latitude, longitude, capacity, occupancy, phone, address
- **hospitals** — id, name, latitude, longitude, emergency_available, phone, address
- **disasters** — id, type, severity, latitude, longitude, description, status, created_at
- **alerts** — id, title, message, disaster_id (FK), severity, created_at, external_id (unique), expires_at, event, urgency, certainty, area, is_active, expired_at, polygons, source, **latitude, longitude, location_source**
- **routes** — id, source_lat, source_lng, destination_lat, destination_lng, estimated_time, distance_km
- **locations** — id, name, normalized_name, latitude, longitude, type, state, district, country, aliases (556k+ GeoNames entries for India)
- **alert_locations** — id, alert_id (FK), name, latitude, longitude, location_source, location_type, state, district, resolved_order (multi-location support for alerts)

### ORM

- SQLAlchemy 2.0 async with `asyncpg` driver
- No Alembic migrations in use — tables created on startup via `Base.metadata.create_all`

## External Dependencies

| Service | Purpose | Auth Required |
|---------|---------|---------------|
| OpenWeatherMap API | Current weather data | API key (required; no mock fallback) |
| Overpass API | OSM infrastructure data (3-server chain) | None (public) |
| OpenRouteService API | Foot-walking routes (frontend only) | API key (optional; OSRM fallback) |
| OSRM Public API | Routing (frontend and backend) | None (public) |
| IMD CAP RSS | Government weather alerts | None (public) |
| NDMA CAP RSS | Government disaster alerts | None (public; frequently rate-limited) |
| Google Gemini API | AI recommendations | API key (optional; deterministic fallback) |
