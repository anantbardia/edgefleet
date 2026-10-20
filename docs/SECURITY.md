# EdgeFleet Security & Threat Model

## 1. Authentication & Role-Based Access Control (RBAC)

EdgeFleet implements strict Role-Based Access Control across all HTTP endpoints and WebSocket interactions:

| Role | Hierarchy Level | Capabilities |
| :--- | :---: | :--- |
| **Viewer** | 1 | Read-only inspection of devices, telemetry history, firmware releases, deployment logs, and alerts. |
| **Operator** | 2 | All Viewer permissions + launch deployments, abort safe deployments, upload firmware releases, acknowledge alerts, trigger cloud sync. |
| **Admin** | 3 | Full administrative authority: approve firmware releases, register/deregister hardware nodes, manage user accounts, inspect raw security audit logs. |

### Token Architecture
- **Access Tokens**: Short-lived (30 minutes), signed with HMAC-SHA256 (`HS256`).
- **Refresh Tokens**: Long-lived (7 days), exchanged at `/api/auth/refresh` to maintain continuous operations without operator re-authentication.
- **Passwords**: Hashed with salted bcrypt (`$2b$12$...`). Plaintext passwords are never stored, logged, or exposed in error traces.

---

## 2. Firmware Validation & Execution Defenses

Uploaded firmware artifacts represent a critical attack vector in IoT environments. EdgeFleet enforces five layers of defense:

1. **Storage Sandboxing**: All binaries are stored outside the Nginx web root in `/var/lib/edgefleet/firmware/` with strict `0640` file permissions owned by the unprivileged `edgefleet` system user. They are never executable on the gateway.
2. **Streaming SHA-256 Digest**: The backend reads incoming multipart chunks and computes the cryptographic SHA-256 hash in memory. Uploaded filenames are discarded; storage paths use `{mcu_family}_{version}_{sha256[:8]}.{ext}`.
3. **Extension & Header Validation**:
   - `ESP32`: Only `.bin` binaries containing valid ESP-IDF image magic headers (`0xE9`) are permitted.
   - `Arduino Uno`: Only `.hex` files matching Intel HEX record formats (`:10...`) are permitted.
4. **Mandatory Administrative Approval**: Uploaded releases cannot be deployed until an Admin explicitly marks `is_approved = True`.
5. **Preflight Compatibility Enforcer**: Deployments fail preflight if the firmware target architecture does not match the node's MCU family.

---

## 3. Safe Subprocess Execution (avrdude)

When flashing Arduino Uno hardware via USB serial, EdgeFleet enforces zero-trust subprocess constraints:
- **No Shell Interpolation**: Subprocesses are spawned exclusively via `asyncio.create_subprocess_exec` passing an immutable argument array. `shell=True` is strictly prohibited throughout the entire codebase.
- **Fixed Binary Path**: The `avrdude` executable path is resolved from system configuration (`/usr/bin/avrdude`), never accepted from client requests.
- **Exclusive Port Lock**: An asynchronous lock ensures simultaneous deployments cannot access the same `/dev/ttyACM*` port.
- **Enforced Timeout**: Flash operations enforce an absolute 120-second timeout to prevent process hanging.

---

## 4. Cancellation Safety State Machine

Deployments adhere to a strict state machine:
- **Safe Cancellation States**: `QUEUED`, `PREFLIGHT`, `TRANSFERRING`, `VERIFYING`. Cancelling during these states halts the operation cleanly and leaves the target device on its current firmware.
- **Unsafe Cancellation States**: `INSTALLING`, `REBOOTING`. The deployment engine explicitly rejects cancellation requests during flash writes to prevent bricking the physical microcontroller.

---

## 5. Rate Limiting

The gateway API employs `SlowAPI` token-bucket rate limiting:
- `POST /api/auth/login`: Maximum 5 requests per minute per IP (brute-force defense).
- `POST /api/firmware/upload`: Maximum 10 uploads per minute.
- General API: 100 requests per minute per IP.
