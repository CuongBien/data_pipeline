import json
import os
import time
from typing import TypedDict, List, Optional
import psycopg2
from paho.mqtt import client as mqtt_client

# ================= CONFIG (Ưu tiên Docker Env) =================
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt") # Mặc định là 'mqtt' trong docker
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "traffic/detections")
MQTT_QOS = int(os.getenv("MQTT_QOS", "1"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"subscriber_{int(time.time())}")

DB_HOST = os.getenv("DB_HOST", "db") # Mặc định là 'db' trong docker
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "traffic_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password123")
DB_TABLE = os.getenv("DB_TABLE", "detections")

# ================= DATA TYPES =================
class DetectionPayload(TypedDict):
    camera_id: str
    image_url: str
    timestamp: float
    trigger_reason: str
    edge_predictions: List[dict]

# ================= DATABASE HANDLER =================
class DBHandler:
    def __init__(self):
        self.conn = None

    def connect(self):
        print(f"🐘 [DB] Connecting to {DB_NAME} at {DB_HOST}:{DB_PORT}...")
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASSWORD,
                connect_timeout=5
            )
            self.conn.autocommit = True
            print("✅ [DB] Connected successfully.")
        except Exception as e:
            print(f"❌ [DB] Connection failed: {e}")
            raise

    def insert(self, p: DetectionPayload):
        sql = f"""
        INSERT INTO {DB_TABLE} (
            camera_id, image_url, "timestamp", trigger_reason, status, edge_predictions
        ) VALUES (%s, %s, to_timestamp(%s), %s, 'NEW', %s)
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            with self.conn.cursor() as cur:
                cur.execute(sql, (
                    p["camera_id"], p["image_url"], p["timestamp"], 
                    p["trigger_reason"], json.dumps(p["edge_predictions"])
                ))
        except Exception as e:
            print(f"❌ [DB] Insert error: {e}")
            self.conn = None # Reset connection for retry

# ================= MQTT HANDLER =================
class MQTTHandler:
    def __init__(self, db: DBHandler):
        self.db = db
        # Tương thích paho-mqtt 2.0
        try:
            self.client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, MQTT_CLIENT_ID)
        except AttributeError:
            self.client = mqtt_client.Client(MQTT_CLIENT_ID)
            
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"📡 [MQTT] Connected to broker at {MQTT_BROKER}:{MQTT_PORT}")
            # Debug: Nghe TẤT CẢ các topic để xem có tin nhắn nào tới không
            client.subscribe("#", qos=MQTT_QOS)
            print(f"📥 [MQTT] Subscribed to ALL topics (#) for debugging")
        else:
            print(f"❌ [MQTT] Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            print(f"📩 [MQTT] Got message on topic: {msg.topic}")
            print(f"📦 [MQTT] Payload: {msg.payload.decode()[:100]}...")
            
            if msg.topic != MQTT_TOPIC:
                return # Bỏ qua nếu không phải topic chúng ta cần
            data = json.loads(msg.payload.decode())
            payload: DetectionPayload = {
                "camera_id": str(data.get("camera_id", "unknown")),
                "image_url": str(data.get("image_url", "")),
                "timestamp": float(data.get("timestamp", time.time())),
                "trigger_reason": str(data.get("trigger_reason", "")),
                "edge_predictions": data.get("detections", [])
            }
            self.db.insert(payload)
            print(f"📝 [DB] Recorded 1 detection from {payload['camera_id']}")
        except Exception as e:
            print(f"⚠️ [MQTT] Message processing error: {e}")

    def run(self):
        import socket
        try:
            mqtt_ip = socket.gethostbyname(MQTT_BROKER)
            print(f"🔍 [DNS] '{MQTT_BROKER}' resolved to IP: {mqtt_ip}")
        except Exception as e:
            print(f"⚠️ [DNS] Could not resolve '{MQTT_BROKER}': {e}")
            
        print(f"🚀 [MQTT] Attempting to connect to {MQTT_BROKER}...")
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.client.loop_forever()

# ================= MAIN =================
if __name__ == "__main__":
    db = DBHandler()
    # Thử kết nối DB trước khi chạy MQTT
    for i in range(5):
        try:
            db.connect()
            break
        except:
            print(f"⏳ Waiting for DB... (attempt {i+1}/5)")
            time.sleep(2)
            
    mqtt = MQTTHandler(db)
    mqtt.run()
