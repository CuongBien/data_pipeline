import json
import os
from minio import Minio
import requests
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pipeline.config import (
    MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, BUCKET_RAW_DATA,
    CVAT_URL, CVAT_USER, CVAT_PASS, CVAT_CLOUD_STORAGE_ID
)

def create_manifest():
    # 1. Kết nối MinIO
    client = Minio(MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=False)
    
    # 2. Liệt kê ảnh và tạo nội dung manifest
    # CVAT manifest v1.1: dòng đầu là version, các dòng sau là info ảnh
    manifest_lines = [json.dumps({"version": "1.1"})]
    
    from PIL import Image
    import io
    
    objects = client.list_objects(BUCKET_RAW_DATA, recursive=True)
    count = 0
    for obj in objects:
        if obj.object_name.lower().endswith(('.jpg', '.jpeg', '.png')):
            # Tải ảnh về RAM để lấy kích thước thật
            data = client.get_object(BUCKET_RAW_DATA, obj.object_name).read()
            with Image.open(io.BytesIO(data)) as img:
                w, h = img.size
            
            item = {
                "name": obj.object_name,
                "extension": obj.object_name.split('.')[-1],
                "width": w,
                "height": h,
                "checksum": obj.etag.strip('"')
            }
            manifest_lines.append(json.dumps(item))
            count += 1
            
    if count == 0:
        print("⚠️ No images found in raw-data bucket.")
        return

    # 3. Lưu và upload manifest.jsonl
    manifest_content = "\n".join(manifest_lines)
    manifest_path = "manifest.jsonl"
    with open(manifest_path, "w") as f:
        f.write(manifest_content)
        
    client.fput_object(BUCKET_RAW_DATA, "manifest.jsonl", manifest_path)
    print(f"✅ Uploaded manifest.jsonl with {count} images to {BUCKET_RAW_DATA}")

    # 4. Báo cho CVAT để link manifest (Dùng API cloudstorages/ID)
    auth = (CVAT_USER, CVAT_PASS)
    url = f"{CVAT_URL}/api/cloudstorages/{CVAT_CLOUD_STORAGE_ID}"
    
    # Chỉ gửi trường manifests để tránh lỗi validate owner
    payload = {
        "manifests": ["manifest.jsonl"]
    }
    
    resp = requests.patch(url, json=payload, auth=auth)
    if resp.status_code == 200:
        print("✅ CVAT Cloud Storage updated with manifest!")
    else:
        print(f"❌ Failed to update CVAT: {resp.text}")

if __name__ == "__main__":
    create_manifest()
