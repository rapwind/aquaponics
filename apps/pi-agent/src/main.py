import json
import os
import socket
import time
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt
import psutil

# Optional sensor imports
try:
    import board
    import busio
    import adafruit_bme280
    import adafruit_bh1750
except Exception:
    board = None
    busio = None
    adafruit_bme280 = None
    adafruit_bh1750 = None

try:
    from w1thermsensor import W1ThermSensor, Unit
except Exception:
    W1ThermSensor = None
    Unit = None


MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

SITE_ID = os.getenv("SITE_ID", "home")
TANK_ID = os.getenv("TANK_ID", "tank-01")
DEVICE_ID = os.getenv("DEVICE_ID", socket.gethostname())
PUBLISH_INTERVAL_SEC = int(os.getenv("PUBLISH_INTERVAL_SEC", "30"))

ENABLE_BME280 = os.getenv("ENABLE_BME280", "true").lower() == "true"
ENABLE_BH1750 = os.getenv("ENABLE_BH1750", "true").lower() == "true"
ENABLE_DS18B20 = os.getenv("ENABLE_DS18B20", "true").lower() == "true"

BME280_I2C_ADDRESS = int(os.getenv("BME280_I2C_ADDRESS", "0x76"), 16)
BH1750_I2C_ADDRESS = int(os.getenv("BH1750_I2C_ADDRESS", "0x23"), 16)

# Global sensor handles
_i2c = None
_bme280 = None
_bh1750 = None
_ds18b20 = None

_last_error_messages: set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def topic_for(group: str) -> str:
    return f"dt/aquaponics/{SITE_ID}/{TANK_ID}/{DEVICE_ID}/{group}"


def get_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def publish_metrics(client: mqtt.Client, group: str, metrics: dict[str, Any]) -> None:
    if not metrics:
        return

    payload = {
        "ts": now_iso(),
        "schema_version": 1,
        "metrics": metrics,
    }
    client.publish(topic_for(group), json.dumps(payload, ensure_ascii=False), qos=1)


def publish_heartbeat(client: mqtt.Client) -> None:
    payload = {
        "ts": now_iso(),
        "alive": True,
        "ip": get_ip(),
    }
    client.publish(topic_for("heartbeat"), json.dumps(payload, ensure_ascii=False), qos=1)


def publish_event(client: mqtt.Client, level: str, message: str) -> None:
    payload = {
        "ts": now_iso(),
        "level": level,
        "message": message,
    }
    client.publish(topic_for("event"), json.dumps(payload, ensure_ascii=False), qos=1)


def publish_error_once(client: mqtt.Client, message: str) -> None:
    global _last_error_messages
    print(f"[error] {message}")
    if message in _last_error_messages:
        return
    _last_error_messages.add(message)
    publish_event(client, "error", message)


def publish_info_once(client: mqtt.Client, message: str) -> None:
    global _last_error_messages
    print(f"[info] {message}")
    key = f"INFO::{message}"
    if key in _last_error_messages:
        return
    _last_error_messages.add(key)
    publish_event(client, "info", message)


def setup_i2c_sensors(client: mqtt.Client) -> None:
    global _i2c, _bme280, _bh1750

    if board is None or busio is None:
        publish_error_once(client, "I2C libraries are not available in container.")
        return

    try:
        _i2c = busio.I2C(board.SCL, board.SDA)
    except Exception as e:
        publish_error_once(client, f"Failed to initialize I2C bus: {e}")
        return

    if ENABLE_BME280 and adafruit_bme280 is not None:
        try:
            _bme280 = adafruit_bme280.Adafruit_BME280_I2C(_i2c, address=BME280_I2C_ADDRESS)
            publish_info_once(client, f"BME280 initialized at address {hex(BME280_I2C_ADDRESS)}")
        except Exception as e:
            publish_error_once(client, f"Failed to initialize BME280: {e}")

    if ENABLE_BH1750 and adafruit_bh1750 is not None:
        try:
            _bh1750 = adafruit_bh1750.BH1750(_i2c, address=BH1750_I2C_ADDRESS)
            publish_info_once(client, f"BH1750 initialized at address {hex(BH1750_I2C_ADDRESS)}")
        except Exception as e:
            publish_error_once(client, f"Failed to initialize BH1750: {e}")


def setup_w1_sensor(client: mqtt.Client) -> None:
    global _ds18b20

    if not ENABLE_DS18B20:
        return

    if W1ThermSensor is None:
        publish_error_once(client, "w1thermsensor library is not available in container.")
        return

    try:
        sensors = W1ThermSensor.get_available_sensors()
        if not sensors:
            publish_error_once(client, "No DS18B20 sensors found.")
            return

        _ds18b20 = sensors[0]
        publish_info_once(client, f"DS18B20 initialized: {_ds18b20.id}")
    except Exception as e:
        publish_error_once(client, f"Failed to initialize DS18B20: {e}")


def read_env_metrics(client: mqtt.Client) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}

    if _bme280 is not None:
        try:
            metrics["air_temp_c"] = {"value": round(float(_bme280.temperature), 2), "unit": "C"}
            metrics["humidity_pct"] = {"value": round(float(_bme280.relative_humidity), 2), "unit": "%"}
            metrics["pressure_hpa"] = {"value": round(float(_bme280.pressure), 2), "unit": "hPa"}
        except Exception as e:
            publish_error_once(client, f"Failed to read BME280: {e}")

    if _bh1750 is not None:
        try:
            metrics["lux"] = {"value": round(float(_bh1750.lux), 2), "unit": "lux"}
        except Exception as e:
            publish_error_once(client, f"Failed to read BH1750: {e}")

    return metrics


def read_water_metrics(client: mqtt.Client) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}

    if _ds18b20 is not None:
        try:
            temp_c = _ds18b20.get_temperature(Unit.DEGREES_C)
            metrics["water_temp_c"] = {"value": round(float(temp_c), 2), "unit": "C"}
        except Exception as e:
            publish_error_once(client, f"Failed to read DS18B20: {e}")

    return metrics


def read_device_metrics() -> dict[str, dict[str, Any]]:
    return {
        "cpu_pct": {"value": round(psutil.cpu_percent(), 2), "unit": "%"},
        "mem_pct": {"value": round(psutil.virtual_memory().percent, 2), "unit": "%"},
        "disk_pct": {"value": round(psutil.disk_usage('/').percent, 2), "unit": "%"},
    }


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[mqtt] connected: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    print(f"[mqtt] disconnected: {reason_code}")


def connect_with_retry(client: mqtt.Client) -> None:
    MAX_BACKOFF = 300
    delay = 5
    while True:
        try:
            print(f"[mqtt] connecting to {MQTT_HOST}:{MQTT_PORT} ...")
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            return
        except Exception as e:
            print(f"[mqtt] connection failed: {e} — retrying in {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, MAX_BACKOFF)


def main():
    print(f"[pi-agent] starting  site={SITE_ID} tank={TANK_ID} device={DEVICE_ID}")
    print(f"[pi-agent] MQTT target: {MQTT_HOST}:{MQTT_PORT}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    connect_with_retry(client)
    client.loop_start()

    # Sensor initialization after MQTT starts so errors can be published
    setup_i2c_sensors(client)
    setup_w1_sensor(client)

    while True:
        try:
            if not client.is_connected():
                print("[mqtt] not connected, attempting reconnect ...")
                connect_with_retry(client)

            env_metrics = read_env_metrics(client)
            water_metrics = read_water_metrics(client)
            device_metrics = read_device_metrics()

            publish_metrics(client, "env", env_metrics)
            publish_metrics(client, "water", water_metrics)
            publish_metrics(client, "device", device_metrics)
            publish_heartbeat(client)
        except Exception as e:
            print(f"[main] error: {e}")

        time.sleep(PUBLISH_INTERVAL_SEC)


if __name__ == "__main__":
    main()
