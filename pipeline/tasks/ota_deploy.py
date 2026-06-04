import os
import time
from pipeline.utils.minio_handler import MinioHandler
from pipeline.utils.mqtt_handler import MQTTHandler
from pipeline.utils.db_handler import DBHandler
from pipeline.config import (
    BEST_MODEL_PATH, BUCKET_PRODUCTION_MODELS, MINIO_URL
)

def deploy_new_model(camera_id="cam_01"):
    """
    Triển khai model mới nhất sau khi huấn luyện thành công.
    """
    minio = MinioHandler()
    db = DBHandler()
    mqtt = MQTTHandler(db)
    
    if not os.path.exists(BEST_MODEL_PATH):
        print(f"❌ Không tìm thấy model tại {BEST_MODEL_PATH}. Hãy chạy retraining trước.")
        return

    # 1. Định nghĩa version mới (Dựa trên timestamp)
    version = f"v{time.strftime('%Y%m%d_%H%M')}"
    object_name = f"{version}.pt"
    
    # 2. Upload lên Production Bucket
    print(f"🚀 [OTA] Đang upload model {version} lên MinIO...")
    minio.upload_file(BUCKET_PRODUCTION_MODELS, object_name, BEST_MODEL_PATH)
    
    # 3. Tạo link download (Giả định MinIO public hoặc dùng presigned URL)
    # Ở đây mình dùng link trực tiếp vì các container trong cùng mạng
    model_url = f"http://{MINIO_URL}/{BUCKET_PRODUCTION_MODELS}/{object_name}"
    
    # 4. Bắn lệnh OTA qua MQTT
    print(f"📡 [OTA] Phát lệnh cập nhật tới {camera_id}...")
    mqtt.send_ota_update(camera_id, version, model_url)
    
    print(f"✅ [OTA] Hoàn tất triển khai model {version}")

if __name__ == "__main__":
    deploy_new_model()
