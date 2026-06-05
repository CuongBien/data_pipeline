import paho.mqtt.client as mqtt
import time
import os

def on_message(client, userdata, msg):
    print(f"✅ RECEIVED on host: {msg.topic} -> {msg.payload.decode()[:50]}")

client = mqtt.Client()
client.on_message = on_message

mqtt_broker = os.getenv("MQTT_BROKER", "127.0.0.1")
print(f"🔍 Connecting to {mqtt_broker}:1883...")
client.connect(mqtt_broker, 1883)
client.subscribe("#")
print("👂 Listening for ALL messages on localhost:1883... (Press Ctrl+C to stop)")
client.loop_forever()
