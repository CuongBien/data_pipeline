import os
import zipfile
from PIL import Image
from ..config import IMG_DIR, LBL_DIR, YOLO_CLASSES

class DataProcessor:
    @staticmethod
    def parse_yolo_to_cvat(txt_content, frame_idx, label_map, img_size):
        """Chuyển đổi nội dung 1 file YOLO txt sang danh sách shape của CVAT."""
        shapes = []
        w, h = img_size
        
        # Tạo map từ Index (0, 1..) sang CVAT ID dựa trên YOLO_CLASSES
        # Ví dụ: {0: 15, 3: 16} (0 là car, 3 là motor)
        idx_to_id = {}
        for idx, name in enumerate(YOLO_CLASSES):
            if name in label_map:
                idx_to_id[idx] = label_map[name]

        for line in txt_content.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) < 5: continue

            try:
                cid = int(parts[0])
                if cid not in idx_to_id: continue

                x, y, bw, bh = map(float, parts[1:5])
                
                # Chuyển từ normalized center x,y sang absolute x1,y1,x2,y2
                x1 = int((x - bw/2) * w)
                y1 = int((y - bh/2) * h)
                x2 = int((x + bw/2) * w)
                y2 = int((y + bh/2) * h)

                shapes.append({
                    "type": "rectangle",
                    "label_id": idx_to_id[cid],
                    "points": [x1, y1, x2, y2],
                    "frame": frame_idx,
                    "occluded": False,
                    "outside": False,
                    "attributes": []
                })
            except:
                continue
        return shapes

    @staticmethod
    def create_zip(file_paths, output_zip):
        """Gộp các file vào một file zip."""
        with zipfile.ZipFile(output_zip, 'w') as z:
            for fpath in file_paths:
                if os.path.exists(fpath):
                    z.write(fpath, os.path.basename(fpath))
