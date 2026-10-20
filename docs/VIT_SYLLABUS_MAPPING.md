# EdgeFleet: Comprehensive Syllabus Mapping Document
**Institution**: Vishwakarma Institute of Technology (VIT)  
**Course**: Internet of Things (IoT)  
**Project**: EdgeFleet — Distributed IoT Fleet Management & Secure Over-The-Air (FOTA) Gateway  

---

## Executive Overview
This document provides an exhaustive, unit-by-unit mapping between the academic syllabus of **Vishwakarma Institute of Technology (VIT)** and the concrete engineering implementation of the **EdgeFleet** project. 

Every unit is mapped to:
1. **Syllabus Topics Covered**
2. **Implementation in EdgeFleet** (with direct source code and hardware references)
3. **Key Architectural Concepts Demonstrated**
4. **Viva-Voce / Examination Alignment**

---

## UNIT I: Introduction to IoT

### 1. Syllabus Topics
*Introduction, Definitions, Characteristics of IoT, IoT Architectures, Physical and Logical Design of IoT, Enabling Technologies in IoT, IoT frameworks, Applications of IoT in various domains.*

### 2. Concrete Implementation in EdgeFleet
| Syllabus Concept | EdgeFleet Implementation | Code / Hardware Reference |
| :--- | :--- | :--- |
| **Definitions & Characteristics** | Dynamic self-adaptation, interoperability, heterogeneous connectivity, unique identity per node. | `device_id` uniqueness enforced in DB schema ([backend/app/models/device.py](file:///e:/edgefleet/backend/app/models/device.py#L15-L35)), dynamic online/offline state handling via MQTT LWT. |
| **IoT Architectures** | 3-Tier Layered Architecture: Perception Layer (Sensors/Nodes), Edge/Network Gateway Layer (Raspberry Pi 4), Application/Presentation Layer (React 18 SPA). | Documented in [docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md](file:///e:/edgefleet/docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md). |
| **Physical Design of IoT** | "Things" in IoT: Edge microcontrollers (ESP32-C3 Mini and Arduino Uno) connected to physical sensors and actuators (LED on GPIO 8/7, light lux sensors). | Firmware sketches: [firmware/esp32_c3_arduino/esp32_c3_arduino.ino](file:///e:/edgefleet/firmware/esp32_c3_arduino/esp32_c3_arduino.ino) and [firmware/arduino_uno/arduino_uno_edgefleet.ino](file:///e:/edgefleet/firmware/arduino_uno/arduino_uno_edgefleet.ino). |
| **Logical Design of IoT** | Functional blocks: Device, Communication, Services, Management, Application, and Security. Communication models: Request-Response (REST) and Publish-Subscribe (MQTT). | FastAPI router endpoints ([backend/app/api/](file:///e:/edgefleet/backend/app/api/)) and Mosquitto broker setup ([backend/app/mqtt/client.py](file:///e:/edgefleet/backend/app/mqtt/client.py)). |
| **Enabling Technologies** | Embedded systems, Wireless communication (IEEE 802.11 Wi-Fi), Cloud/Edge computing, Data processing protocols. | Raspberry Pi 4 ARM64 SBC acting as local edge compute node running Linux Debian Bookworm. |
| **Applications in Various Domains** | Fleet lifecycle management applicable across Smart Agriculture, Smart Cities, and Industrial IoT (IIoT). | Detailed in Slide 6 of [docs/PRESENTATION_SLIDES_8_DECK.md](file:///e:/edgefleet/docs/PRESENTATION_SLIDES_8_DECK.md). |

---

## UNIT II: IoT Design Methodology and Platform

### 1. Syllabus Topics
*IoT Design Methodology Steps and IoT System Design Cycle. Hardware Platforms - CISC/RISC Based microcontrollers and programming (8051/AVR), Arduino, Raspberry Pi, NodeMCU, ESP32. Sensors, actuators selection criteria for specific applications and interfacing basics.*

### 2. Concrete Implementation in EdgeFleet
| Syllabus Concept | EdgeFleet Implementation | Code / Hardware Reference |
| :--- | :--- | :--- |
| **IoT System Design Methodology** | 10-step design methodology followed: Purpose & Requirement Specification, Process Specification, Domain Model, Information Model, Service Specs, IoT Level Specs, Functional View, Operational View, Device & Component Integration, and Application Development. | Implemented end-to-end: REST APIs defined via OpenAPI ([docs/openapi.json](file:///e:/edgefleet/docs/openapi.json)), Pydantic schemas ([backend/app/schemas/](file:///e:/edgefleet/backend/app/schemas/)). |
| **CISC vs. RISC Microcontrollers** | Contrasts 8-bit Harvard RISC (AVR ATmega328P on Arduino Uno) with 32-bit modern open-standard RISC-V (Espressif ESP32-C3). | Handled via dual adapter classes: `ArduinoUnoAdapter` ([backend/app/device_adapters/arduino_uno.py](file:///e:/edgefleet/backend/app/device_adapters/arduino_uno.py)) vs `ESP32OTAAdapter` ([backend/app/device_adapters/esp32_ota.py](file:///e:/edgefleet/backend/app/device_adapters/esp32_ota.py)). |
| **Arduino (AVR/ATmega328P)** | Legacy edge node connected via USB serial; programmed in C++ and flashed in-system using STK500 bootloader protocol via `avrdude`. | [firmware/arduino_uno/arduino_uno_edgefleet.ino](file:///e:/edgefleet/firmware/arduino_uno/arduino_uno_edgefleet.ino); automated flash execution via `avrdude` in [backend/app/device_adapters/arduino_uno.py](file:///e:/edgefleet/backend/app/device_adapters/arduino_uno.py#L50-L95). |
| **Raspberry Pi Platform** | Serves as the central Single Board Computer (SBC) Gateway running Debian 64-bit OS, systemd daemons, Nginx reverse proxy, Mosquitto, and Python FastAPI. | Detailed system provisioning script: [deploy/raspberry-pi/install.sh](file:///e:/edgefleet/deploy/raspberry-pi/install.sh) and [docs/RASPBERRY_PI_SETUP.md](file:///e:/edgefleet/docs/RASPBERRY_PI_SETUP.md). |
| **ESP32 Platform (ESP32-C3 Mini)** | Connected wirelessly via 2.4 GHz Wi-Fi; implements dual-partition A/B OTA, non-volatile storage (NVS), hardware watchdog, and MQTT telemetry. | [firmware/esp32_c3_arduino/esp32_c3_arduino.ino](file:///e:/edgefleet/firmware/esp32_c3_arduino/esp32_c3_arduino.ino#L20-L100). |
| **Sensors & Actuators Interfacing** | - Actuators: Dual-pin active blinking on GPIO 8 (SuperMini) and GPIO 7 (LOLIN C3 Mini) to signal status and OTA progress.<br/>- Sensors: Analog light lux, VCC supply voltage monitoring, and heap/RSSI telemetry. | LED pin definitions in [esp32_c3_arduino.ino#L32-L35](file:///e:/edgefleet/firmware/esp32_c3_arduino/esp32_c3_arduino.ino#L32-L35); telemetry payload generator in [esp32_c3_arduino.ino#L250-L290](file:///e:/edgefleet/firmware/esp32_c3_arduino/esp32_c3_arduino.ino#L250-L290). |

---

## UNIT III: IoT Protocols and Standards

### 1. Syllabus Topics
*RFID, IEEE 802.15.4, Zigbee, NFC, Z-Wave, BLE, Bacnet, Modbus. IPv6, 6LowPAN, MQTT. Authorization and Access Control in IoT.*

### 2. Concrete Implementation in EdgeFleet
| Syllabus Concept | EdgeFleet Implementation | Code / Hardware Reference |
| :--- | :--- | :--- |
| **MQTT Protocol (Core Implementation)** | - Lightweight Publish/Subscribe protocol over TCP port 1883.<br/>- Topic hierarchies with parameterization (`edgefleet/v1/devices/{id}/...`).<br/>- Quality of Service: QoS 1 (At least once delivery) with PubAck verification.<br/>- Last Will and Testament (LWT) for automatic disconnected/offline node detection. | Mosquitto configuration and client initialization in [backend/app/mqtt/client.py](file:///e:/edgefleet/backend/app/mqtt/client.py#L30-L75); packet parsing in [backend/app/mqtt/handlers.py](file:///e:/edgefleet/backend/app/mqtt/handlers.py). |
| **Comparison with Other Protocols (Zigbee, BLE, Modbus)** | Comparative evaluation in architecture documentation: Zigbee/802.15.4 (mesh routing), BLE (short-range point-to-point), Modbus (industrial serial registers) vs MQTT over IP for high-throughput FOTA orchestration. | Analytical comparison matrix in Slide 7 of [docs/PRESENTATION_SLIDES_8_DECK.md](file:///e:/edgefleet/docs/PRESENTATION_SLIDES_8_DECK.md). |
| **IP Networking (IPv4 / IPv6 / 6LoWPAN)** | Native TCP/IP stack integration on ESP32-C3; local dynamic DHCP resolution (`10.202.94.37`) and gateway base URL detection (`10.202.94.199`). | Network resolution logic in [backend/app/device_adapters/esp32_ota.py#L70-L86](file:///e:/edgefleet/backend/app/device_adapters/esp32_ota.py#L70-L86). |
| **Authorization and Access Control in IoT** | - Role-Based Access Control (RBAC): `admin`, `operator`, `viewer`.<br/>- Stateless JSON Web Tokens (JWT) using `HS256` HMAC signing.<br/>- Password salting and hashing using `bcrypt`.<br/>- Endpoint route guards protecting dangerous actions (firmware delete, device update, deploy). | Route guards in [backend/app/api/deps.py](file:///e:/edgefleet/backend/app/api/deps.py#L30-L80); user model in [backend/app/models/user.py](file:///e:/edgefleet/backend/app/models/user.py). |

---

## UNIT IV: Wireless Sensor Networks for IoT

### 1. Syllabus Topics
*Types of Wireless Sensors, Examples and Working, Wireless Sensor Networks: History and Context of the node, Connecting nodes, Networking Nodes, WSN and IoT. Types of Network and network topologies for IoT.*

### 2. Concrete Implementation in EdgeFleet
| Syllabus Concept | EdgeFleet Implementation | Code / Hardware Reference |
| :--- | :--- | :--- |
| **Context & Anatomy of an IoT Node** | Complete breakdown of an edge node: Processing unit (RISC-V core), Transceiver (Wi-Fi 802.11b/g/n), Memory (SRAM + Flash with A/B partitions), Power supply. | Defined in ESP32-C3 firmware [firmware/esp32_c3_arduino/esp32_c3_arduino.ino](file:///e:/edgefleet/firmware/esp32_c3_arduino/esp32_c3_arduino.ino). |
| **Network Topologies for IoT** | **Hierarchical Star-Gateway Topology**: Edge nodes connect radially to the Raspberry Pi 4 edge gateway, which serves as the local cluster head and single point of WAN uplink. | Visualized in Mermaid graph in [docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md#2-system-architecture--topology](file:///e:/edgefleet/docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md). |
| **Connecting & Networking Nodes** | Automatic handshake and node registration: When a node boots, it issues a status announcement on `edgefleet/v1/devices/{id}/status`. The gateway captures IP, uptime, and firmware version to register or update the node dynamically. | Registration and heartbeat updater in [backend/app/mqtt/handlers.py#L75-L115](file:///e:/edgefleet/backend/app/mqtt/handlers.py#L75-L115). |
| **WSN Node Constraints & Management** | Mitigates memory limitations, flash wear, and packet loss through chunked streaming, checksum validation, and local gateway proxying. | [backend/app/device_adapters/esp32_ota.py](file:///e:/edgefleet/backend/app/device_adapters/esp32_ota.py). |

---

## UNIT V: Cloud Integration and Data Visualization

### 1. Syllabus Topics
*Cloud platforms for IoT: Thing Speak, Blynk, Firebase. Real-time data logging, charting, and alerts. Security and privacy fundamentals: Security Challenges in IoT Systems, Authentication, Authorization, and Access Control.*

### 2. Concrete Implementation in EdgeFleet
| Syllabus Concept | EdgeFleet Implementation | Code / Hardware Reference |
| :--- | :--- | :--- |
| **IoT Platforms & Edge Integration** | Overcomes limitations of third-party public clouds (ThingSpeak, Blynk, Firebase) by implementing a sovereign, self-hosted, edge-native IoT Gateway exposed globally via Cloudflare Zero-Trust Tunnels. | Cloudflare tunnel integration: [scratch/start-tunnel.sh](file:///C:/Users/anant/.gemini/antigravity-ide/brain/6b7f229a-5544-4af5-994e-4e3b2b301544/scratch/start-tunnel.sh) and [docs/CLOUD_DEPLOYMENT.md](file:///e:/edgefleet/docs/CLOUD_DEPLOYMENT.md). |
| **Real-Time Data Logging & Charting** | - Continuous sensor logging to SQLite datastore.<br/>- Full-duplex WebSocket streaming (`/ws/devices` and `/ws/deployments`) providing sub-second reactivity without polling.<br/>- Visual telemetry graphs built with Recharts. | WebSocket manager: [backend/app/websocket/manager.py](file:///e:/edgefleet/backend/app/websocket/manager.py); React UI page: [frontend/src/pages/Dashboard.tsx](file:///e:/edgefleet/frontend/src/pages/Dashboard.tsx). |
| **Real-Time Alerting System** | Automated threshold alerts: Unexpected reboot detection (`reset_reason`), firmware update failures, and node offline events. | Alert service in [backend/app/services/alert_service.py](file:///e:/edgefleet/backend/app/services/alert_service.py); Alert model in [backend/app/models/alert.py](file:///e:/edgefleet/backend/app/models/alert.py). |
| **Security Challenges in IoT Systems** | - **Mitigating Man-in-the-Middle (MITM)**: TLS encryption over Cloudflare tunnel.<br/>- **Mitigating Firmware Tampering**: SHA-256 cryptographic hash checks on every uploaded binary.<br/>- **Mitigating Accidental Bricking**: Preflight board-variant checking and hardware A/B rollback fallback. | Security architecture document: [docs/SECURITY.md](file:///e:/edgefleet/docs/SECURITY.md) and preflight validator in [backend/app/device_adapters/base.py](file:///e:/edgefleet/backend/app/device_adapters/base.py#L30-L55). |

---

## UNIT VI: Domain-Specific Smart Systems: Case Studies

### 1. Syllabus Topics
*Smart agriculture, Smart health, Smart cities, Smart transportation, Industrial IoT. System integration and real-world challenges.*

### 2. Concrete Implementation in EdgeFleet
| Syllabus Concept | EdgeFleet Implementation | Code / Hardware Reference |
| :--- | :--- | :--- |
| **Industrial IoT (IIoT)** | Fleet management for manufacturing sensor nodes monitoring vibration, motor RPM, and temperature. EdgeFleet enables zero-downtime firmware deployment to 100+ machines simultaneously without stopping the assembly line. | Analyzed in [docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md#11-the-industry-problem-context](file:///e:/edgefleet/docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md). |
| **Smart Cities & Municipal Infrastructure** | Remote firmware updates and telemetry collection for connected municipal streetlights, smart parking sensors, and automated water flow meters across city subnets. | Case study detailed in Slide 6 of [docs/PRESENTATION_SLIDES_8_DECK.md](file:///e:/edgefleet/docs/PRESENTATION_SLIDES_8_DECK.md). |
| **Smart Agriculture & Precision Farming** | Management of solar-powered ESP32-C3 soil sensor clusters. Farmers update sensor calibration constants and power-saving sleep algorithms over local Wi-Fi from an edge gateway on the farmhouse. | Documented in [docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md](file:///e:/edgefleet/docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md). |
| **System Integration Challenges** | - **Intermittent Connectivity**: Handled by MQTT keepalives and automated reconnect state machines.<br/>- **Heterogeneous Hardware**: Handled by modular adapter pattern separating IP Wi-Fi nodes from USB serial nodes.<br/>- **Resource Constraints**: Gateway footprint under 320 MB RAM; microcontroller firmware under 1.15 MB. | Benchmarks and architecture in [docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md#5-current-system-capabilities-state-of-the-project](file:///e:/edgefleet/docs/PROJECT_DEEP_DIVE_AND_ARCHITECTURE.md). |

---

## 3. Quick Reference: Syllabus Viva & Exam Defense Q&A

### Q1: Why did you choose MQTT over HTTP for telemetry, but HTTP over MQTT for firmware updates?
> **Answer**: Telemetry involves tiny, high-frequency packets (e.g. 100 bytes every 5 seconds). MQTT has a minuscule 2-byte header overhead compared to HTTP's 500-byte header overhead, making it drastically more bandwidth-efficient. Additionally, MQTT provides Last Will and Testament (LWT) for instant offline detection. Conversely, firmware updates are large (1.1 MB). Pushing a 1.1 MB payload over MQTT would choke the broker and saturate message queues. Therefore, EdgeFleet uses MQTT to coordinate the update command, but streams the binary directly over high-throughput HTTP GET chunks from the local Raspberry Pi gateway.

### Q2: How does EdgeFleet prevent a device from bricking if power is lost during an OTA update?
> **Answer**: The ESP32-C3 Mini uses a dual-partition (A/B) flash layout (`ota_0` and `ota_1`). While running version 1.0.0 in `ota_0`, the new binary is written to the inactive partition `ota_1`. If power cuts out mid-transfer, the bootloader's `otadata` record still points to `ota_0`, so the device simply reboots into its working firmware without any damage. Furthermore, once written, the ESP32 verifies the SHA-256 cryptographic checksum before switching boot flags. If a boot failure occurs, the hardware watchdog triggers automatic rollback to `ota_0`.

### Q3: What is the architectural role of the Raspberry Pi 4 gateway in contrast to cloud-only platforms like Blynk or ThingSpeak?
> **Answer**: Platforms like Blynk or ThingSpeak require every single microcontroller to maintain a direct, continuous connection to external cloud servers over the public internet, consuming high bandwidth and exposing every node to external attack surfaces. EdgeFleet implements an **Edge-Native Gateway Architecture**: the Raspberry Pi 4 acts as a local autonomous controller, keeping node traffic isolated on a secure local subnet. It can manage, log, and flash nodes completely offline without internet access. When remote access is needed, an encrypted Cloudflare Zero-Trust tunnel provides secure access without opening inbound firewall ports.
