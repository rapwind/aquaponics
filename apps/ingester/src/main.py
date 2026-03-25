import time

import paho.mqtt.client as mqtt

from config import MQTT_HOST, MQTT_PASSWORD, MQTT_PORT, MQTT_USER, TOPIC_FILTER
from db import get_conn, insert_rows
from parser import build_rows, parse_payload


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[mqtt] connected: {reason_code}")
    client.subscribe(TOPIC_FILTER, qos=1)


def on_message(client, userdata, msg):
    try:
        payload = parse_payload(msg.payload)
        rows = build_rows(msg.topic, payload)
        insert_rows(userdata["conn"], rows)
        print(f"[ingester] inserted {len(rows)} rows from {msg.topic}")
    except Exception as e:
        print(f"[ingester] error processing message from {msg.topic}: {e}")


def main():
    while True:
        try:
            conn = get_conn()

            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
            client.user_data_set({"conn": conn})
            client.on_connect = on_connect
            client.on_message = on_message
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f"[ingester] fatal loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
