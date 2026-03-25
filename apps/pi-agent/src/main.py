import json
import os
import socket
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psutil

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

SITE_ID = os.getenv("SITE_ID", "home")
TANK_ID = os.getenv("TANK_ID", "tank-01")
DEVICE_ID = os.getenv("DEVICE_ID", socket.gethostname())
PUBLISH_INTERVAL_SEC = int(os.getenv("PUBLISH_INTERVAL_SEC", "30"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish(client: mqtt.Client, group: str, metrics: dict) -> None:
    topic = f"dt/aquaponics/{SITE_ID}/{TANK_ID}/{DEVICE_ID}/{group}"
    payload = {
        "ts": now_iso(),
        "schema_version": 1,
        "metrics": metrics,
    }
    client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)


def publish_heartbeat(client: mqtt.Client) -> None:
    topic = f"dt/aquaponics/{SITE_ID}/{TANK_ID}/{DEVICE_ID}/heartbeat"
    payload = {
        "ts": now_iso(),
        "alive": True,
        "ip": get_ip(),
    }
    client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)


def publish_event(client: mqtt.Client, level: str, message: str) -> None:
    topic = f"dt/aquaponics/{SITE_ID}/{TANK_ID}/{DEVICE_ID}/event"
    payload = {
        "ts": now_iso(),
        "level": level,
        "message": message,
    }
    client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)


def get_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def read_env_metrics() -> dict:
    # TODO: BME280 / BH1750 実装に置き換え
    return {
        "air_temp_c": {"value": 23.4, "unit": "C"},
        "humidity_pct": {"value": 44.2, "unit": "%"},
        "pressure_hpa": {"value": 1017.8, "unit": "hPa"},
        "lux": {"value": 380.0, "unit": "lux"},
    }


def read_water_metrics() -> dict:
    # TODO: DS18B20 / 水位 / pH 実装に置き換え
    return {
        "water_temp_c": {"value": 24.1, "unit": "C"},
        "water_level_cm": {"value": 18.6, "unit": "cm"},
    }


def read_device_metrics() -> dict:
    return {
        "cpu_pct": {"value": psutil.cpu_percent(), "unit": "%"},
        "mem_pct": {"value": psutil.virtual_memory().percent, "unit": "%"},
    }


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    while True:
        try:
            publish(client, "env", read_env_metrics())
            publish(client, "water", read_water_metrics())
            publish(client, "device", read_device_metrics())
            publish_heartbeat(client)
        except Exception as e:
            publish_event(client, "error", str(e))

        time.sleep(PUBLISH_INTERVAL_SEC)


if __name__ == "__main__":
    main()
