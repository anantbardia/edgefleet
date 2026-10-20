/*
 * EdgeFleet Arduino Uno (ATmega328P) Node Sketch
 *
 * Communicates with the EdgeFleet Raspberry Pi gateway via USB Serial at 115200 baud.
 * Emits newline-delimited JSON telemetry and responds to query commands.
 */

#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_ID        "uno-001"
#define BAUD_RATE        115200

unsigned long last_telemetry_time = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 3000;
unsigned long loop_counter = 0;

long read_internal_vcc_mv() {
  // Read 1.1V reference against AVcc
  #if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
    ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  #else
    return 5000;
  #endif
  delay(2); // Wait for Vref to settle
  ADCSRA |= _BV(ADSC); // Convert
  while (bit_is_set(ADCSRA, ADSC));
  uint8_t low  = ADCL;
  uint8_t high = ADCH;
  long result = (high << 8) | low;
  result = 1125300L / result; // Calculate Vcc (in mV); 1125300 = 1.1*1023*1000
  return result;
}

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial && millis() < 2000); // Wait for serial port on USB boards

  // Print startup greeting
  Serial.println();
  Serial.print("{\"event\":\"boot\",\"device_id\":\"");
  Serial.print(DEVICE_ID);
  Serial.print("\",\"version\":\"");
  Serial.print(FIRMWARE_VERSION);
  Serial.println("\",\"baud\":115200}");
}

void loop() {
  loop_counter++;
  unsigned long now = millis();

  // Handle incoming commands from serial
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "PING") {
      Serial.println("{\"response\":\"PONG\"}");
    } else if (cmd == "VERSION") {
      Serial.print("{\"version\":\"");
      Serial.print(FIRMWARE_VERSION);
      Serial.println("\"}");
    } else if (cmd == "INFO") {
      Serial.print("{\"device_id\":\"");
      Serial.print(DEVICE_ID);
      Serial.print("\",\"version\":\"");
      Serial.print(FIRMWARE_VERSION);
      Serial.print("\",\"uptime_ms\":");
      Serial.print(now);
      Serial.println("}");
    }
  }

  // Periodic telemetry stream
  if (now - last_telemetry_time >= TELEMETRY_INTERVAL_MS) {
    last_telemetry_time = now;

    int raw_analog = analogRead(A0);
    float light_lux = (raw_analog / 1023.0f) * 800.0f;
    long vcc = read_internal_vcc_mv();

    Serial.print("{\"schema_version\":\"1.0\",\"device_id\":\"");
    Serial.print(DEVICE_ID);
    Serial.print("\",\"firmware_version\":\"");
    Serial.print(FIRMWARE_VERSION);
    Serial.print("\",\"uptime_seconds\":");
    Serial.print(now / 1000);
    Serial.print(",\"readings\":{\"light_lux\":");
    Serial.print(light_lux, 1);
    Serial.print(",\"vcc_mv\":");
    Serial.print(vcc);
    Serial.print(",\"loop_count\":");
    Serial.print(loop_counter);
    Serial.println("}}");
  }
}
