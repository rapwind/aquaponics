import json
from datetime import datetime, timezone
from typing import Any


def parse_topic(topic: str) -> dict[str, str]:
    # dt/aquaponics/{site_id}/{tank_id}/{device_id}/{sensor_group}
    parts = topic.split("/")
    if len(parts) != 6:
        raise ValueError(f"Invalid topic format: {topic}")

    root, project, site_id, tank_id, device_id, sensor_group = parts

    if root != "dt" or project != "aquaponics":
        raise ValueError(f"Unexpected topic namespace: {topic}")

    return {
        "site_id": site_id,
        "tank_id": tank_id,
        "device_id": device_id,
        "sensor_group": sensor_group,
    }


def parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)

    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")

    return datetime.fromisoformat(raw)


def parse_payload(payload_bytes: bytes) -> dict[str, Any]:
    return json.loads(payload_bytes.decode("utf-8"))


def build_rows(topic: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    topic_info = parse_topic(topic)
    ts = parse_timestamp(payload.get("ts"))
    metrics = payload.get("metrics", {})

    rows: list[dict[str, Any]] = []

    for metric_name, metric_data in metrics.items():
        rows.append(
            {
                "ts": ts,
                "tank_id": topic_info["tank_id"],
                "device_id": topic_info["device_id"],
                "sensor_group": topic_info["sensor_group"],
                "metric_name": metric_name,
                "value": float(metric_data["value"]),
                "unit": metric_data.get("unit"),
                "status": metric_data.get("status"),
                "topic": topic,
                "raw_payload": json.dumps(payload, ensure_ascii=False),
            }
        )

    return rows
