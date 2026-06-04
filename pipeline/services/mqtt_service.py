import sys
import os

# Add the project root to sys.path so we can import 'pipeline'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pipeline.utils.mqtt_handler import MQTTHandler
from pipeline.utils.db_handler import DBHandler

def main():
    print("🚀 Starting MQTT Listener Service...")
    db = DBHandler()
    mqtt = MQTTHandler(db)
    
    try:
        mqtt.run()
    except KeyboardInterrupt:
        print("🛑 Stopping MQTT Listener...")
    except Exception as e:
        print(f"❌ [MQTT Service] Critical error: {e}")

if __name__ == "__main__":
    main()
