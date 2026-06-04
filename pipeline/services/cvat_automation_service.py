import os
import time
import io
from PIL import Image
from ..celery_app import app
from ..config import (
    BUCKET_RAW_DATA, BUCKET_PSEUDO_LABELS, BUCKET_ARCHIVED_IMAGES, BUCKET_ARCHIVED_LABELS,
    BUCKET_LABELED_DATA, IMG_DIR, LBL_DIR, IMG_ZIP, ANN_ZIP, WORK_DIR,
    SYNC_BATCH_THRESHOLD, TRAIN_DATA_THRESHOLD, DB_TABLE
)
from ..utils.minio_handler import MinioHandler
from ..utils.cvat_handler import CVATHandler
from ..utils.data_processor import DataProcessor
from ..utils.inference_handler import InferenceHandler
from ..utils.db_handler import DBHandler
from ..utils.telegram_handler import TelegramHandler
from ..config import SYNC_BATCH_THRESHOLD, TRAIN_DATA_THRESHOLD

# Initialize handlers
inference_engine = None

def get_inference_engine():
    global inference_engine
    if inference_engine is None:
        inference_engine = InferenceHandler()
    return inference_engine

@app.task
def auto_inference_task():
    """Celery task to generate pseudo-labels for records with status 'NEW'."""
    db = DBHandler()
    minio = MinioHandler()
    engine = get_inference_engine()
    
    # Đảm bảo các bucket tồn tại
    minio.ensure_bucket(BUCKET_RAW_DATA)
    minio.ensure_bucket(BUCKET_PSEUDO_LABELS)
    
    # 1. Lấy danh sách bản ghi mới từ DB
    records = db.get_new_records(limit=20)
    if not records:
        print("💤 [Inference] No 'NEW' records to process.")
        return "No data"

    processed_count = 0
    for rec in records:
        img_name = rec['image_url']
        txt_name = img_name.rsplit('.', 1)[0] + ".txt"
        
        if minio.exists(BUCKET_PSEUDO_LABELS, txt_name):
            continue
            
        print(f"🧠 [Inference] Processing record {rec['id']}: {img_name}...")
        local_img_path = os.path.join(IMG_DIR, img_name)
        try:
            minio.download_file(BUCKET_RAW_DATA, img_name, local_img_path)
            txt_content = engine.predict(local_img_path)
            
            if txt_content:
                txt_bytes = io.BytesIO(txt_content.encode('utf-8'))
                minio.upload_file(BUCKET_PSEUDO_LABELS, txt_name, txt_bytes, length=len(txt_content.encode('utf-8')))
                
                # Cập nhật trạng thái sang INFERRED
                db.update_status([rec['id']], 'INFERRED')
                print(f"✅ [Inference] Generated pseudo-label for {img_name} and marked as INFERRED")
                processed_count += 1
        except Exception as e:
            print(f"❌ [Inference] Error on record {rec['id']}: {e}")
        finally:
            if os.path.exists(local_img_path):
                os.remove(local_img_path)
                
    return f"Inferred {processed_count} records"

@app.task
def sync_cvat_task():
    """Celery task to sync 'INFERRED' records to CVAT using Cloud Storage."""
    db = DBHandler()
    minio = MinioHandler()
    cvat = CVATHandler()
    processor = DataProcessor()

    # 1. Lấy danh sách bản ghi đã qua bước Inference (status = 'INFERRED')
    records = db.get_records_by_status('INFERRED', limit=SYNC_BATCH_THRESHOLD)
    
    if not records or len(records) < SYNC_BATCH_THRESHOLD:
        print(f"💤 [Sync] Only {len(records)} records ready. Waiting for {SYNC_BATCH_THRESHOLD}...")
        return f"Waiting for batch (current: {len(records)})"

    # Sắp xếp để khớp thứ tự
    records = sorted(records, key=lambda x: x['image_url'])
    record_ids = [r['id'] for r in records]
    img_files = [r['image_url'] for r in records]

    print(f"🚀 [Sync] Starting Cloud Storage sync for {len(records)} records...")

    # 2. Lấy kích thước ảnh (Chỉ tải 1 tấm duy nhất để lấy resolution)
    sample_img = img_files[0]
    sample_path = os.path.join(IMG_DIR, sample_img)
    try:
        minio.download_file(BUCKET_RAW_DATA, sample_img, sample_path)
        with Image.open(sample_path) as im:
            img_size = im.size # (width, height)
        os.remove(sample_path)
    except Exception as e:
        print(f"❌ [Sync] Failed to get image size: {e}")
        img_size = (1920, 1080) # Fallback mặc định

    # 3. Tổng hợp nhãn giả từ MinIO (Chỉ tải file .txt)
    shapes = []
    label_map = cvat.get_label_mapping()
    
    for idx, rec in enumerate(records):
        img_name = rec["image_url"]
        txt_name = img_name.rsplit('.', 1)[0] + ".txt"
        
        if minio.exists(BUCKET_PSEUDO_LABELS, txt_name):
            txt_content = minio.download_file_as_str(BUCKET_PSEUDO_LABELS, txt_name)
            # Chuyển đổi sang format CVAT shapes
            new_shapes = processor.parse_yolo_to_cvat(txt_content, idx, label_map, img_size)
            shapes.extend(new_shapes)

    # 4. Tạo Task trên CVAT dùng Cloud Storage
    try:
        task_name = f"Batch_{int(time.time())}_{len(records)}imgs"
        task_id = cvat.create_task(task_name, img_files)
        
        if shapes:
            cvat.upload_annotations(task_id, shapes)
            print(f"📝 [Sync] Uploaded {len(shapes)} shapes to Task {task_id}.")
        
        # 5. Cập nhật DB và thông báo
        db.update_status(record_ids, 'IN_CVAT', cvat_task_id=int(task_id))
        
        tg = TelegramHandler()
        tg.alert_new_task(task_id, len(records))

        # 6. Archive (Di chuyển ảnh và nhãn sang kho lưu trữ)
        for img_name in img_files:
            try:
                minio.move_object(BUCKET_RAW_DATA, img_name, BUCKET_ARCHIVED_IMAGES)
                txt_name = img_name.rsplit('.', 1)[0] + ".txt"
                if minio.exists(BUCKET_PSEUDO_LABELS, txt_name):
                    minio.move_object(BUCKET_PSEUDO_LABELS, txt_name, BUCKET_ARCHIVED_LABELS)
            except Exception as e:
                print(f"⚠️ [Sync] Archive error for {img_name}: {e}")

    except Exception as e:
        print(f"❌ [Sync] Critical error: {e}")
        raise e

    return f"Synced {len(records)} records to CVAT task {task_id} via Cloud Storage"

@app.task
def export_labeled_data_task():
    """Quét các task hoàn thành trên CVAT để tải nhãn về MinIO."""
    db = DBHandler()
    minio = MinioHandler()
    cvat = CVATHandler()
    
    minio.ensure_bucket(BUCKET_LABELED_DATA)

    # 1. Lấy danh sách các CVAT Task ID đang chờ (status = 'IN_CVAT')
    # Ở đây mình sẽ lấy danh sách task_id duy nhất
    active_tasks = db.get_active_cvat_tasks() # Cần implement hàm này
    
    for task_id in active_tasks:
        try:
            if cvat.is_task_ready_for_export(task_id):
                print(f"📥 [Export] Task {task_id} is completed! Extracting labels...")
                
                # 2. Lấy danh sách file gốc để map tên
                original_filenames = db.get_task_filenames(task_id)
                
                # 3. Export và giải nén nhãn
                labels_dict = cvat.export_task_annotations(task_id, original_filenames)
                
                for label_name, content in labels_dict.items():
                    # Upload nhãn (.txt) lên MinIO
                    minio.upload_file(
                        BUCKET_LABELED_DATA, 
                        f"labels/{label_name}", 
                        io.BytesIO(content.encode('utf-8')), 
                        length=len(content)
                    )
                    
                    # Di chuyển ảnh tương ứng từ archived-images sang labeled-data/images
                    img_name = label_name.replace('.txt', '.jpg')
                    try:
                        minio.move_object(BUCKET_ARCHIVED_IMAGES, img_name, BUCKET_LABELED_DATA, f"images/{img_name}")
                    except Exception as img_err:
                        print(f"⚠️ [Export] Could not move image {img_name}: {img_err}")
                
                # Cập nhật DB: IN_CVAT -> LABELED
                db.update_status_by_task(task_id, "LABELED")
                print(f"✅ [Export] Task {task_id} synced to labeled-data bucket.")

                # 4. Gửi Telegram Alert
                tg = TelegramHandler()
                tg.alert_task_archived(task_id)

                # 5. Kiểm tra ngưỡng Train (Đếm số lượng ảnh chính xác từ DB)
                # Lấy tổng số bản ghi có trạng thái 'LABELED'
                sql_count = f"SELECT COUNT(*) FROM {DB_TABLE} WHERE status = 'LABELED'"
                with db.connection.cursor() as cur:
                    cur.execute(sql_count)
                    total_labeled_images = cur.fetchone()[0]
                
                if total_labeled_images >= TRAIN_DATA_THRESHOLD:
                    print(f"🔥 [Auto-Train] Threshold reached ({total_labeled_images}/{TRAIN_DATA_THRESHOLD}). Triggering training pipeline...")
                    # Kích hoạt Training Pipeline (Dùng is_mock=True để test cho an toàn)
                    training_pipeline_task.delay(is_mock=True)
                    tg.alert_training_ready(total_labeled_images)
        except Exception as e:
            print(f"❌ [Export] Error for task {task_id}: {e}")

@app.task
def training_pipeline_task(is_mock=False):
    """
    Task tổng hợp: Prepare Data -> Train -> OTA Deploy.
    """
    from ..tasks.prepare_training_data import prepare_data_v2
    from ..tasks.train_engine import run_retraining
    from ..tasks.mock_train import run_mock_training
    from ..tasks.ota_deploy import deploy_new_model
    
    print("🎬 [Pipeline] Starting Training & Deployment Pipeline...")
    try:
        # 1. Trộn dữ liệu thông minh
        prepare_data_v2()
        
        # 2. Huấn luyện (Dùng Mock nếu đang ở chế độ test)
        if is_mock:
            run_mock_training()
        else:
            run_retraining()
            
        # 3. Triển khai từ xa (OTA)
        deploy_new_model()
        
        print("🏁 [Pipeline] Full cycle completed successfully!")
        return "Success"
    except Exception as e:
        print(f"💥 [Pipeline] Failed: {e}")
        return f"Failed: {e}"
