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

## Nearby Users / Shared Location Flow

```
User Browser
    │
    ▼
GPS / Geolocation API (navigator.geolocation.watchPosition)
    │
    ▼
Frontend Location Hook (useUserLocation)
    │
    ▼
HTTP POST /api/users/location (Bearer token)
    │
    ▼
FastAPI Backend — Users Router
    │
    ▼
SQLAlchemy User Model
    │
    ▼
PostgreSQL — users table
    │   last_latitude, last_longitude, location_accuracy,
    │   last_location_update, location_visibility, is_online
    ▼
GET /api/users/nearby (Bearer token + lat/lng/radius)
    │
    ▼
Database Query (filters: visibility=true, not stale (< 5 min),
    distance <= radius_km, excludes current user)
    │
    ▼
Response: NearbyUsersResponse { users: [...], count }
    │
    ▼
Frontend Hook (useNearbyUsers)
    │
    ▼
MapPage — Nearby User Markers + Count Overlay
```

### Location Sharing Details

- **Origin**: Browser GPS via `navigator.geolocation.watchPosition` (high accuracy, 10s timeout, 5s max age)
- **Transport**: HTTPS (required for GPS) → Axios with JWT interceptor → FastAPI `/api/users/location`
- **Storage**: Extended `users` table with 6 new columns (see Database section)
- **Retrieval**: Polling-based — `useNearbyUsers` hook fetches every 30 seconds (configurable); not WebSocket/real-time
- **Display**: `MapPage` renders other users as purple 👤 markers with distance popups; top-right count overlay shows active nearby user count
- **Visibility Control**: `location_visibility` boolean column — when `false`, user is excluded from nearby results but still stores own location
- **Online State**: `is_online` boolean — set to `true` on location update; not actively set to `false` (stale filter handles effective offline)
- **Stale Threshold**: 5 minutes (`STALE_THRESHOLD_MINUTES`) — users not updating within this window are filtered out of nearby results

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
- **useUserLocation** — periodic location update to backend (default 30s interval, minimum 50m movement threshold); sends latitude, longitude, accuracy to `POST /api/users/location`
- **useNearbyUsers** — fetches nearby active users from backend (default 30s refresh, 10km radius); returns users array with distance_km, last_seen, status and count

### API Client

Single Axios client at `services/api.ts` with:
- JWT token injection via request interceptor (reads from localStorage)
- 401 redirect to `/login` via response interceptor
- Domain-specific export objects: `authApi`, `shelterApi`, `hospitalApi`, `disasterApi`, `alertApi`, `settingsApi`, `routeApi`, `weatherApi`, `locationApi`, `aiApi`, `userApi`, `routingApi` (note: `routingApi` is defined but unused; routing uses direct `fetch()` in `utils/routing.ts`)

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
| `risk.py` | `/api/risk` | Risk Assessment |
| `sos.py` | `/api/sos` | SOS (User & Admin) |
| `admin.py` | `/api/admin` | Admin Dashboard |

### User Router Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users/me` | Current user profile |
| POST | `/api/users/location` | Update current user's GPS location |
| GET | `/api/users/nearby` | Get nearby active users within radius |
| GET | `/api/users/settings` | Get current user's settings |
| PUT | `/api/users/settings` | Update current user's settings |

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
- **sos.py** — SOS incident management, responder assignment, status transitions, admin override

### CAP Ingestion

Located in `app/disaster_sources/`:
- **CapProvider** — fetches RSS feeds, parses CAP XML 1.2, extracts alerts with polygon data
- **BackgroundIngestion** — asyncio background task polling every 300 seconds
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

- **users** — id, full_name, email, password (hashed), role (enum: admin/user), last_latitude, last_longitude, location_accuracy, last_location_update, location_visibility, is_online
- **user_settings** — id, user_id (FK, unique), theme, accent_color, notifications_enabled, email_notifications, push_notifications, sound_alerts, emergency_radius, min_alert_severity, default_map_type, auto_locate, show_gov_alerts, show_user_disasters, larger_text, reduced_motion
- **shelters** — id, name, latitude, longitude, capacity, occupancy, phone, address
- **hospitals** — id, name, latitude, longitude, emergency_available, phone, address
- **disasters** — id, type, severity, latitude, longitude, description, status, created_at
- **alerts** — id, title, message, disaster_id (FK), severity, created_at, external_id (unique), expires_at, event, urgency, certainty, area, is_active, expired_at, polygons, source
- **routes** — id, source_lat, source_lng, destination_lat, destination_lng, estimated_time, distance_km

### ORM

- SQLAlchemy 2.0 async with `asyncpg` driver
- Alembic migrations in use — initial migration `2bfd451b4aed` for alerts history fields, latest migration `7b9aa0df48e9` adds user location fields (6 columns to users table)

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

## Admin Dashboard Architecture

### Admin Authentication
- Reuses existing JWT authentication with role-based access control
- `UserRole.ADMIN` enum value in User model
- `require_admin` dependency in `app/utils/dependencies.py` validates admin role
- Single admin account seeded via development script: `admin@aidrac.local`

### Admin API Endpoints (`/api/admin`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/overview` | GET | Summary statistics (active alerts, SOS, people in zones, responders) |
| `/alerts` | GET | List all active government alerts with locations |
| `/sos` | GET | List SOS incidents with optional status filter |
| `/responders` | GET | List nearby available responders (online users with location) |
| `/users` | GET | List all users with location data |
| `/incidents` | GET | SOS incident history with filtering |
| `/zone-stats` | GET | Statistics for affected zone (people, SOS, responders) |
| `/sos/{id}/acknowledge` | POST | Admin acknowledges SOS |
| `/sos/{id}/assign` | POST | Admin assigns responder to SOS |
| `/sos/{id}/status` | POST | Admin updates SOS status |

### Admin Frontend (`/admin`)
- Protected route guarded by `requireAdmin` prop in `ProtectedRoute`
- Real-time overview cards with live backend data
- Live disaster map (reuses MapPage components via iframe)
- SOS management grouped by status: NEW, ACKNOWLEDGED, ASSIGNED, RESPONDING, RESOLVED
- Available responders list with assignment capability
- Affected zone statistics
- Active government alerts display
- Incident history with resolution tracking

## SOS Emergency Response Architecture

### SOS Lifecycle
```
USER PRESSES SOS
       ↓
POST /api/sos → SOSIncident created (status: ACTIVE)
       ↓
ADMIN RECEIVES SOS via /api/admin/sos (polling)
NEARBY USERS RECEIVE SOS via /api/sos/nearby (Dashboard card)
       ↓
USER ACCEPTS SOS via POST /api/sos/{id}/accept
       ↓
SOS status: RESPONDER_ACCEPTED
Responder assigned, RESPONDER tab appears
       ↓
RESPONDER UPDATES STATUS:
  RESPONDER_ACCEPTED → ASSISTANCE_IN_PROGRESS (En Route)
  ASSISTANCE_IN_PROGRESS → ASSISTANCE_PROVIDED (Helping)
       ↓
VICTIM CONFIRMS SAFE via POST /api/sos/{id}/confirm-safe
       ↓
SOS status: USER_CONFIRMED_SAFE → RESOLVED
Responder tab disappears
       ↓
INCIDENT REMAINS IN ADMIN HISTORY via /api/admin/incidents
```

### SOS Status Transitions
| Current Status | Allowed Next Status | Actor |
|----------------|---------------------|-------|
| ACTIVE, RECEIVED, ACKNOWLEDGED, AWAITING_RESPONDER | RESPONDER_ACCEPTED (accept) | Responder |
| ACTIVE, RECEIVED, ACKNOWLEDGED, AWAITING_RESPONDER | ACKNOWLEDGED | Admin |
| ACKNOWLEDGED, AWAITING_RESPONDER | RESPONDER_ASSIGNED (assign) | Admin |
| RESPONDER_ACCEPTED | ASSISTANCE_IN_PROGRESS | Responder |
| ASSISTANCE_IN_PROGRESS | ASSISTANCE_PROVIDED | Responder |
| ASSISTANCE_PROVIDED | USER_CONFIRMED_SAFE | Victim |
| USER_CONFIRMED_SAFE | RESOLVED | Auto (victim confirmation) |
| Any (except resolved) | CANCELLED | Victim |
| Any | Any | Admin (override) |

### Responder Interface (Secret SOS Tab)
- Only visible when user has accepted an SOS OR admin assigned them
- Shows victim info, location, navigation, status progression
- Real-time GPS tracking with navigation to victim
- Status progression: Accepted → En Route → Helping → Completed
- Auto-closes when SOS resolved (history preserved in admin)

### Database Models
- **SOSIncident** (`sos_incidents` table):
  - `id`, `reporting_user_id`, `assigned_responder_id` (FKs to users)
  - `latitude`, `longitude`, `location_accuracy`, `location_timestamp`
  - `emergency_type`, `emergency_details`
  - `status` (SOSStatus enum: 11 states)
  - `responder_type` (COMMUNITY/OFFICIAL)
  - `created_at`, `updated_at`, `accepted_at`, `resolved_at`

### Nearby Responder System
- Reuses existing `useNearbyUsers` / `/api/users/nearby` for location-based discovery
- When SOS active: nearby eligible users see "EMERGENCY NEARBY" card on Dashboard
- User clicks "ACCEPT TO HELP" → becomes responder for that SOS
- Admin notified of assignment, responder gets dedicated SOS panel

### Notification System
- Browser notifications via `Notification` API (permission requested on app mount)
- Alert sounds via Web Audio API
- Wired to: nearby SOS detection, critical government alerts
- Deduplication prevents spam (tracks last notified SOS/alert ID)
- Respects user settings: `notifications_enabled`, `push_notifications`, `sound_alerts`

### Security
- SOS location only visible to: victim, assigned responder, admin
- `/api/sos/{id}` endpoint enforces authorization (victim/responder/admin only)
- Admin endpoints require `require_admin` dependency
- Responder assignment validated (responder must exist, cannot self-respond)
