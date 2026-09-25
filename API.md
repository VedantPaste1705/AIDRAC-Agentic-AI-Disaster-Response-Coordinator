# API Reference

Base URL: `/api`

Authentication: Bearer token via `Authorization: Bearer <token>` header for protected endpoints.

---

## Health

### GET /api/health

Returns server status and version.

**Authentication:** None

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## Authentication

### POST /api/auth/register

Register a new user account.

**Authentication:** None

**Request Body:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "securepass"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "user"
  }
}
```

### POST /api/auth/login

Log in with email and password.

**Authentication:** None

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepass"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "user"
  }
}
```

---

## Users

### GET /api/users/me

Get the current authenticated user's profile.

**Authentication:** Required (user)

**Response:**
```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}
```

### POST /api/users/location

Update the current user's GPS location. Sets `is_online=true` and updates `last_location_update` to current timestamp.

**Authentication:** Required (user)

**Request Body:**
```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "accuracy": 10.5
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `latitude` | float | Yes | Latitude (-90 to 90) |
| `longitude` | float | Yes | Longitude (-180 to 180) |
| `accuracy` | float | No | GPS accuracy in meters (≥ 0) |

**Response (200):**
```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "role": "user"
}
```

**Note:** The response is the updated user object (without location fields). The location is stored in the database and returned via the nearby endpoint.

### GET /api/users/nearby

Get nearby active users within the specified radius. Excludes the current user. Filters out users with `location_visibility=false` and stale locations (no update in last 5 minutes).

**Authentication:** Required (user)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lat` | float | Yes | — | Latitude (-90 to 90) |
| `lng` | float | Yes | — | Longitude (-180 to 180) |
| `radius_km` | float | No | 10 | Search radius in kilometers (0.1 to 100) |

**Response:**
```json
{
  "users": [
    {
      "user_id": 2,
      "full_name": "Jane Smith",
      "latitude": 28.6200,
      "longitude": 77.2100,
      "distance_km": 0.85,
      "last_seen": "2026-01-15T10:30:00Z",
      "status": "active"
    }
  ],
  "count": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | int | Nearby user's ID |
| `full_name` | string | Nearby user's full name |
| `latitude` | float | Nearby user's latitude |
| `longitude` | float | Nearby user's longitude |
| `distance_km` | float | Haversine distance from requester (rounded to 3 decimals) |
| `last_seen` | datetime (ISO 8601) | Timestamp of user's last location update |
| `status` | string | Always "active" (stale users are filtered out) |

### GET /api/users/settings

Get the current user's settings. Auto-creates default settings if they don't exist.

**Authentication:** Required (user)

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "theme": "dark",
  "accent_color": "sapphire",
  "notifications_enabled": true,
  "email_notifications": true,
  "push_notifications": true,
  "sound_alerts": true,
  "emergency_radius": 25,
  "min_alert_severity": "info",
  "default_map_type": "standard",
  "auto_locate": true,
  "show_gov_alerts": true,
  "show_user_disasters": true,
  "larger_text": false,
  "reduced_motion": false
}
```

### PUT /api/users/settings

Update the current user's settings. Partial update supported.

**Authentication:** Required (user)

**Request Body** (all fields optional):
```json
{
  "theme": "light",
  "accent_color": "emerald",
  "notifications_enabled": false
}
```

**Response:** Returns the complete updated settings object.

---

## Shelters

### GET /api/shelters

List all shelters from the database.

**Authentication:** None

**Response:**
```json
[
  {
    "id": 1,
    "name": "Community Shelter A",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "capacity": 500,
    "occupancy": 120,
    "phone": "+91-1234567890",
    "address": "New Delhi"
  }
]
```

### POST /api/shelters

Create a new shelter.

**Authentication:** Required (admin)

**Request Body:**
```json
{
  "name": "New Shelter",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "capacity": 300,
  "occupancy": 0,
  "phone": "+91-9876543210",
  "address": "New Delhi"
}
```

### PUT /api/shelters/{shelter_id}

Update an existing shelter.

**Authentication:** Required (admin)

### DELETE /api/shelters/{shelter_id}

Delete a shelter.

**Authentication:** Required (admin)

**Response:** 204 No Content

---

## Hospitals

### GET /api/hospitals

List all hospitals from the database.

**Authentication:** None

**Response:**
```json
[
  {
    "id": 1,
    "name": "General Hospital",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "emergency_available": true,
    "phone": "+91-1234567890",
    "address": "New Delhi"
  }
]
```

### POST /api/hospitals

Create a new hospital.

**Authentication:** Required (admin)

**Request Body:**
```json
{
  "name": "New Hospital",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "emergency_available": true,
  "phone": "+91-9876543210",
  "address": "New Delhi"
}
```

**Note:** No PUT or DELETE endpoints exist for hospitals.

---

## Disasters

### GET /api/disasters

List all disasters.

**Authentication:** None

**Response:**
```json
[
  {
    "id": 1,
    "type": "flood",
    "severity": "critical",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "description": "Severe flooding in low-lying areas",
    "status": "active",
    "created_at": "2026-01-01T00:00:00"
  }
]
```

### GET /api/disasters/active

List only active disasters.

**Authentication:** None

### POST /api/disasters

Create a new disaster record.

**Authentication:** Required (admin)

**Request Body:**
```json
{
  "type": "flood",
  "severity": "critical",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "description": "Severe flooding in low-lying areas"
}
```

---

## Alerts

### GET /api/alerts

Get active alerts. Optionally filtered by location.

**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | No | Latitude for location filtering |
| `lng` | float | No | Longitude for location filtering |
| `all` | bool | No | Set to `true` to include all alerts including expired |

**Response:**
```json
[
  {
    "id": 1,
    "title": "Severe Thunderstorm Warning",
    "message": "A severe thunderstorm is expected...",
    "disaster_id": null,
    "severity": "warning",
    "created_at": "2026-01-01T00:00:00",
    "external_id": "imd-12345",
    "expires_at": "2026-01-02T00:00:00",
    "event": "Thunderstorm",
    "urgency": "expected",
    "certainty": "likely",
    "area": "New Delhi",
    "is_active": true,
    "expired_at": null,
    "polygons": "28.6139 77.2090 28.7139 77.2090 28.7139 77.3090 28.6139 77.3090",
    "source": "imd"
  }
]
```

### POST /api/alerts

Create a new alert.

**Authentication:** Required (admin)

**Request Body:**
```json
{
  "title": "Severe Thunderstorm Warning",
  "message": "A severe thunderstorm is expected...",
  "severity": "critical",
  "disaster_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Alert title (1-255 characters) |
| `message` | string | Yes | Alert message body |
| `severity` | string | No | Severity level (default: "info") |
| `disaster_id` | int | No | Optional FK to a disaster record |

### GET /api/alerts/history

Get paginated alert history (expired/deactivated alerts).

**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | No | 50 | Number of alerts per page (max 200) |
| `offset` | int | No | 0 | Pagination offset |

---

## Weather

### GET /api/weather

Get current weather for a location.

**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lat` | float | No | 28.6139 | Latitude |
| `lng` | float | No | 77.2090 | Longitude |

**Response:**
```json
{
  "temperature": 32.5,
  "feels_like": 34.0,
  "humidity": 55,
  "wind_speed": 4.5,
  "description": "scattered clouds",
  "icon": "03d",
  "rain": 0.0,
  "city": "New Delhi"
}
```

---

## Routes

### GET /api/routes

List all routes, ordered by ID.

**Authentication:** None

**Response:**
```json
[
  {
    "id": 1,
    "source_lat": 28.6139,
    "source_lng": 77.2090,
    "destination_lat": 28.7041,
    "destination_lng": 77.1025,
    "estimated_time": 45.0,
    "distance_km": 3.2
  }
]
```

### POST /api/routes

Create a new route.

**Authentication:** None

**Request Body:**
```json
{
  "source_lat": 28.6139,
  "source_lng": 77.2090,
  "destination_lat": 28.7041,
  "destination_lng": 77.1025,
  "estimated_time": 45.0,
  "distance_km": 3.2
}
```

---

## Location (OpenStreetMap)

### GET /api/location/nearby

Get nearby infrastructure from OpenStreetMap via Overpass API. Returns up to 7 categories: hospitals, shelters, community centres, schools, police stations, fire stations, and pharmacies.

**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lat` | float | Yes | — | Latitude (-90 to 90) |
| `lng` | float | Yes | — | Longitude (-180 to 180) |
| `radius` | int | No | 10000 | Search radius in meters (100 to 100000) |

**Response:**
```json
{
  "hospitals": [
    {
      "name": "General Hospital",
      "latitude": 28.6268,
      "longitude": 77.2183,
      "distance": 2.189,
      "address": "40, Tolstoy Rd, New Delhi"
    }
  ],
  "shelters": [],
  "community_centres": [],
  "schools": [],
  "police": [],
  "firestations": [],
  "pharmacies": []
}
```

### GET /api/location/safe-destination

Get the single best safe destination scored by weighted distance.

**Authentication:** None

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lat` | float | Yes | — | Latitude (-90 to 90) |
| `lng` | float | Yes | — | Longitude (-180 to 180) |
| `radius` | int | No | 10000 | Search radius in meters (100 to 100000) |

**Scoring Weights:** shelter=1.0, community_centre=1.3, school=1.5, hospital=2.0, police=2.3, firestation=2.6

---

## AI

### POST /api/ai/recommendation

Get an AI-powered disaster recommendation. Routes through a LangGraph multi-agent pipeline (Weather, Alert, Infrastructure, Route, Coordinator agents). Returns structured recommendation with risk level, summary, destination, reasoning, and actionable steps.

**Authentication:** None

**Request Body:**
```json
{
  "question": "Should I evacuate?",
  "lat": 28.6139,
  "lng": 77.2090,
  "incident_id": "uuid-string"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | User's emergency question |
| `lat` | float | No | User's current latitude |
| `lng` | float | No | User's current longitude |
| `incident_id` | string | No | UUID for incident memory preservation |

**Response:**
```json
{
  "riskLevel": "high",
  "summary": "Severe weather conditions detected in your area.",
  "recommendedDestination": {
    "type": "shelter",
    "name": "Community Shelter A"
  },
  "reason": "Multiple factors indicate elevated risk...",
  "actions": [
    "Move to higher ground immediately",
    "Take emergency supply kit",
    "Proceed to nearest shelter: Community Shelter A (1.2 km)"
  ]
}
```

---

## Admin Dashboard

All admin endpoints require administrator authentication (`role: admin`).

### GET /api/admin/overview

Get summary statistics for the admin dashboard.

**Authentication:** Required (admin)

**Response:**
```json
{
  "active_alerts": 5,
  "active_sos": 3,
  "people_in_affected_zones": 42,
  "people_marked_safe": 12,
  "people_requiring_help": 2,
  "available_responders": 8,
  "active_response_tasks": 3
}
```

| Field | Type | Description |
|-------|------|-------------|
| `active_alerts` | int | Number of active government CAP alerts |
| `active_sos` | int | Number of active SOS incidents (all non-resolved statuses) |
| `people_in_affected_zones` | int | Users with recent location in alert areas (24h) |
| `people_marked_safe` | int | Resolved SOS where victim confirmed safe |
| `people_requiring_help` | int | Active SOS without assigned responder |
| `available_responders` | int | Online users with location sharing enabled |
| `active_response_tasks` | int | SOS with responder en route or helping |

### GET /api/admin/alerts

List all active government alerts with full location data.

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `active_only` | bool | No | true | Filter to active alerts only |
| `limit` | int | No | 100 | Maximum results (1-500) |
| `offset` | int | No | 0 | Pagination offset |

**Response:** Array of alert objects with `locations` array for multi-district alerts.

### GET /api/admin/sos

List SOS incidents with optional status filter.

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status_filter` | string | No | — | Filter by SOS status (e.g., "active", "responder_accepted") |
| `limit` | int | No | 100 | Maximum results (1-500) |
| `offset` | int | No | 0 | Pagination offset |

**Response:** Array of SOS incidents with victim/responder names.

### GET /api/admin/responders

List nearby available responders (online users with location sharing).

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `active_only` | bool | No | true | Only online users with recent location |
| `limit` | int | No | 100 | Maximum results (1-500) |
| `offset` | int | No | 0 | Pagination offset |

**Response:** Array of users with location and active SOS info.

### GET /api/admin/users

List all users with location data.

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | int | No | 100 | Maximum results (1-500) |
| `offset` | int | No | 0 | Pagination offset |

### GET /api/admin/incidents

SOS incident history with filtering.

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status_filter` | string | No | — | Filter by SOS status |
| `date_from` | datetime | No | — | Filter from date (ISO 8601) |
| `date_to` | datetime | No | — | Filter to date (ISO 8601) |
| `limit` | int | No | 100 | Maximum results (1-500) |
| `offset` | int | No | 0 | Pagination offset |

### GET /api/admin/zone-stats

Statistics for a specific disaster/alert affected zone.

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `disaster_id` | int | No | — | Disaster ID for zone center |
| `alert_id` | int | No | — | Alert ID for zone center |

**Response:**
```json
{
  "total_people_detected": 42,
  "people_requiring_help": 2,
  "active_sos": 3,
  "people_helped": 5,
  "people_marked_safe": 12,
  "responders_active": 8
}
```

### POST /api/admin/sos/{sos_id}/acknowledge

Acknowledge an SOS incident (admin action).

**Authentication:** Required (admin)

**Response:** `{ "success": true, "sos_id": 1, "status": "acknowledged" }`

### POST /api/admin/sos/{sos_id}/assign

Assign a responder to an SOS incident.

**Authentication:** Required (admin)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `responder_id` | int | Yes | User ID of responder to assign |

**Response:** `{ "success": true, "sos_id": 1, "responder_id": 5, "status": "responder_assigned" }`

### POST /api/admin/sos/{sos_id}/status

Admin override SOS status.

**Authentication:** Required (admin)

**Request Body:**
```json
{
  "status": "responder_assigned"
}
```

**Response:** `{ "success": true, "sos_id": 1, "status": "responder_assigned" }`

---

## SOS

### POST /api/sos

Create a new SOS incident.

**Authentication:** Required (user)

**Request Body:**
```json
{
  "latitude": 28.6139,
  "longitude": 77.2090,
  "accuracy": 10.5,
  "timestamp": 1699999999000,
  "emergency_type": "medical",
  "emergency_details": "Heart attack symptoms"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `latitude` | float | Yes | Latitude (-90 to 90) |
| `longitude` | float | Yes | Longitude (-180 to 180) |
| `accuracy` | float | No | GPS accuracy in meters |
| `timestamp` | int | No | Client timestamp (milliseconds) |
| `emergency_type` | string | No | Type of emergency |
| `emergency_details` | string | No | Additional details |

**Response (201):** SOS incident object with `id`, `status: "active"`, timestamps.

### GET /api/sos/active

Get the current user's active SOS (as victim or responder).

**Authentication:** Required (user)

**Response:**
```json
{
  "sos": { ... SOS incident or null ... },
  "is_responder": false,
  "responder_sos": { ... SOS incident or null ... }
}
```

### GET /api/sos/nearby

Get nearby active SOS incidents within radius.

**Authentication:** Required (user)

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `lat` | float | Yes | — | Latitude |
| `lng` | float | Yes | — | Longitude |
| `radius_km` | float | No | 10 | Search radius (0.1-50 km) |

**Response:** Array of nearby SOS with victim name, distance, emergency type.

### GET /api/sos/{sos_id}

Get SOS incident details (victim, responder, or admin only).

**Authentication:** Required (user)

**Response:** Full SOS incident with victim/responder names.

### POST /api/sos/{sos_id}/cancel

Cancel own SOS (victim only).

**Authentication:** Required (user - must be victim)

### POST /api/sos/{sos_id}/accept

Accept nearby SOS as responder.

**Authentication:** Required (user - must not be victim)

**Response:** Updated SOS with `assigned_responder_id`, `status: "responder_accepted"`, `accepted_at`.

### POST /api/sos/{sos_id}/status

Update SOS status (victim, responder, or admin).

**Authentication:** Required (user)

**Request Body:**
```json
{
  "status": "assistance_in_progress"
}
```

**Valid Transitions:**
- Victim: `active` → `cancelled`, `assistance_provided` → `user_confirmed_safe` → `resolved`
- Responder: `responder_accepted` → `assistance_in_progress` → `assistance_provided`
- Admin: Any status to any status

### POST /api/sos/{sos_id}/confirm-safe

Victim confirms they are safe (resolves SOS).

**Authentication:** Required (user - must be victim)

### GET /api/sos/my/history

Get current user's SOS history.

**Authentication:** Required (user)

**Query Parameters:** `limit` (default 50), `offset` (default 0)

### Admin SOS Endpoints

#### GET /api/sos/admin/active

Get all active SOS incidents (admin only).

#### GET /api/sos/admin/history

Get resolved SOS incident history (admin only).

**Query Parameters:** `limit` (default 50), `offset` (default 0)

#### POST /api/sos/admin/{sos_id}/responder

Admin assign/remove responder.

**Query Parameters:** `responder_id` (optional - omit to unassign)

**Response:** Updated SOS with responder assignment.
