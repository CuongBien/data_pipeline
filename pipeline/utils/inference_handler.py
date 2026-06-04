import os
import torch
import io
from ultralytics import YOLO
from ..config import MODEL_PATH

class InferenceHandler:
    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🧠 [Inference] Loading model on {self.device}...")
        self.model = YOLO(MODEL_PATH)
        self.model.to(self.device)

    def predict(self, img_path):
        results = self.model(img_path, imgsz=1280, conf=0.45, verbose=False, device=self.device)
        result = results[0]
        
        # Convert result to YOLO format string
        txt_content = ""
        for box in result.boxes:
            cls_id = int(box.cls[0])
            x, y, w, h = box.xywhn[0].tolist()
            txt_content += f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"
            
        return txt_content
