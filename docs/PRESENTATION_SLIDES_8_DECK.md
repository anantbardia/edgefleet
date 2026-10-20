# EdgeFleet: Presentation Slide Deck (8 Core Slides)

---

## Slide 1: The Problem — The IoT Maintenance & Update Challenge

### Slide Title
**The Challenge: Managing & Updating Distributed IoT Microcontrollers**

### Key Takeaway
Remote microcontrollers are hard to reach, risky to update, and vulnerable to catastrophic failure ("bricking").

### Slide Content (Bullet Points)
- **Physically Inaccessible Hardware**: IoT nodes are installed in remote, hazardous, or elevated locations (factory machinery, agricultural fields, utility poles) where physical maintenance is costly and impractical.
- **The "Bricking" Risk**: A dropped network packet, power cut, or corrupted binary during a firmware flash can leave a microcontroller permanently disabled, requiring on-site replacement.
- **Heterogeneous Environments**: Fleets consist of mixed hardware—modern 32-bit Wi-Fi microcontrollers (**ESP32-C3 Mini**) alongside rugged 8-bit industrial controllers (**Arduino Uno**).
- **Single-Point Cloud Vulnerability**: Cloud-only IoT platforms (Blynk, ThingSpeak, AWS IoT) require constant internet, incur recurring subscription costs, and fail when local network connectivity drops.

### Visual Recommendation
- Contrast graphic: An engineer with a ladder and laptop cable vs. a central dashboard sending a wireless update signal.

---

## Slide 2: The Solution — EdgeFleet Platform Overview

### Slide Title
**EdgeFleet: Edge-Native Fleet Management & Safe FOTA Platform**

### Key Takeaway
A local edge gateway that unifies heterogeneous microcontrollers with safe remote updates and real-time observability.

### Slide Content (Bullet Points)
- **Autonomous Local Gateway**: Powered by a Raspberry Pi 4 operating on-premise, allowing full fleet management even without public internet connectivity.
- **Multi-Architecture Support**: Centrally manages both wireless **ESP32-C3 Mini** nodes (via Wi-Fi) and wired **Arduino Uno** nodes (via USB serial).
- **Fail-Safe Firmware Over-The-Air (FOTA)**: Atomic updates with preflight hardware checks and automatic rollback protection.
- **Real-Time Web Dashboard**: A single browser-based interface for telemetry monitoring, device health tracking, and 1-click deployments.

### Visual Recommendation
- Diagram showing the **Raspberry Pi Gateway** in the center communicating with **ESP32-C3** nodes over Wi-Fi and **Arduino Uno** nodes over USB, with a browser interface connected to the gateway.

---

## Slide 3: System Architecture — 3-Tier Edge-Native Design

### Slide Title
**System Architecture: 3-Tier Layered Hierarchy**

### Key Takeaway
Clean separation between operator presentation, edge gateway orchestration, and physical microcontroller execution.

### Slide Content (Bullet Points)
- **Tier 1: Operator Presentation Layer (Frontend)**
  - Web dashboard built with **React 18** and **TypeScript**.
  - Bidirectional **WebSockets** for sub-second telemetry and live deployment tracking.
- **Tier 2: Edge Gateway Controller (Raspberry Pi 4)**
  - **FastAPI Engine**: Asynchronous core handling API requests, RBAC security, and deployment pipelines.
  - **Mosquitto MQTT Broker**: Lightweight pub/sub messaging engine for high-frequency telemetry.
  - **Local SQLite Database (WAL Mode)**: High-speed concurrent local storage for fleet logs and firmware releases.
- **Tier 3: Distributed Edge Hardware (Physical Nodes)**
  - **ESP32-C3 Mini**: 32-bit RISC-V core with Wi-Fi, dual-partition A/B flash, and onboard status LEDs.
  - **Arduino Uno**: 8-bit AVR ATmega328P connected via USB serial for rugged sensing.

### Visual Recommendation
- 3 horizontal layer blocks:
  - Top Block: `Web Dashboard (React + WebSockets)`
  - Middle Block: `Raspberry Pi 4 Gateway (FastAPI + Mosquitto + SQLite)`
  - Bottom Block: `Edge Nodes (ESP32-C3 Mini [Wi-Fi] + Arduino Uno [USB])`

---

## Slide 4: System Architecture Flow — How Data & Updates Move

### Slide Title
**System Architecture Flow: Data Ingestion & FOTA Execution Pipeline**

### Key Takeaway
Optimized dual-channel communication: lightweight MQTT for commands and telemetry; high-throughput HTTP for firmware streaming.

### Slide Content (Bullet Points)
1. **Telemetry Pipeline**: Microcontrollers publish sensor metrics to MQTT broker every 5s ➔ Gateway broadcasts to Dashboard via WebSockets.
2. **Preflight Safety Gate**: Gateway validates firmware target compatibility before dispatch (prevents flashing Arduino code onto an ESP32).
3. **Command Dispatch**: Gateway dispatches an update trigger command containing SHA-256 hash and download URL via MQTT.
4. **Local HTTP Binary Stream**: ESP32-C3 downloads the 1.1 MB binary directly from the local gateway IP (`10.202.94.199`) in under 4 seconds.
5. **Flash & Self-Test**: ESP32 verifies checksum, reboots into the new firmware, and reports online status.

### Flow Diagram for Slide
```
[ Operator Dashboard ]
         │  1. Initiate Deployment (HTTPS/WSS)
         ▼
[ Raspberry Pi 4 Gateway ]
   ├── 2. Preflight Safety Check (Validates board & binary)
   ├── 3. Sends Trigger Command via MQTT (Port 1883)
   │               │
   │               ▼
   │      [ ESP32-C3 Mini Node ]
   │               │
   └── 4. Streams 1.1 MB Binary via local HTTP (Port 80)
                   │
                   ▼
          [ ESP32-C3 Mini Node ]
          5. Writes to Inactive Partition
          6. Verifies SHA-256 Checksum
          7. Reboots into New Version & Confirms Online
```

---

## Slide 5: Safety Innovation — How EdgeFleet Prevents "Bricking"

### Slide Title
**Fail-Safe Firmware Updates: Dual-Partition (A/B) Architecture**

### Key Takeaway
Zero risk of bricking: the active firmware is never overwritten until the new version is completely downloaded and verified.

### Slide Content (Bullet Points)
- **Preflight Compatibility Gate**:
  - Automatically matches MCU family and board variant before deployment dispatch.
- **Dual A/B Partition Layout**:
  - Memory is split into two independent slots: **Slot A** and **Slot B**.
  - While the device runs safely on **Slot A**, the new update streams into inactive **Slot B**.
- **Cryptographic SHA-256 Verification**:
  - The device computes the hash of the downloaded image; if corrupted, the partition is rejected before reboot.
- **Hardware Watchdog & Automatic Rollback**:
  - If a power interruption occurs during download: **Slot A remains 100% intact**.
  - If the new firmware crashes or fails to connect: The bootloader automatically rolls back to **Slot A**.

### Visual Recommendation
- Side-by-side comparison diagram:
  - *Standard Flashing*: In-place overwrite ➔ Network drop ➔ Device dead ❌
  - *EdgeFleet A/B*: Background write to Slot B ➔ Verify ➔ Safe Switch / Auto Rollback ✅

---

## Slide 6: Real-World Applications

### Slide Title
**Real-World Applications: Domain-Specific Deployments**

### Key Takeaway
EdgeFleet provides centralized lifecycle management across diverse industrial and municipal environments.

### Slide Content (4 Key Application Quadrants)
1. **Industrial IoT (IIoT) & Factory Automation**:
   - Machinery vibration, motor RPM, and thermal monitoring.
   - Update anomaly detection thresholds across 50+ machines simultaneously without halting assembly lines.
2. **Smart Agriculture & Precision Farming**:
   - Soil moisture, nutrient, and environmental sensors across acres of land.
   - Central farmhouse gateway updates irrigation schedules and sleep algorithms wirelessly.
3. **Smart Cities & Infrastructure**:
   - Connected streetlights, automated water metering, and parking vacancy sensors.
   - Push security patches across city blocks without sending maintenance trucks.
4. **Hazardous Environmental Monitoring**:
   - Flood detection, wildfire monitoring, and air quality nodes in dangerous or remote terrain.
   - Updates dispatched safely from a distance with zero physical contact required.

### Visual Recommendation
- 4-quadrant layout with clean icons: Factory Gear (IIoT), Crop Sprout (Agriculture), City Skyline (Smart Cities), Weather/Shield (Environment).

---

## Slide 7: Technical Stack & Practical Implementation

### Slide Title
**Technical Stack & Engineering Highlights**

### Key Takeaway
Production-grade open-source technologies integrated into a lightweight, cost-effective edge system.

### Slide Content (Component Table)
| Layer | Technologies Used | Role in System |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, WebSockets | Real-time control dashboard & telemetry visualization |
| **Gateway Core** | Python 3.11, FastAPI, SQLite (WAL Mode) | Asynchronous device orchestration & local database |
| **Messaging** | Mosquitto MQTT v2.0 (Port 1883), HTTP/1.1 | Telemetry pub/sub & high-speed binary delivery |
| **Security** | JWT Tokens, bcrypt, Cloudflare Zero Trust | Secure role-based login & encrypted remote ingress |
| **Edge Hardware** | ESP32-C3 Mini (RISC-V) & Arduino Uno (AVR) | Wi-Fi sensing node & USB serial sensor node |

### Key Practical Highlights
- **Ultra-Low Resource Footprint**: Entire gateway runs on a 2 GB Raspberry Pi 4 using under 350 MB RAM.
- **Zero Cloud Costs**: Operates independently on local network; optional public access via free Cloudflare Tunnel without port-forwarding.
- **Real Working Prototype**: Live physical demonstration with active telemetry streaming and over-the-air updates.

---

## Slide 8: Validated Results & Future Scope

### Slide Title
**Current Capabilities & Future Engineering Scope**

### Key Takeaway
A fully functional, benchmarked working prototype ready for real-world deployment and future enhancements.

### Slide Content (Two Columns)

#### Column 1: Validated Results (Working Today)
- **Fast Wi-Fi FOTA**: ESP32-C3 Mini downloads and flashes 1.1 MB firmware in under **4.5 seconds**.
- **Serial Programming**: Arduino Uno flashed over USB serial via automated `avrdude` STK500 pipeline.
- **Live Telemetry & Alerts**: Sensor telemetry streaming every 5 seconds with automatic offline detection.
- **Safety Verified**: Preflight gate blocks mismatched binaries; A/B rollback protects against failed boots.

#### Column 2: Future Scope (Roadmap)
- **Hardware-Enforced Cryptographic Signing**: Embedding Ed25519 public keys in hardware eFuses to prevent unauthorized firmware execution.
- **Peer-to-Peer Mesh Updates (ESP-NOW)**: Allowing Wi-Fi nodes to daisy-chain firmware to nodes located outside router range.
- **Binary Delta Updates**: Generating binary diffs to reduce update transfer sizes from 1.1 MB to ~50 KB for cellular IoT.

### Visual Recommendation
- Left side: Green checkmark badges for current working achievements.
- Right side: Forward-arrow milestone cards for future enhancements.
