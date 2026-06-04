"""
Tracking Bridge — subscribes traffic/detections, runs IoU tracker, publishes traffic/tracked.

Run:  python -m pipeline.services.tracking_bridge
"""

import json
import os
import sys
import time

from paho.mqtt import client as mqtt_client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from pipeline.config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_QOS,
    MQTT_TOPIC,
    MQTT_TRACKED_TOPIC,
)
from pipeline.utils.iou_tracker import PerCameraTracker


def _make_client(client_id: str) -> mqtt_client.Client:
    try:
        return mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, client_id)
    except AttributeError:
        return mqtt_client.Client(client_id)


class TrackingBridge:
    def __init__(self) -> None:
        self._tracker = PerCameraTracker(iou_threshold=0.3, max_missed=5)
        pid = os.getpid()
        self._sub = _make_client(f"bridge_sub_{pid}")
        self._pub = _make_client(f"bridge_pub_{pid}")
        self._sub.on_connect = self._on_sub_connect
        self._sub.on_message = self._on_message
        self._sub.on_disconnect = lambda c, u, rc: (
            print(f"[BRIDGE] Sub disconnected rc={rc}") if rc != 0 else None
        )
        self._pub.on_disconnect = lambda c, u, rc: (
            print(f"[BRIDGE] Pub disconnected rc={rc}") if rc != 0 else None
        )

    def _on_sub_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe(MQTT_TOPIC, qos=MQTT_QOS)
            print(f"[BRIDGE] Subscribed to {MQTT_TOPIC}")
        else:
            print(f"[BRIDGE] Sub connect failed rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception as e:
            print(f"[BRIDGE] JSON parse error: {e}")
            return

        camera_id = str(data.get("camera_id", "unknown"))
        timestamp = float(data.get("timestamp", time.time()))

        try:
            tracked = self._tracker.update(
                camera_id, data.get("detections", []), timestamp
            )
        except Exception as e:
            print(f"[BRIDGE] Tracker error camera='{camera_id}': {e}")
            return

        enriched = {
            "camera_id": camera_id,
            "stream_id": camera_id,
            "image_url": data.get("image_url", ""),
            "timestamp": timestamp,
            "trigger_reason": data.get("trigger_reason", ""),
            "objects": tracked,
        }

        try:
            self._pub.publish(MQTT_TRACKED_TOPIC, json.dumps(enriched), qos=MQTT_QOS)
        except Exception as e:
            print(f"[BRIDGE] Publish error: {e}")

    def run(self) -> None:
        print(f"[BRIDGE] Starting  broker={MQTT_BROKER}:{MQTT_PORT}")
        print(
            f"[BRIDGE]   sub: {MQTT_TOPIC}  pub: {MQTT_TRACKED_TOPIC}  QoS={MQTT_QOS}"
        )
        self._pub.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self._pub.loop_start()
        self._sub.reconnect_delay_set(min_delay=1, max_delay=30)
        self._sub.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self._sub.loop_forever()

    def stop(self) -> None:
        self._sub.disconnect()
        self._pub.loop_stop()
        self._pub.disconnect()
        print("[BRIDGE] Stopped.")


def main() -> None:
    bridge = TrackingBridge()
    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()
