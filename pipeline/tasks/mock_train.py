import os
import shutil
from pipeline.config import STUDENT_MODEL_PATH, TRAIN_MODEL_DIR, BEST_MODEL_PATH

def run_mock_training():
    """
    Giả lập quá trình huấn luyện: Chỉ copy model cũ sang folder kết quả.
    """
    from .train_engine import ensure_base_models
    ensure_base_models()
    
    print("🎭 [Mock Train] Đang giả lập quá trình huấn luyện...")
    
    # Tạo folder weights nếu chưa có
    weights_dir = os.path.dirname(BEST_MODEL_PATH)
    os.makedirs(weights_dir, exist_ok=True)
    
    if os.path.exists(STUDENT_MODEL_PATH):
        shutil.copy(STUDENT_MODEL_PATH, BEST_MODEL_PATH)
        print(f"✅ [Mock Train] Đã copy model từ {STUDENT_MODEL_PATH} sang {BEST_MODEL_PATH}")
        print("🚀 Sẵn sàng để test OTA Deployment!")
    else:
        print(f"❌ [Mock Train] Không tìm thấy model gốc tại {STUDENT_MODEL_PATH}")

if __name__ == "__main__":
    run_mock_training()
