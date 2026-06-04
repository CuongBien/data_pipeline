import torch
import math
import os
from ultralytics import YOLO
from ultralytics.utils.torch_utils import ModelEMA
from ultralytics.utils import LOGGER
from pipeline.utils.minio_handler import MinioHandler
from pipeline.config import (
    TEACHER_MODEL_PATH, STUDENT_MODEL_PATH, BUCKET_PRODUCTION_MODELS,
    TRAIN_MODEL_DIR, TRAIN_DATA_DIR
)

# Thử import modelopt, nếu chưa cài sẽ báo lỗi cụ thể
try:
    import modelopt.torch.prune as mtp
except ImportError:
    LOGGER.warning("⚠️ Thư viện nvidia-modelopt chưa được cài đặt. Bước Pruning sẽ bị bỏ qua.")
    mtp = None

def ensure_base_models():
    """Tải teacher và student base từ MinIO nếu chưa có."""
    minio = MinioHandler()
    os.makedirs(os.path.dirname(TEACHER_MODEL_PATH), exist_ok=True)
    
    if not os.path.exists(TEACHER_MODEL_PATH):
        print("📥 Tải Teacher model từ MinIO...")
        minio.download_file(BUCKET_PRODUCTION_MODELS, "yolov8m_teacher.pt", TEACHER_MODEL_PATH)
        
    if not os.path.exists(STUDENT_MODEL_PATH):
        print("📥 Tải Student base model từ MinIO...")
        # Lấy bản pruned đã upload
        minio.download_file(BUCKET_PRODUCTION_MODELS, "yolov8n_pruned.pt", STUDENT_MODEL_PATH)

def get_pruned_trainer(teacher_model, data_yaml_path):
    """Tạo class Trainer tùy chỉnh với KD loss."""
    
    base_trainer = YOLO("yolov8n.pt").task_map["detect"]["trainer"]

    class CustomPrunedTrainer(base_trainer):
        def _setup_train(self):
            super()._setup_train()
            # Đưa teacher lên đúng device sau khi trainer biết device
            self._teacher = teacher_model.to(self.device).model.eval()
            for p in self._teacher.parameters():
                p.requires_grad = False

            if mtp:
                def collect_func(batch):
                    return self.preprocess_batch(batch)["img"]

                def score_func(m):
                    m.eval()
                    self.validator.args.save = False
                    self.validator.args.plots = False
                    self.validator.args.verbose = False
                    self.validator.args.data = data_yaml_path
                    metrics = self.validator(model=m)
                    return metrics["fitness"]

                prune_constraints = {"flops": "70%"}
                self.model.is_fused = lambda: True
                LOGGER.info("--- ĐANG TÌM CẤU TRÚC TỐI ƯU (FASTNAS) ---")

                self.model, prune_res = mtp.prune(
                    model=self.model,
                    mode="fastnas",
                    constraints=prune_constraints,
                    dummy_input=torch.randn(1, 3, self.args.imgsz, self.args.imgsz).to(self.device),
                    config={
                        "score_func": score_func,
                        "checkpoint": "modelopt_fastnas_search_checkpoint.pth",
                        "data_loader": self.train_loader,
                        "collect_func": collect_func,
                        "max_iter_data_loader": 20,
                    },
                )
                self.model.to(self.device)
                self.ema = ModelEMA(self.model)
                LOGGER.info(f"--- ĐÃ CẮT VẬT LÝ THÀNH CÔNG: {prune_res} ---")

        def loss(self, batch, preds=None):
            """Override loss để thêm KD loss từ teacher."""
            student_loss, student_loss_items = super().loss(batch, preds)

            imgs = batch["img"].to(self.device)
            with torch.no_grad():
                teacher_preds = self._teacher(imgs)

            student_preds = self.model(imgs)

            kd_loss = 0
            if isinstance(teacher_preds, (list, tuple)) and isinstance(student_preds, (list, tuple)):
                for t_feat, s_feat in zip(teacher_preds, student_preds):
                    if isinstance(t_feat, torch.Tensor) and isinstance(s_feat, torch.Tensor):
                        if t_feat.shape != s_feat.shape:
                            s_feat = torch.nn.functional.interpolate(
                                s_feat, size=t_feat.shape[-2:], mode='bilinear', align_corners=False
                            )
                        kd_loss += torch.nn.functional.mse_loss(s_feat, t_feat)

            kd_weight = 0.5
            total_loss = student_loss + kd_weight * kd_loss
            return total_loss, student_loss_items

    return CustomPrunedTrainer

def run_retraining():
    ensure_base_models()
    
    data_yaml = os.path.join(TRAIN_DATA_DIR, "data.yaml")
    if not os.path.exists(data_yaml):
        raise FileNotFoundError("❌ Không tìm thấy data.yaml. Hãy chạy prepare_training_data task trước.")

    teacher = YOLO(TEACHER_MODEL_PATH)
    # Load model student (có thể là bản đã prune hoặc chưa)
    model = YOLO(STUDENT_MODEL_PATH)
    
    trainer_class = get_pruned_trainer(teacher, data_yaml)
    
    print("🚀 Bắt đầu quá trình Huấn luyện với KD + Pruning...")
    model.train(
        data=data_yaml,
        trainer=trainer_class,
        epochs=70,
        imgsz=640,
        batch=16, # Giảm batch size để tránh OOM trên server thông thường
        lr0=0.0001,
        device=0 if torch.cuda.is_available() else 'cpu',
        project=TRAIN_MODEL_DIR,
        name='retrain_kd_pruned',
        exist_ok=True
    )
    print(f"✅ Training hoàn tất. Model lưu tại: {TRAIN_MODEL_DIR}")

if __name__ == "__main__":
    run_retraining()
