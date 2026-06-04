from minio import Minio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pipeline.config import MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, BUCKET_RAW_DATA, BUCKET_ARCHIVED_IMAGES

def list_minio():
    client = Minio(
        MINIO_URL,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    for bucket in [BUCKET_RAW_DATA, BUCKET_ARCHIVED_IMAGES]:
        print(f"📦 Bucket: {bucket}")
        try:
            objects = client.list_objects(bucket)
            for obj in objects:
                print(f"  - {obj.object_name}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    list_minio()
