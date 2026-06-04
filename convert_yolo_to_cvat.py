#!/usr/bin/env python3
"""
Convert YOLO 1.1 format → CVAT XML format và upload annotations
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import requests
from requests.auth import HTTPBasicAuth

# Config
CVAT_URL = "http://localhost:8080"
CVAT_USER = "django"
CVAT_PASS = "Rmr2612+"
WORK_DIR = "./cvat_temp"
IMG_DIR = f"{WORK_DIR}/images"
LBL_DIR = f"{WORK_DIR}/obj_train_data"

import json

# Class mapping via Environment Variables
try:
    _labels_env = os.environ.get("YOLO_LABELS", '{"0": "Bus", "1": "Car", "2": "Motor", "3": "Truck"}')
    CLASS_NAMES = {int(k): v for k, v in json.loads(_labels_env).items()}
except Exception as e:
    print(f"Warning: Failed to parse YOLO_LABELS from environment: {e}")
    CLASS_NAMES = {0: "Bus", 1: "Car", 2: "Motor", 3: "Truck"}

def get_image_size(img_path):
    """Lấy kích thước ảnh"""
    try:
        img = Image.open(img_path)
        return img.width, img.height
    except:
        return 1920, 1080  # Default size nếu không đọc được

def yolo_to_json_annotations(image_files, label_files):
    """
    Convert YOLO format → CVAT JSON annotations format
    """
    shapes = []
    frame_id = 0
    
    for img_file, txt_file in zip(sorted(image_files), sorted(label_files)):
        img_path = os.path.join(IMG_DIR, img_file)
        txt_path = os.path.join(LBL_DIR, txt_file)
        
        # Lấy kích thước ảnh
        width, height = get_image_size(img_path)
        
        # Đọc YOLO file
        if os.path.exists(txt_path) and os.path.getsize(txt_path) > 0:
            with open(txt_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split()
                    class_id = int(parts[0])
                    x_center = float(parts[1])
                    y_center = float(parts[2])
                    box_width = float(parts[3])
                    box_height = float(parts[4])
                    
                    # Convert normalized → pixel coordinates
                    x_min = int((x_center - box_width / 2) * width)
                    y_min = int((y_center - box_height / 2) * height)
                    x_max = int((x_center + box_width / 2) * width)
                    y_max = int((y_center + box_height / 2) * height)
                    
                    # Ensure bounds
                    x_min = max(0, min(x_min, width))
                    y_min = max(0, min(y_min, height))
                    x_max = max(0, min(x_max, width))
                    y_max = max(0, min(y_max, height))
                    
                    # Create shape object
                    shape = {
                        'type': 'rectangle',
                        'occluded': False,
                        'z_order': 0,
                        'label_id': class_id,
                        'points': [x_min, y_min, x_max, y_max],
                        'attributes': [],
                        'frame': frame_id,
                        'group': 0,
                        'source': 'manual',
                        'rotation': 0.0
                    }
                    shapes.append(shape)
        
        frame_id += 1
    
    return shapes

def upload_annotations(task_id, shapes_json):
    """
    Upload annotations vào CVAT qua API
    Using JSON format với shapes
    """
    auth = HTTPBasicAuth(CVAT_USER, CVAT_PASS)
    
    print(f"📤 Uploading annotations...")
    print(f"   Total shapes: {len(shapes_json)}")
    
    # Prepare JSON payload
    annotations_json = {
        "version": 1,
        "tags": [],
        "shapes": shapes_json,
        "tracks": []
    }
    
    url = f"{CVAT_URL}/api/jobs/2/annotations"  # Job 2 for Task 3
    
    try:
        print(f"   URL: {url}")
        print(f"   Payload size: {len(str(annotations_json))} bytes")
        
        response = requests.put(
            url, 
            json=annotations_json,
            auth=auth, 
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print(f"\n✅ Upload thành công!")
            return True
        else:
            print(f"\n❌ Upload thất bại!")
            print(f"   Response: {response.text[:300]}")
            return False
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        return False

def main():
    print("=" * 70)
    print("🔄 CONVERT YOLO → CVAT XML & UPLOAD")
    print("=" * 70)
    
    # Input task_id
    task_id = input("\n📝 Nhập Task ID: ").strip()
    if not task_id:
        print("❌ Task ID không được để trống")
        return
    
    # Danh sách ảnh & nhãn
    img_files = sorted([f for f in os.listdir(IMG_DIR) if os.path.isfile(os.path.join(IMG_DIR, f))])
    txt_files = sorted([f for f in os.listdir(LBL_DIR) if os.path.isfile(os.path.join(LBL_DIR, f))])
    
    print(f"\n📊 Dữ liệu:")
    print(f"   Ảnh: {len(img_files)} file")
    print(f"   Nhãn: {len(txt_files)} file")
    
    if len(img_files) != len(txt_files):
        print(f"\n❌ Lỗi: Số lượng ảnh ({len(img_files)}) không khớp nhãn ({len(txt_files)})")
        return
    
    # Convert
    print(f"\n🔄 Đang convert YOLO → JSON annotations...")
    shapes_json = yolo_to_json_annotations(img_files, txt_files)
    print(f"   ✅ Converted: {len(shapes_json)} bounding boxes")
    
    # Upload
    print(f"\n📤 Đang upload annotations...")
    success = upload_annotations(task_id, shapes_json)
    
    if success:
        print(f"\n🎉 HOÀN TẤT!")
        print(f"   1. Mở CVAT: {CVAT_URL}/tasks/{task_id}")
        print(f"   2. Nhãn AI (bounding box) sẽ được hiển thị")
        print(f"   3. Annotators có thể review & refine")
    else:
        print(f"\n❌ Upload thất bại. Kiểm tra:")
        print(f"   - Task ID có đúng không")
        print(f"   - CVAT server có chạy không")
        print(f"   - Credentials đúng không")

if __name__ == "__main__":
    main()
