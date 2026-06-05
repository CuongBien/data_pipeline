import os

# ================= CELERY CONFIG =================
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# ================= MINIO CONFIG =================
MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadminpassword")
MINIO_SECURE = False

# Buckets
BUCKET_RAW_DATA = "raw-data"
BUCKET_PSEUDO_LABELS = "pseudo-labels"
BUCKET_ARCHIVED_IMAGES = "archived-images"
BUCKET_ARCHIVED_LABELS = "archived-labels"
BUCKET_LABELED_DATA = "labeled-data"

# ================= CVAT CONFIG =================
CVAT_URL = os.getenv("CVAT_URL", "http://host.docker.internal:8080")
CVAT_USER = os.getenv("CVAT_USER", "django")
CVAT_PASS = os.getenv("CVAT_PASS", "Rmr2612+")
CVAT_PROJECT_ID = os.getenv("CVAT_PROJECT_ID", "1")
CVAT_CLOUD_STORAGE_ID = int(os.getenv("CVAT_CLOUD_STORAGE_ID", "5"))
# Traefik CVAT (port 8080) route theo Host 127.0.0.1 — thiếu header → 404 toàn bộ /api/*
CVAT_HOST_HEADER = os.getenv("CVAT_HOST_HEADER", "127.0.0.1")
# Endpoint MinIO mà container CVAT reach được (tránh alias DNS "minio" trùng mqtt trên mlops_traffic_net)
CVAT_MINIO_ENDPOINT = os.getenv("CVAT_MINIO_ENDPOINT", "http://core-backbone-minio-1:9000")

# ================= TELEGRAM ALERT =================
TELEGRAM_TOKEN = "8657283198:AAFc2P75rdlPPBEm9ID-N0jV25YMXX487jY"
TELEGRAM_CHAT_ID = "5994574529"
BOT_NAME = "TraffiJetsonAlertBot"

# ================= AUTOMATION THRESHOLDS =================
SYNC_BATCH_THRESHOLD = 2  # Ngưỡng thấp để test nhanh
TRAIN_DATA_THRESHOLD = 5  # Ngưỡng thấp để test luồng tự động

# ================= MQTT CONFIG =================
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "traffic/detections")
MQTT_QOS = 1
MQTT_CLIENT_ID = f"server_subscriber_{os.getpid()}"
MQTT_TRACKED_TOPIC = os.getenv("MQTT_TRACKED_TOPIC", "traffic/tracked")

# ================= DB CONFIG =================
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "traffic_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password123")
DB_TABLE = os.getenv("DB_TABLE", "detections")
DB_RETRY_MAX_ATTEMPTS = 5
DB_RETRY_BASE_SECONDS = 1.0

# ================= PROJECT CONFIG =================
YOLO_CLASSES = ["Bus", "Car", "Motor", "Truck"]
MODEL_PATH = "pipeline/model/yolo26x.pt"

WORK_DIR = "./cvat_temp"
IMG_DIR = os.path.join(WORK_DIR, "images")
LBL_DIR = os.path.join(WORK_DIR, "labels")
MODEL_DIR = os.path.join(WORK_DIR, "model")
IMG_ZIP = os.path.join(WORK_DIR, "images.zip")
ANN_ZIP = os.path.join(WORK_DIR, "annotations.zip")

# Ensure directories exist
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(LBL_DIR, exist_ok=True)
# ================= TRAINING & OTA =================
BUCKET_BASE_DATASET = "base-dataset"
BUCKET_PRODUCTION_MODELS = "production-models"

TRAIN_WORK_DIR = os.path.join(WORK_DIR, "training")
TRAIN_DATA_DIR = os.path.join(TRAIN_WORK_DIR, "dataset")
TRAIN_MODEL_DIR = os.path.join(TRAIN_WORK_DIR, "models")

# Ngưỡng mAP tối thiểu để chấp nhận model mới (so với model cũ)
MAP_IMPROVEMENT_THRESHOLD = 0.01
# Đường dẫn model cho Training
TEACHER_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8m_teacher.pt")
STUDENT_MODEL_PATH = os.path.join(MODEL_DIR, "yolov8n_pruned.pt")
BEST_MODEL_PATH = os.path.join(TRAIN_MODEL_DIR, "weights/best.pt")
