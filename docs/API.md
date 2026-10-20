# EdgeFleet REST & WebSocket API Specification

All API endpoints are served under `/api` with JSON payloads. Interactive Swagger UI is accessible at `/api/docs` and OpenAPI JSON at `/api/openapi.json`.

---

## 1. Authentication

Protected endpoints require a Bearer token in the `Authorization` header:
```http
Authorization: Bearer <access_token>
```

### `POST /api/auth/login`
Authenticate with email and password.
- **Request Body**:
  ```json
  {
    "email": "operator@edgefleet.local",
    "password": "operatorpassword123"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### `POST /api/auth/refresh`
Exchange a valid refresh token for a new access token.

### `GET /api/auth/me`
Retrieve profile of currently authenticated user.

---

## 2. Devices

### `GET /api/devices`
List registered fleet nodes with pagination and filtering.
- **Query Parameters**:
  - `page` (default 1), `page_size` (default 20, max 100)
  - `mcu_family`: `esp32` | `arduino_uno`
  - `is_online`: `true` | `false`
  - `search`: string matching ID, name, or IP

### `POST /api/devices` *(Admin only)*
Register a new microcontroller in the fleet.
- **Request Body**:
  ```json
  {
    "device_id": "esp32-004",
    "name": "Substation Climate Sensor",
    "mcu_family": "esp32",
    "board_variant": "esp32-wroom-32"
  }
  ```

### `GET /api/devices/{device_id}`
Retrieve complete diagnostic metadata for a single device.

---

## 3. Telemetry

### `GET /api/devices/{device_id}/telemetry`
Query historical telemetry time-series points.
- **Query Parameters**:
  - `page`, `page_size` (max 500)
  - `start_time`, `end_time` (ISO-8601 strings)

### `GET /api/devices/{device_id}/telemetry/latest`
Retrieve the most recent telemetry sample emitted by the device.

---

## 4. Firmware Releases

### `GET /api/firmware`
Query registered firmware images. Filter by `mcu_family` or `is_approved`.

### `POST /api/firmware/upload` *(Operator+)*
Upload a new firmware binary (`multipart/form-data`).
- **Form Fields**:
  - `file`: binary `.bin` or `.hex`
  - `version`: version string (e.g. `1.2.0`)
  - `mcu_family`: `esp32` | `arduino_uno`
  - `target_boards`: JSON string array, e.g. `["esp32-wroom-32"]`
  - `release_notes`: text

### `PATCH /api/firmware/{release_id}` *(Admin only)*
Approve or reject a firmware release:
```json
{
  "is_approved": true
}
```

---

## 5. Deployments

### `POST /api/deployments/preflight`
Run non-destructive hardware compatibility checks.
- **Request Body**:
  ```json
  {
    "device_ids": ["esp32-001"],
    "release_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "results": [
      {
        "device_id": "esp32-001",
        "compatible": true,
        "warnings": [],
        "errors": []
      }
    ],
    "all_compatible": true,
    "confirmation_token": "eyJhbGciOi..."
  }
  ```

### `POST /api/deployments` *(Operator+)*
Launch a firmware rollout. Requires `confirmation_token` returned by preflight.

### `POST /api/deployments/{id}/cancel` *(Operator+)*
Safely cancel an in-flight deployment (only permitted during `QUEUED`, `PREFLIGHT`, `TRANSFERRING`, or `VERIFYING`).

---

## 6. WebSocket Real-Time Stream

Connect to `ws://<gateway-ip>/api/ws` or `wss://<cloud-domain>/ws`.

### Inbound Events to Browser
- `telemetry`: `{"type": "telemetry", "device_id": "...", "readings": {...}}`
- `device_status`: `{"type": "device_status", "device_id": "...", "is_online": true}`
- `deployment_update`: `{"type": "deployment_update", "deployment_id": "...", "state": "INSTALLING"}`
- `alert`: `{"type": "alert", "alert": {...}}`
