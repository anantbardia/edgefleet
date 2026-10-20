"""MQTT topic templates and parsing utilities."""

TOPIC_PREFIX = "edgefleet/v1/devices"

TELEMETRY_TOPIC = f"{TOPIC_PREFIX}/+/telemetry"
STATUS_TOPIC = f"{TOPIC_PREFIX}/+/status"
EVENTS_TOPIC = f"{TOPIC_PREFIX}/+/events"
UPDATE_STATUS_TOPIC = f"{TOPIC_PREFIX}/+/update/status"
COMMANDS_TOPIC = f"{TOPIC_PREFIX}/{{device_id}}/commands"


def make_command_topic(device_id: str) -> str:
    """Format the outbound command topic for a specific device."""
    return f"{TOPIC_PREFIX}/{device_id}/commands"


def parse_topic(topic: str) -> tuple[str, str] | None:
    """Extract (device_id, message_type) from a topic.

    Example: 'edgefleet/v1/devices/esp32-001/telemetry' -> ('esp32-001', 'telemetry')
    Example: 'edgefleet/v1/devices/esp32-001/update/status' -> ('esp32-001', 'update_status')
    """
    parts = topic.strip("/").split("/")
    if len(parts) == 4 and parts[0] == "edgefleet" and parts[1] == "v1" and parts[2] == "devices":
        return parts[3], parts[4] if len(parts) > 4 else parts[3]
    if len(parts) == 5 and parts[0] == "edgefleet" and parts[1] == "v1" and parts[2] == "devices":
        if parts[4] == "status" and parts[3] != "devices":
            return parts[3], "status"
        return parts[3], parts[4]
    if len(parts) == 6 and parts[0] == "edgefleet" and parts[1] == "v1" and parts[2] == "devices":
        if parts[4] == "update" and parts[5] == "status":
            return parts[3], "update_status"
    return None
