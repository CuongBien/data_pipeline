from minio import Minio
from minio.commonconfig import CopySource
from ..config import MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE

class MinioHandler:
    def __init__(self):
        self.client = Minio(
            MINIO_URL,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )

    def list_objects(self, bucket):
        try:
            return [obj.object_name for obj in self.client.list_objects(bucket, recursive=True)]
        except Exception:
            return []

    def download_file_as_str(self, bucket_name, object_name):
        """Tải file và trả về nội dung dạng string."""
        try:
            response = self.client.get_object(bucket_name, object_name)
            content = response.read().decode('utf-8')
            response.close()
            response.release_conn()
            return content
        except Exception as e:
            print(f"❌ [MinIO] Download as string failed: {e}")
            return ""

    def exists(self, bucket, name):
        try:
            self.client.stat_object(bucket, name)
            return True
        except Exception:
            return False

    def download_file(self, bucket, object_name, local_path):
        self.client.fget_object(bucket, object_name, local_path)

    def upload_file(self, bucket, object_name, data, length=None):
        if hasattr(data, 'read'): # If it's a file-like object
            self.client.put_object(bucket, object_name, data, length=length)
        else: # If it's a local path
            self.client.fput_object(bucket, object_name, data)

    def move_object(self, src_bucket, src_name, dest_bucket, dest_name=None):
        if dest_name is None:
            dest_name = src_name
        
        if not self.client.bucket_exists(dest_bucket):
            self.client.make_bucket(dest_bucket)
            
        src = CopySource(src_bucket, src_name)
        self.client.copy_object(dest_bucket, dest_name, src)
        self.client.remove_object(src_bucket, src_name)

    def ensure_bucket(self, bucket_name):
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)
