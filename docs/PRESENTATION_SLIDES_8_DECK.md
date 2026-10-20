# EdgeFleet: Presentation Slide Deck (8 Core Slides)
### *A Practical, High-Impact Guide to Impress Your Faculty*

> **Presentation Strategy for Faculty**:
> Faculty members care about three key things:
> 1. **Did you solve a real, practical engineering problem?** (Yes: remote firmware updates without bricking devices).
> 2. **Is your architecture well-structured and sound?** (Yes: 3-tier edge-native architecture).
> 3. **Did you build and test a real working prototype?** (Yes: Raspberry Pi Gateway + ESP32-C3 Mini Wi-Fi node + Arduino Uno).
>
> Keep slides clean with bold headings and minimal text. Use the provided **"What to Say"** speaker notes to sound confident and professional.

---

## Slide 1: The Real-World Problem — The IoT Maintenance Dilemma

### Slide Heading
**The Challenge: Managing & Updating Remote IoT Microcontrollers**

### Bullet Points on Slide
- **Inaccessible Devices**: IoT nodes are deployed in remote locations (factory ceilings, agricultural fields, smart streetlights) where manual physical access is expensive or impossible.
- **The "Bricking" Nightmare**: If power cuts out or a corrupted binary is sent during a remote update, the microcontroller is permanently disabled ("bricked") and requires manual replacement.
- **Heterogeneous Hardware**: Real-world deployments mix different chips together—modern 32-bit Wi-Fi microcontrollers (**ESP32-C3**) alongside rugged 8-bit industrial controllers (**Arduino Uno**).
- **Cloud Dependency Risks**: Relying entirely on external cloud servers creates high latency, recurring subscription costs, and total failure when the local internet goes down.

### Visual on Slide
- Visual contrast: A technician climbing a tall ladder in a factory with a laptop cable vs. a wireless update signal.
- Tagline: *"How do we update hundreds of different microcontrollers remotely without ever bricking them?"*

### What to Say to Faculty
> *"Respected faculty, in modern IoT, deploying sensors is only the first step. The hardest problem is maintaining them. Once you mount a sensor on a farm pole or inside an industrial machine, you cannot go with a USB cable every time there is a bug fix or feature update. If an update fails halfway through, the device is dead. EdgeFleet solves this by giving you a secure, local command center that manages and updates heterogeneous microcontrollers completely over-the-air, with zero risk of bricking."*

---

## Slide 2: The Solution — EdgeFleet Overview

### Slide Heading
**EdgeFleet: Edge-Native Fleet Management & Safe FOTA Platform**

### Bullet Points on Slide
- **Centralized Edge Gateway**: A Raspberry Pi acts as a local on-site brain, managing devices independently even if the wider internet is down.
- **Unified Multi-Board Support**: Manages both wireless **ESP32-C3 Mini** nodes over Wi-Fi and wired **Arduino Uno** nodes over USB serial from a single dashboard.
- **Fail-Safe Firmware Over-The-Air (FOTA)**: Safe remote updates that automatically roll back if something goes wrong.
- **Real-Time Fleet Dashboard**: A responsive web control panel for real-time sensor monitoring, device health tracking, and 1-click deployments.

### Visual on Slide
- A clean diagram showing the **Raspberry Pi Gateway** in the middle, wirelessly controlling **ESP32-C3** nodes and wired **Arduino Uno** nodes, with a laptop/mobile accessing the dashboard.

### What to Say to Faculty
> *"EdgeFleet is an edge-native IoT management platform. Instead of forcing every tiny microcontroller to talk directly to an expensive cloud server, we place an intelligent gateway—a Raspberry Pi—on the local premises. The gateway talks to modern Wi-Fi devices like the ESP32-C3 Mini and legacy wired devices like Arduino Uno. It provides a real-time web dashboard where an engineer can monitor live telemetry and push new firmware with a single click."*

---

## Slide 3: System Architecture — The 3-Tier Hierarchy

### Slide Heading
**System Architecture: Clean 3-Tier Design**

### Bullet Points on Slide
- **Tier 1: Operator Presentation Layer (Frontend)**
  - Modern web dashboard built with **React** and **TypeScript**.
  - Uses **WebSockets** for live, instant updates without refreshing the page.
- **Tier 2: Edge Gateway Controller (Raspberry Pi 4)**
  - **FastAPI Core**: High-speed asynchronous engine managing devices and firmware binaries.
  - **Mosquitto MQTT Broker**: Ultra-lightweight messaging engine for sensor data and commands.
  - **Local SQLite Database**: Stores device logs, release files, and telemetry locally.
- **Tier 3: Distributed Edge Nodes (Physical Hardware)**
  - **ESP32-C3 Mini**: High-speed 32-bit RISC-V microcontroller with Wi-Fi and dual-partition OTA.
  - **Arduino Uno**: 8-bit AVR microcontroller connected via USB serial for rugged sensing.

### Visual on Slide
- 3 clean horizontal layers:
  - `Top`: Operator Web Dashboard (React)
  - `Middle`: Raspberry Pi 4 Gateway (FastAPI + MQTT + SQLite)
  - `Bottom`: Physical Hardware Nodes (ESP32-C3 Mini + Arduino Uno)

### What to Say to Faculty
> *"Our architecture follows a clean 3-tier hierarchy. At Tier 1, operators have a responsive React dashboard with live WebSockets. At Tier 2, our Raspberry Pi edge gateway runs an asynchronous FastAPI server, an MQTT broker, and a local database. At Tier 3, we have the physical hardware: an ESP32-C3 Mini communicating wirelessly and an Arduino Uno communicating over serial. This structure keeps the heavy processing on the gateway, allowing our microcontrollers to stay lightweight and power-efficient."*

---

## Slide 4: System Architecture Flow — How Data & Updates Move

### Slide Heading
**Data & Command Flow: Step-by-Step Architecture Pipeline**

### Visual Diagram for Slide
*(You can draw this exact flow in PowerPoint or Draw.io)*

```
[ Operator Dashboard ]
         │
         │  1. Initiate Deployment (HTTPS/WSS)
         ▼
[ Raspberry Pi Gateway ]
   ├── 2. Runs Preflight Safety Check (Validates board & firmware)
   ├── 3. Sends Trigger Command via MQTT (Port 1883)
   │               │
   │               ▼
   │      [ ESP32-C3 Mini Node ]
   │               │
   └── 4. Streams 1.1 MB Binary via local HTTP (10.202.94.199)
                   │
                   ▼
          [ ESP32-C3 Mini Node ]
          5. Writes to Inactive Partition
          6. Verifies SHA-256 Checksum
          7. Reboots into New Version & Confirms Online!
```

### Key Highlights for Faculty
- **Two Separate Channels for Efficiency**:
  - **MQTT**: Used for tiny, lightweight messages (sensor readings, status heartbeats, commands).
  - **Local HTTP**: Used for fast, reliable binary file downloads (streams 1.1 MB in under 4 seconds).
- **Continuous Feedback**: Every step is reported back to the dashboard in real time over WebSockets.

### What to Say to Faculty
> *"This flow diagram highlights the engineering elegance of our system. Notice we don't clog our MQTT broker with large firmware files. When an operator triggers an update, the gateway sends a tiny command over MQTT. The ESP32-C3 then opens a high-speed local HTTP connection to the gateway to stream the binary. Once downloaded and checksum-verified, the device reboots into the new firmware and reports success back to the dashboard. The entire process takes less than 5 seconds."*

---

## Slide 5: The Hero Feature — How EdgeFleet Prevents "Bricking"

### Slide Heading
**Atomic Dual-Partition (A/B) Updates: Zero-Downtime & Fail-Safe**

### Bullet Points on Slide
- **Preflight Compatibility Gate**:
  - Before sending an update, the gateway verifies that the firmware was compiled for the exact target board (prevents flashing Arduino code onto an ESP32).
- **Dual A/B Flash Partitioning**:
  - Flash memory is divided into two separate application slots: **Slot A** and **Slot B**.
  - While the node is running safely on **Slot A**, the new update downloads into **Slot B**.
- **Cryptographic Verification**:
  - The node computes the **SHA-256 checksum** of the downloaded code before switching.
- **Automatic Fallback Watchdog**:
  - If power cuts out during download: **Slot A is completely untouched**.
  - If the new code crashes on boot: The hardware bootloader automatically reverts to **Slot A**.

### Visual on Slide
- Simple graphic comparing **Old Way (Single Flash)** vs. **EdgeFleet A/B Way**:
  - *Old Way*: Overwrite active memory ➔ Power loss = Bricked board ❌
  - *EdgeFleet*: Write to Slot B ➔ Verify ➔ Switch active boot pointer ➔ Never Bricks ✅

### What to Say to Faculty
> *"Faculty often ask: 'What happens if the Wi-Fi drops or someone pulls the plug while updating?' This slide answers that. We use an A/B dual-partition scheme. The active code is running in Partition A. The new code is written to Partition B in the background. If power is cut at 50%, Partition A is completely intact; the device restarts normally. If the new code has a fatal bug and crashes, the hardware watchdog catches it and flips back to Partition A. It is virtually impossible to brick the device."*

---

## Slide 6: Real-World Applications

### Slide Heading
**Industry Use Cases: Where EdgeFleet Delivers Real Value**

### 4 Key Application Quadrants
1. **Industrial IoT (IIoT) & Smart Factories**:
   - Machinery vibration, motor RPM, and temperature monitoring.
   - Update threshold detection algorithms on 50+ factory machines simultaneously without halting assembly lines.
2. **Smart Agriculture & Precision Farming**:
   - Soil moisture, nutrient, and micro-climate sensors scattered across acres.
   - Farmhouse gateway updates irrigation schedules and power-saving sleep routines wirelessly.
3. **Smart Cities & Municipal Infrastructure**:
   - Connected streetlights, smart parking nodes, and automated water flow meters.
   - Updates dispatched across entire city blocks without requiring physical maintenance trucks.
4. **Hazardous Environmental Monitoring**:
   - Flood level, air quality, and wildfire detection nodes placed in dangerous or inaccessible areas.
   - Wired Arduino sensor units updated over serial safely from the gateway.

### What to Say to Faculty
> *"EdgeFleet isn't just a classroom project; it directly addresses major industrial needs. In precision agriculture, farmers have sensor nodes spread across acres—EdgeFleet updates all of them from a gateway on the barn. In smart factories, changing sensor logic on 50 machines takes seconds instead of taking days of downtime. Any sector deploying distributed microcontrollers benefits from centralized, safe fleet management."*

---

## Slide 7: Technical Stack & Working Implementation

### Slide Heading
**Engineering Stack: Production-Grade Technologies**

### Technology Breakdown Table
| Layer | Technologies Used | Role in EdgeFleet |
| :--- | :--- | :--- |
| **Operator UI** | React 18, TypeScript, Vite, WebSockets | Instant real-time control & telemetry visualization |
| **Gateway Brain** | Python 3.11, FastAPI, SQLite (WAL Mode) | Asynchronous business logic & local data persistence |
| **Communications** | Mosquitto MQTT (Port 1883), HTTP/1.1 | Telemetry streaming & high-speed binary delivery |
| **Security** | JWT Tokens, bcrypt, Cloudflare Zero Trust | Secure role-based login & encrypted global access |
| **Edge Hardware** | ESP32-C3 Mini (RISC-V) & Arduino Uno (AVR) | Wi-Fi sensing node & USB serial sensor node |

### Key Practical Achievements
- **Zero Cloud Costs**: Runs entirely on a standard Raspberry Pi 4 (consumes <350 MB RAM).
- **Public Remote Access**: Reachable securely from anywhere in the world via Cloudflare Tunnel without opening router ports.
- **Tested on Physical Hardware**: Real ESP32-C3 Mini connected, streaming telemetry, and accepting OTA updates.

### What to Say to Faculty
> *"Our implementation uses proven, production-grade tools. We chose FastAPI for its high asynchronous speed, Mosquitto MQTT for lightweight device messaging, and React for a modern, responsive interface. The entire gateway runs efficiently on a 2GB Raspberry Pi with under 350 megabytes of memory. Through an encrypted Cloudflare Tunnel, we can demonstrate controlling the hardware right from our smartphones without port-forwarding."*

---

## Slide 8: Current Capabilities & Future Roadmap

### Slide Heading
**Validated Results & Future Vision**

### Validated Results (What Works Today)
- ✅ **Tested Wi-Fi OTA**: ESP32-C3 Mini downloads and flashes 1.1 MB firmware in under **4.5 seconds**.
- ✅ **Tested Serial Flashing**: Arduino Uno programmed over USB via `avrdude` STK500 protocol.
- ✅ **Real-Time Telemetry**: Live sensor metrics pushed every 5 seconds with automatic offline detection.
- ✅ **Safety Validated**: Preflight checks prevent wrong-architecture firmware flashing.

### Future Scope (Where We Can Take It Next)
- **1. Cryptographic Signature Verification**: Using hardware eFuses and Ed25519 digital signatures so only authorized code can run on the chip.
- **2. Mesh Network Updates (ESP-NOW)**: Allowing ESP32 nodes to relay firmware to neighboring nodes that are out of Wi-Fi range.
- **3. Low-Bandwidth Delta Updates**: Sending only binary differences (diffs) to reduce update size from 1.1 MB down to 50 KB for cellular/solar nodes.

### What to Say to Faculty
> *"To conclude, EdgeFleet is a complete, working prototype. We have verified both Wi-Fi OTA on the ESP32-C3 Mini in under 4.5 seconds and USB serial flashing on the Arduino Uno. Looking ahead, we plan to implement cryptographic hardware signing and ESP-NOW mesh networking so nodes can daisy-chain updates to devices far outside Wi-Fi coverage. Thank you, and we welcome any questions from the panel!"*
