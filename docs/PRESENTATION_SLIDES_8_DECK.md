# EdgeFleet: 8-Slide Technical Presentation Deck & Diagram Guide

> **Note for Presenter**: This presentation is structured as **8 core content slides** (excluding Title and Thank You slides) optimized for academic defense, capstone evaluations, and technical conferences. Each slide provides exact slide bullet points, visual layout instructions, and speaker notes.

---

## Slide 1: The Edge IoT Dilemma — Problem Statement & Motivation

### Slide Title
**The Edge IoT Dilemma: Firmware Fragility and Lifecycle Management in Distributed Fleets**

### Key Content Points
- **The Explosion of Edge Heterogeneity**: Modern IoT deployments mix 8-bit CISC/AVR microcontrollers (legacy sensors, motor drivers) with 32-bit RISC-V nodes (Wi-Fi/BLE edge devices).
- **The "Bricking" Catastrophe**:
  - Pushing an incompatible binary or experiencing a power/network drop during an in-place flash renders field nodes permanently non-bootable.
  - Requires physical truck rolls, manual disassembly, and specialized programmer hardware (ISP/JTAG).
- **Network & Cloud Vulnerabilities**:
  - Over-reliance on monolithic cloud platforms (AWS Greengrass, Azure IoT Hub, Blynk) introduces bandwidth costs, latency, and single-point-of-failure outages.
  - Absence of edge preflight checks permits accidental deployment of mismatched architectures.
- **Project Problem Statement**:
  > *"To design and implement an edge-native, zero-trust IoT fleet management and secure Over-The-Air (FOTA) platform capable of coordinating heterogeneous microcontrollers with atomic failover, preflight safety gates, and real-time observability without mandatory cloud dependency."*

### Visual Layout Recommendation
- **Left Column**: Diagram showing a truck technician driving to a broken utility pole ("The Cost of Bricking: $500/truck roll").
- **Right Column**: Highlighted callout box with the formal Problem Statement and 4 key challenge badges: `Heterogeneity`, `Bricking Risk`, `Unstable Networks`, `Cloud Lock-in`.

### Speaker Notes
*"Good morning. In modern industrial and smart city deployments, edge microcontrollers are installed in places where humans cannot easily reach them. When you have hundreds of devices running different chips—like an 8-bit Arduino on a machine and a 32-bit ESP32-C3 on Wi-Fi—updating firmware remotely is terrifying. One corrupted byte or power interruption can permanently brick a device. EdgeFleet was engineered from the ground up to eliminate this risk."*

---

## Slide 2: Proposed Solution — The EdgeFleet Paradigm

### Slide Title
**EdgeFleet: Edge-Native Heterogeneous Fleet Orchestration & Secure FOTA**

### Key Content Points
- **Decentralized Edge Gateway Paradigm**:
  - Utilizes an on-premise Raspberry Pi 4 as an autonomous local edge gateway controller.
  - Local nodes communicate locally via high-speed Wi-Fi (MQTT/HTTP) and USB Serial without routing internal device traffic through third-party public clouds.
- **Architectural Safety Innovations**:
  - **Preflight Compatibility Gate**: Gateway verifies MCU family, target board variants, and connection health before dispatching payloads.
  - **Dual-Partition (A/B) Atomic Updates**: Firmware is written to an inactive flash partition; if the new version fails self-test, the hardware watchdog automatically reverts to the known-good partition.
  - **Universal Flashing Engine**: Seamlessly coordinates both IP-based Wi-Fi OTA and physical serial flashing (STK500 protocol via `avrdude`).
- **Cloudflare Zero-Trust Remote Ingress**:
  - Secure global dashboard access via encrypted tunnels (`cloudflared`) without open inbound firewall ports or dynamic DNS configurations.

### Visual Layout Recommendation
- High-level block diagram contrasting traditional **Cloud-Only IoT Architecture** (vulnerable, high latency) vs. **EdgeFleet Gateway Architecture** (secure, local autonomy, zero-trust cloud uplink).

### Speaker Notes
*"Rather than connecting every tiny microcontroller directly to the public internet, EdgeFleet introduces an intelligent edge gateway on a Raspberry Pi. It acts as the local air-traffic controller. It inspects every update before it is sent, supervises both wireless ESP32-C3 nodes and wired Arduino nodes, and provides operators with a real-time reactive dashboard from anywhere in the world using encrypted Cloudflare tunnels."*

---

## Slide 3: Detailed System Architecture & Hardware Topology

### Slide Title
**Hierarchical System Architecture: Gateway, Networks & Edge Nodes**

### Key Content Points
- **Tier 1: Global Operator Interface (SPA)**:
  - React 18, TypeScript, and Vite running an industrial dark-mode control interface.
  - Bidirectional WebSockets for sub-second telemetry and deployment stage tracking.
- **Tier 2: Raspberry Pi 4 Edge Gateway (Brain)**:
  - **Nginx Reverse Proxy**: Single ingress point terminating SSL and routing web traffic to API services.
  - **FastAPI Core Engine**: Asynchronous Python event loop handling REST transactions, RBAC authentication, and deployment jobs.
  - **Mosquitto MQTT Broker**: High-throughput message bus for lightweight telemetry and low-latency command dispatch.
  - **SQLite Database with WAL Mode**: Embedded zero-maintenance datastore enabling concurrent async reads and writes.
- **Tier 3: Distributed Heterogeneous Edge Nodes**:
  - **ESP32-C3 Mini Node**: 32-bit RISC-V core operating over 2.4 GHz Wi-Fi with dual A/B partitions and dual-pin status indication (GPIO 8/7).
  - **Arduino Uno Node**: 8-bit AVR ATmega328P connected via USB Serial running Optiboot bootloader flashed directly by gateway `avrdude` daemon.

### Visual Layout Recommendation
- 3-tier horizontal architecture diagram showing **Frontend UI** ➔ **Raspberry Pi 4 Gateway** ➔ **Field Nodes (ESP32-C3 Mini + Arduino Uno)** with distinct protocol labels (`WSS`, `HTTP REST`, `MQTT (1883)`, `USB Serial (/dev/ttyACM0)`).

### Speaker Notes
*"Here we see the 3-tier architecture. On top is the operator dashboard. In the center is the Raspberry Pi 4 running our FastAPI orchestration engine and Mosquitto MQTT broker. At the bottom are the field devices. What makes EdgeFleet unique is its ability to handle both modern 32-bit RISC-V Wi-Fi microcontrollers and legacy 8-bit AVR microcontrollers under one unified lifecycle registry."*

---

## Slide 4: System Architecture Flow Diagram & Interaction Workflow

### Slide Title
**System Architecture Flow Diagram: End-to-End Data & Command Pipeline**

### Visual Diagram (Instructions for PPT Diagram Tool / Draw.io / Mermaid)
> **Diagram Generation Prompt / Instructions**:
> Create a clean left-to-right sequence and flow block diagram featuring 4 distinct functional blocks:
> 1. `Operator Browser (React SPA)`
> 2. `Cloudflare Edge & Gateway Reverse Proxy (Nginx)`
> 3. `FastAPI Orchestrator & MQTT Broker (Raspberry Pi 4)`
> 4. `Physical Microcontrollers (ESP32-C3 Mini via Wi-Fi & Arduino Uno via USB)`
> Connect them with color-coded arrows representing: **Telemetry (Blue)**, **OTA Commands (Orange)**, **Binary Payloads (Green)**, and **Heartbeats/LWT (Red)**.

```mermaid
graph TD
    subgraph Client ["Operator Layer"]
        A[Dashboard Browser / Mobile UI]
    end

    subgraph Ingress ["Ingress & Security"]
        B[Cloudflare Zero-Trust Tunnel]
        C[Nginx Reverse Proxy :80]
    end

    subgraph Gateway ["Raspberry Pi 4 Gateway (10.202.94.199)"]
        D[FastAPI Application Server]
        E[(SQLite WAL Database)]
        F[Mosquitto MQTT Broker :1883]
        G[ESP32 OTA Adapter]
        H[Arduino Serial Adapter / avrdude]
    end

    subgraph Nodes ["Heterogeneous Edge Nodes"]
        I[ESP32-C3 Mini Wi-Fi Node<br/>RISC-V | Dual Partition A/B]
        J[Arduino Uno Hardware Node<br/>ATmega328P | Optiboot USB]
    end

    A <==>|HTTPS / WSS| B
    B -->|Proxy Pass| C
    C -->|API / WebSockets| D
    D <--> E
    D <-->|Internal Pub/Sub| F
    D -->|Coordinate OTA| G
    D -->|Coordinate Flash| H

    F <==>|MQTT Telemetry & Commands| I
    G ==>|HTTP Binary Stream| I
    H ==>|USB Serial 115200 STK500| J
    I -.->|LWT Offline Detection| F
```

### Flow Diagram Key Stages
1. **Telemetry Loop**: Nodes publish sensor data to MQTT ➔ Broker forwards to FastAPI ➔ Gateway broadcasts to UI via WebSockets.
2. **Command Dispatch**: User initiates update ➔ Gateway checks preflight ➔ Publishes command over MQTT.
3. **Firmware Stream**: ESP32-C3 streams binary via HTTP directly from local gateway IP (`10.202.94.199`).
4. **Heartbeat & LWT**: Mosquitto automatically flags dead nodes if MQTT keepalive expires.

### Speaker Notes
*"This diagram highlights the data flow. Notice the dual paths: telemetry travels upstream in blue over MQTT and WebSockets, giving operators instant sub-second feedback. When an update is deployed, the command travels in orange over MQTT, but the heavy 1.1-megabyte binary is streamed in green directly over local high-speed HTTP, conserving broker bandwidth. Meanwhile, the Arduino is flashed via dedicated USB STK500 protocol."*

---

## Slide 5: Core Working — Secure FOTA Lifecycle & Fail-Safe Mechanics

### Slide Title
**FOTA Execution Engine: Zero-Downtime Atomic A/B Updates**

### Key Content Points
1. **Stage 1: Preflight Verification**:
   - Validates MCU family (`esp32` == `esp32`), target board compatibility (`ESP32-C3`), and ensures device is online (`is_online == True`). Prevents bricking before dispatch.
2. **Stage 2: Orchestrated MQTT Command**:
   - Dispatches download URL (`http://10.202.94.199/api/firmware/{id}/download`), SHA-256 hash, and deployment token.
3. **Stage 3: Streaming to Inactive Partition (`ota_1`)**:
   - ESP32-C3 continues running application code in `ota_0` while writing incoming stream into `ota_1`.
4. **Stage 4: Cryptographic Integrity Verification**:
   - ESP32 computes SHA-256 hash of written bytes. If hash mismatches, partition is discarded immediately.
5. **Stage 5: Bootloader Switch & Self-Test Verification**:
   - `otadata` flags are updated to boot `ota_1`.
   - Node reboots into new version (v1.1.0).
   - If boot crashes or watchdog timer fires before health confirmation, hardware rolls back into `ota_0`.
6. **Stage 6: Status Confirmation**:
   - Node connects to Wi-Fi, publishes `status: online` with `version: 1.1.0`. Deployment marked `SUCCESS`.

### Visual Layout Recommendation
- 6-step horizontal timeline with icons for each stage: `Preflight (Shield)` ➔ `Dispatch (Signal)` ➔ `Stream (Download)` ➔ `Verify (Key)` ➔ `Reboot (Cycle)` ➔ `Success (Checkmark)`.

### Speaker Notes
*"Let's examine what happens during an actual update on the ESP32-C3 Mini. At no point is the active application wiped before the new one is verified. The device downloads the new code into an inactive second partition. If power cuts out mid-download, the device simply reboots into its existing software as if nothing happened. Only after the entire 1.1 megabytes are validated against the SHA-256 checksum does the bootloader switch partitions."*

---

## Slide 6: Real-World Applications & Industrial Case Studies

### Slide Title
**Real-World Applications: Where EdgeFleet Makes an Impact**

### Key Content Points
- **1. Industrial IoT (IIoT) & Predictive Maintenance**:
  - Deployments in manufacturing facilities where microcontrollers monitor motor vibration, temperature, and current draw.
  - EdgeFleet enables updating sensor threshold algorithms across 100+ machines simultaneously without factory floor shutdown.
- **2. Smart Agriculture & Precision Farming**:
  - Solar-powered ESP32 nodes measuring soil moisture, NPK levels, and ambient climate across remote acres.
  - Gateway installed on farm silo updates irrigation firmware over Wi-Fi without requiring farmers to walk fields with laptops.
- **3. Smart Cities & Municipal Infrastructure**:
  - Connected street lighting, automated water metering, and parking vacancy sensors.
  - Edge gateway manages localized neighborhood subnets and communicates status via cellular uplink.
- **4. Remote Environmental Monitoring**:
  - Air quality, river water pollution, and seismic warning nodes installed in hazardous zones.
  - Arduino Uno nodes interfaced to specialized analog sensors updated over USB without physical retrieval.

### Visual Layout Recommendation
- 4-quadrant layout with high-contrast icons and use-case photos:
  - Top-Left: Smart Factory Robotic Assembly.
  - Top-Right: Precision Agriculture / Smart Irrigation.
  - Bottom-Left: Smart City Streetlights & Grids.
  - Bottom-Right: Environmental Wildfire/Flood Sensor Nodes.

### Speaker Notes
*"Where does this matter in the real world? Imagine an industrial factory with 50 vibration sensor nodes on high-voltage motors, or a smart farm with ESP32-C3 sensors measuring soil moisture across 20 acres. In both cases, sending a technician with a laptop and a USB cable to update each device is economically unfeasible and hazardous. EdgeFleet allows operators to push tested, verified firmware to all nodes in minutes from a single dashboard."*

---

## Slide 7: Technical Stack & Protocol Implementation Matrix

### Slide Title
**Technology Stack, Protocols & Standards Compliance**

### Key Content Points
- **Full-Stack Technology Breakdown**:
  - **Frontend SPA**: React 18, TypeScript, Vite, Tailwind-grade custom design system, Lucide icons, Recharts telemetry graphing.
  - **Gateway Core**: Python 3.11, FastAPI (ASGI async event loop), Pydantic v2 data validation, SQLAlchemy 2.0 with async engine.
  - **Edge Communications**: Mosquitto MQTT v2.0 broker, Eclipse Paho client, WebSockets (RFC 6455).
  - **Hardware Tooling**: `avrdude` (STK500v1 serial programmer), Arduino-ESP32 Core, Espressif dual-OTA bootloader.
  - **Security & Networking**: Nginx 1.22 reverse proxy, Cloudflare Zero-Trust daemon, JWT Bearer authentication, bcrypt hashing.
- **Protocol Comparison Matrix**:

| Protocol | Layer | Purpose in EdgeFleet | Bandwidth Efficiency | Reliability Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **MQTT (TCP/1883)** | Application / M2M | Telemetry streaming & command dispatch | Ultra-low (2-byte header overhead) | QoS 1 (PubAck) + LWT |
| **HTTP/1.1 (TCP/80)** | Application / Web | Large binary chunk streaming | High throughput (1.1 MB in ~4s) | Range headers & Content-Length |
| **STK500v1 (UART)** | Physical Serial | Arduino Uno ATmega328P flashing | 115,200 baud direct hardware link | Byte-by-byte flash readback |
| **WebSockets (TCP)** | Full-Duplex Web | Real-time UI synchronization | Minimal framing (no HTTP polling) | Ping/Pong heartbeat frames |

### Visual Layout Recommendation
- Tech stack logos/badges (FastAPI, React, Vite, MQTT, Raspberry Pi, ESP32, Python) along the top.
- Formatted comparative protocol table along the bottom.

### Speaker Notes
*"EdgeFleet uses the right protocol for the right job. For tiny, frequent telemetry updates, we use MQTT because of its tiny 2-byte header overhead and Last Will and Testament feature. But for pushing a 1.1 megabyte firmware binary, we switch to HTTP streaming directly over local Wi-Fi, which saturates the link and finishes in under 4 seconds. For the Arduino Uno, we interface directly via STK500 serial protocol at 115,200 baud."*

---

## Slide 8: Current Capabilities vs. Future Scope & Roadmap

### Slide Title
**Benchmarked Results, Current Capabilities & Future Horizon**

### Key Content Points
- **Current Operational Metrics (Tested on Hardware)**:
  - **ESP32-C3 OTA Duration**: ~4.2 seconds to stream and flash 1.11 MB binary over local Wi-Fi.
  - **Arduino Uno Flashing Duration**: ~12.8 seconds to write and verify 32 KB flash via `avrdude`.
  - **Gateway Footprint**: Under 320 MB total RAM utilization on Raspberry Pi 4 (including OS, Nginx, Mosquitto, and FastAPI).
  - **Failover Protection**: 100% rollback success rate during simulated corrupted checksum injections.
- **Future Scope & Engineering Roadmap**:
  - **1. Asymmetric Cryptographic Signing (Ed25519/ECDSA)**:
    - Embedding public keys in ESP32 eFuses to prevent unauthorized firmware execution even if the gateway is compromised.
  - **2. ESP-NOW Mesh FOTA**:
    - Relaying firmware chunks across nodes outside Wi-Fi range using peer-to-peer ESP-NOW mesh networking.
  - **3. Cellular & Low-Bandwidth Delta Updates (Courgette/BSDiff)**:
    - Generating binary diffs that reduce a 1.1 MB update to a 45 KB delta patch for solar/satellite nodes.
  - **4. Gateway TinyML Predictive Anomaly Detection**:
    - Machine learning models running on Raspberry Pi to identify abnormal telemetry signatures and freeze risky rollouts.

### Visual Layout Recommendation
- **Left Column**: "Today: Validated Capabilities" with green checkmarks and benchmark metrics.
- **Right Column**: "Tomorrow: Research & Roadmap" featuring roadmap milestones (`Ed25519 Hardware Signing`, `Mesh FOTA`, `Delta Compaction`, `TinyML Safeguards`).

### Speaker Notes
*"To conclude: today, EdgeFleet is a fully functioning, benchmarked system. It updates an ESP32-C3 Mini in 4.2 seconds over Wi-Fi and an Arduino Uno in 12.8 seconds over USB, all while consuming less than 320 megabytes of RAM on a 2GB Raspberry Pi. Our roadmap will push this further by adding hardware-enforced Ed25519 cryptographic signing, ESP-NOW peer-to-peer mesh propagation for devices outside Wi-Fi coverage, and binary delta compaction for cellular IoT."*
