import paho.mqtt.client as mqtt
import time

def on_message(client, userdata, msg):
    print(f"✅ RECEIVED on host: {msg.topic} -> {msg.payload.decode()[:50]}")

client = mqtt.Client()
client.on_message = on_message

print("🔍 Connecting to localhost:1883...")
client.connect("127.0.0.1", 1883)
client.subscribe("#")
print("👂 Listening for ALL messages on localhost:1883... (Press Ctrl+C to stop)")
client.loop_forever()
