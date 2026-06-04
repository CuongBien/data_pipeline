import json
import time
from paho.mqtt import client as mqtt_client
from pipeline.config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, MQTT_QOS, MQTT_CLIENT_ID
from pipeline.utils.db_handler import DBHandler

class MQTTHandler:
    def __init__(self, db_handler: DBHandler):
        self.db_handler = db_handler
        self.client = mqtt_client.Client(client_id=MQTT_CLIENT_ID, clean_session=False)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            print(f"[MQTT] Connection failed rc={rc}")
            return
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC, qos=MQTT_QOS)
        print(f"[MQTT] Subscribed to {MQTT_TOPIC}")

    def _on_message(self, client, userdata, message):
        raw_text = message.payload.decode("utf-8")
        print(f"📩 [MQTT] Got message on topic: {message.topic}")
        try:
            data = json.loads(raw_text)
            
            # Khớp logic với file core-backbone của bạn
            payload = {
                "camera_id": str(data.get("camera_id", "unknown")),
                "image_url": str(data.get("image_url", "")),
                "timestamp": float(data.get("timestamp", time.time())),
                "trigger_reason": str(data.get("trigger_reason", "")),
                "edge_predictions": data.get("detections", []) # Lấy danh sách vật thể từ Jetson
            }
            
            self.db_handler.insert_with_retry(payload)
            print(f"📝 [DB] Recorded 1 detection from {payload['camera_id']} with {len(payload['edge_predictions'])} objects.")
        except Exception as exc:
            print(f"❌ [MQTT] Error processing message: {exc}")

    def run(self):
        print(f"🚀 [MQTT] Attempting to connect to {MQTT_BROKER}...")
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.client.loop_forever()

    def publish(self, topic, payload):
        """Gửi tin nhắn MQTT."""
        # Nếu chưa connect thì connect
        if not self.client.is_connected():
            self.client.connect(MQTT_BROKER, MQTT_PORT)
        self.client.publish(topic, payload, qos=1)

    def send_ota_update(self, camera_id, version, model_url):
        """Gửi lệnh cập nhật model xuống thiết bị qua MQTT."""
        topic = f"traffic/cmd/{camera_id}"
        payload = {
            "command": "update_model",
            "version": version,
            "url": model_url,
            "timestamp": time.time()
        }
        self.publish(topic, json.dumps(payload))
        print(f"📡 [OTA] Sent update command to {camera_id}: Version {version}")
