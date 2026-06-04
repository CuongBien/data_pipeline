import time
import requests
from ..config import CVAT_URL, CVAT_USER, CVAT_PASS, CVAT_PROJECT_ID, CVAT_CLOUD_STORAGE_ID

class CVATHandler:
    def __init__(self):
        self.url = CVAT_URL.rstrip('/')
        self.auth = (CVAT_USER, CVAT_PASS)
        self.project_id = int(CVAT_PROJECT_ID)
        self.headers = {"Host": "localhost"}

    def get_label_mapping(self):
        """Lấy danh sách label từ API labels."""
        endpoint = f"{self.url}/api/labels"
        params = {"project_id": self.project_id}
        resp = requests.get(endpoint, params=params, auth=self.auth, headers=self.headers)
        resp.raise_for_status()
        
        results = resp.json().get("results", [])
        return {l["name"]: l["id"] for l in results}

    def create_task(self, name, filenames):
        """Tạo task mới từ danh sách file trên Cloud Storage."""
        endpoint = f"{self.url}/api/tasks"
        data = {"name": name, "project_id": self.project_id, "image_quality": 85}
        resp = requests.post(endpoint, json=data, auth=self.auth, headers=self.headers)
        resp.raise_for_status()
        task_id = resp.json()["id"]

        # Báo cho CVAT lấy ảnh từ Cloud Storage (MinIO)
        data_endpoint = f"{endpoint}/{task_id}/data/"
        print(f"📦 [CVAT] Creating data for task {task_id} using Cloud Storage ID: {CVAT_CLOUD_STORAGE_ID}")
        payload = {
            "image_quality": 85,
            "storage": "cloud_storage",
            "cloud_storage_id": int(CVAT_CLOUD_STORAGE_ID),
            "server_files": filenames,
            "use_zip_chunks": True,
            "use_cache": True
        }
        resp = requests.post(data_endpoint, json=payload, auth=self.auth, headers=self.headers)
        if resp.status_code >= 400:
            import sys
            sys.stderr.write(f"❌ [CVAT ERROR] Status: {resp.status_code}\n")
            sys.stderr.write(f"❌ [CVAT ERROR] Body: {resp.text}\n")
        resp.raise_for_status()
        
        self._wait_for_task_status(task_id)
        return task_id

    def upload_annotations(self, task_id, shapes):
        """Upload nhãn giả lên task."""
        endpoint = f"{self.url}/api/tasks/{task_id}/annotations/"
        data = {"shapes": shapes, "tracks": [], "tags": []}
        requests.put(endpoint, json=data, auth=self.auth, headers=self.headers).raise_for_status()

    def export_task_annotations(self, task_id, original_filenames):
        """Xuất nhãn từ CVAT, giải nén và đổi tên về nguyên bản."""
        import zipfile
        import io
        import re

        # Bước 1: Request export
        trigger_url = f"{self.url}/api/tasks/{task_id}/dataset/export"
        params = {"format": "YOLO 1.1", "save_images": "false"}
        
        print(f"📦 [CVAT] Exporting annotations for Task {task_id}...")
        resp = requests.post(trigger_url, params=params, auth=self.auth, headers=self.headers, timeout=10)
        resp.raise_for_status()
        
        request_id = resp.json().get("id") or resp.json().get("rq_id")

        # Bước 2: Poll status
        poll_url = f"{self.url}/api/requests/{request_id}"
        download_url = None
        for i in range(20):
            time.sleep(5)
            p_resp = requests.get(poll_url, auth=self.auth, headers=self.headers, timeout=10)
            status = p_resp.json().get("status")
            if status == "finished":
                download_url = p_resp.json().get("result_url")
                if download_url:
                    download_url = download_url.replace("http://localhost", self.url)
                break
        else: raise Exception("Export timeout")

        # Bước 3: Download và giải nén
        print(f"✨ [CVAT] Downloading and mapping labels...")
        d_resp = requests.get(download_url, auth=self.auth, headers=self.headers, timeout=60)
        d_resp.raise_for_status()
        
        extracted_labels = {} # {original_filename.txt: content}
        
        with zipfile.ZipFile(io.BytesIO(d_resp.content)) as z:
            # YOLO export của CVAT có cấu trúc: obj_train_data/filename.txt
            for zip_info in z.infolist():
                if zip_info.filename.endswith('.txt') and 'obj_train_data' in zip_info.filename:
                    # Lấy tên file nguyên bản (vd: obj_train_data/edge_test_123.txt -> edge_test_123.txt)
                    base_name = zip_info.filename.split('/')[-1]
                    
                    # Nếu tên file là frame_XXXXXX.txt thì mới cần map
                    if base_name.startswith('frame_'):
                        match = re.search(r'frame_(\d+)', base_name)
                        if match:
                            frame_id = int(match.group(1))
                            if frame_id < len(original_filenames):
                                final_name = original_filenames[frame_id].rsplit('.', 1)[0] + ".txt"
                                extracted_labels[final_name] = z.read(zip_info.filename).decode('utf-8')
                    else:
                        # Dùng luôn tên file gốc mà CVAT đã giữ lại
                        extracted_labels[base_name] = z.read(zip_info.filename).decode('utf-8')
        
        return extracted_labels

    def is_task_ready_for_export(self, task_id):
        """Kiểm tra job status."""
        endpoint = f"{self.url}/api/jobs"
        resp = requests.get(endpoint, params={"task_id": task_id}, auth=self.auth, headers=self.headers)
        if resp.status_code == 404:
            endpoint = f"{self.url}/api/tasks/{task_id}/jobs"
            resp = requests.get(endpoint, auth=self.auth, headers=self.headers)
            
        resp.raise_for_status()
        jobs = resp.json().get("results", [])
        if not jobs: return False
        return all(j.get("state") == "completed" for j in jobs)

    def _wait_for_task_status(self, task_id, timeout=60):
        start_time = time.time()
        endpoint = f"{self.url}/api/tasks/{task_id}"
        while time.time() - start_time < timeout:
            resp = requests.get(endpoint, auth=self.auth, headers=self.headers)
            if resp.json().get("status") in ["Completed", "Finished", "validation"]: return True
            time.sleep(2)
        return False
