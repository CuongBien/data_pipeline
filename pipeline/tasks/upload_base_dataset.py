import os
from pipeline.utils.minio_handler import MinioHandler
from pipeline.config import BUCKET_BASE_DATASET, BUCKET_PRODUCTION_MODELS

def upload_base_data_recursive(local_data_dir):
    """
    Tự động quét và upload toàn bộ cấu trúc folder data lên MinIO.
    Hỗ trợ: train/ val/ test/
    """
    minio = MinioHandler()
    minio.ensure_bucket(BUCKET_BASE_DATASET)
    
    print(f"🚀 Bắt đầu quét dữ liệu tại {local_data_dir}...")
    
    count = 0
    # os.walk để quét mọi thư mục con
    for root, dirs, files in os.walk(local_data_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.txt')):
                local_path = os.path.join(root, file)
                # Tạo object_name bằng cách lấy đường dẫn tương đối (vd: train/images/1.jpg)
                rel_path = os.path.relpath(local_path, local_data_dir)
                object_name = rel_path.replace("\\", "/") # Chuẩn hóa đường dẫn cho MinIO
                
                minio.upload_file(BUCKET_BASE_DATASET, object_name, local_path)
                count += 1
                if count % 100 == 0:
                    print(f"  - Đã upload {count} file...")

    print(f"✅ Hoàn tất! Đã upload {count} file lên bucket {BUCKET_BASE_DATASET}.")

    # Upload Models
    models_to_upload = {
        "yolov8m_teacher.pt": "/app/models/teacher.pt",
        "yolov8n_pruned.pt": "/app/models/student_pruned.pt"
    }
    minio.ensure_bucket(BUCKET_PRODUCTION_MODELS)
    for obj_name, l_path in models_to_upload.items():
        if os.path.exists(l_path):
            print(f"📦 Đang upload model {obj_name} từ {l_path}...")
            minio.upload_file(BUCKET_PRODUCTION_MODELS, obj_name, l_path)
            print(f"✅ Đã upload model {obj_name}.")
        else:
            print(f"ℹ️ Không thấy model tại {l_path}. Bỏ qua.")

if __name__ == "__main__":
    # Đường dẫn bên trong container
    DATA_PATH = "/app/data" 
    upload_base_data_recursive(DATA_PATH)
