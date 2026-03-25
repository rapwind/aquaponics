import os


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


MQTT_HOST = get_env("MQTT_HOST")
MQTT_PORT = int(get_env("MQTT_PORT", "1883"))
MQTT_USER = get_env("MQTT_USER")
MQTT_PASSWORD = get_env("MQTT_PASSWORD")

PGHOST = get_env("PGHOST")
PGPORT = int(get_env("PGPORT", "5432"))
PGDATABASE = get_env("PGDATABASE")
PGUSER = get_env("PGUSER")
PGPASSWORD = get_env("PGPASSWORD")

TOPIC_FILTER = "dt/aquaponics/+/+/+/+"
