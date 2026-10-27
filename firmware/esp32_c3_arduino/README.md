# EdgeFleet ESP32-C3 Wi-Fi & FOTA Node

This sketch enables your **ESP32-C3** microcontroller to connect to the EdgeFleet Raspberry Pi Gateway via Wi-Fi and receive **Over-The-Air (FOTA)** firmware updates.

---

## 1. Initial Flash (One-Time via USB)

1. Open `esp32_c3_edgefleet.ino` in **Arduino IDE**.
2. Install the **PubSubClient** library:
   - **Tools** -> **Manage Libraries...** -> Search for `PubSubClient` by Nick O'Leary -> Install.
3. Configure your network credentials at the top of `esp32_c3_edgefleet.ino`:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* GATEWAY_HOST  = "10.162.65.199"; // IP of your Raspberry Pi Gateway
   const char* DEVICE_ID     = "esp32-c3-01";
   const char* BOARD_VARIANT = "ESP32-C3";
   const char* CURRENT_VERSION = "1.0.0";
   ```
4. Select your Board and Flash Settings:
   - **Tools** -> **Board** -> **esp32** -> **ESP32C3 Dev Module** (or **LOLIN C3 Mini**)
   - **Tools** -> **Partition Scheme** -> **Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)** or **Default 4MB with spiffs**
   - **Tools** -> **Port** -> Select your ESP32-C3 USB COM Port
5. Click **Upload** (Arrow icon).

Once uploaded, open the Serial Monitor at **115200 baud**. You will see:
```text
[Wi-Fi] Connected! IP Address: 10.202.94.37
[MQTT] Connected successfully!
[MQTT] Subscribed to edgefleet/v1/devices/esp32-c3-01/commands
[Telemetry] {"schema_version":"1.0","device_id":"esp32-c3-01", ...}
```

Now, check your EdgeFleet Dashboard:
- Go to **Device Inventory** — `esp32-c3-01` will appear with a green **Online** badge and live telemetry!

---

## 2. Compiling New Firmware for Wi-Fi OTA

When you want to deploy an updated version (e.g., v1.1.0 or blink pattern change):

1. In `esp32_c3_edgefleet.ino`, update the version:
   ```cpp
   const char* CURRENT_VERSION = "1.1.0";
   ```
2. In Arduino IDE, click:
   - **Sketch** -> **Export Compiled Binary** (or press `Ctrl+Alt+S`)
3. Open the sketch folder:
   - **Sketch** -> **Show Sketch Folder**
   - Inside `build/esp32.esp32.esp32c3/`, you will find `esp32_c3_edgefleet.ino.bin`!

---

## 3. Deploying Over Wi-Fi via EdgeFleet Dashboard

1. Open your EdgeFleet Dashboard.
2. Go to **Firmware Releases** -> Click **Upload Firmware**:
   - **File**: Select `esp32_c3_edgefleet.ino.bin`
   - **Version**: `1.1.0`
   - **Architecture**: `ESP32 (Wi-Fi OTA)`
   - **Target Board**: `ESP32-C3`
   - Click **Upload Release**
3. On the new release card, click **Approve Release**.
4. Go to **Deployments** -> **Launch New Firmware Deployment**:
   - **Target Device**: `esp32-c3-01`
   - **Release**: `v1.1.0 (ESP32-C3)`
   - Click **Run Preflight Compatibility** (it will verify that the device is online and compatible)
   - Click **Start Deployment**!

Watch the live stepper on the dashboard:
`QUEUED` -> `TRANSFERRING` -> `VERIFYING` -> `INSTALLING` -> `REBOOTING` -> `SUCCESS`!

Your ESP32-C3 will download the firmware over Wi-Fi, flash itself, reboot, and report back online with `v1.1.0`!
