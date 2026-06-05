import time
import requests
from urllib.parse import quote, urlparse, urlunparse

from ..config import (
    CVAT_URL,
    CVAT_USER,
    CVAT_PASS,
    CVAT_PROJECT_ID,
    CVAT_CLOUD_STORAGE_ID,
    CVAT_HOST_HEADER,
    CVAT_MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    BUCKET_RAW_DATA,
)


class CVATHandler:
    CVAT_API_ACCEPT = "application/vnd.cvat+json; version=2.0"

    def __init__(self):
        self.url = CVAT_URL.rstrip("/")
        self.auth = (CVAT_USER, CVAT_PASS)
        self.project_id = int(CVAT_PROJECT_ID)
        self.cloud_storage_id = int(CVAT_CLOUD_STORAGE_ID)

    def _headers(self, json_body=False):
        headers = {
            "Accept": self.CVAT_API_ACCEPT,
            "Host": CVAT_HOST_HEADER,
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(self, method, path, **kwargs):
        kwargs.setdefault("auth", self.auth)
        kwargs.setdefault("headers", self._headers(json_body=kwargs.get("json") is not None))
        kwargs.setdefault("timeout", 30)
        url = path if str(path).startswith("http") else f"{self.url}{path}"
        return requests.request(method, url, **kwargs)

    def _resolve_result_url(self, result_url: str) -> str:
        """CVAT trả result_url dạng http://127.0.0.1/api/... — map về CVAT_URL thực tế."""
        if not result_url:
            raise ValueError("empty result_url")

        if result_url.startswith("/"):
            return f"{self.url}{result_url}"

        parsed = urlparse(result_url)
        base = urlparse(self.url)
        return urlunparse((
            base.scheme,
            base.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))

    def ensure_cloud_storage(self):
        """Đồng bộ Cloud Storage CVAT với MinIO thật (endpoint + credential)."""
        expected_endpoint = CVAT_MINIO_ENDPOINT.rstrip("/")
        resp = self._request("GET", f"/api/cloudstorages/{self.cloud_storage_id}")
        resp.raise_for_status()
        storage = resp.json()

        attrs = storage.get("specific_attributes") or ""
        endpoint_ok = f"endpoint_url={quote(expected_endpoint, safe='')}" in attrs
        resource_ok = storage.get("resource") == BUCKET_RAW_DATA

        if endpoint_ok and resource_ok:
            return storage

        print(
            f"🔧 [CVAT] Updating cloud storage {self.cloud_storage_id} "
            f"→ bucket={BUCKET_RAW_DATA}, endpoint={expected_endpoint}"
        )
        payload = {
            "display_name": storage.get("display_name") or "MinIO raw-data",
            "provider_type": "AWS_S3_BUCKET",
            "resource": BUCKET_RAW_DATA,
            "credentials_type": "KEY_SECRET_KEY_PAIR",
            "key": MINIO_ACCESS_KEY,
            "secret_key": MINIO_SECRET_KEY,
            "specific_attributes": f"region=us-east-1&endpoint_url={quote(expected_endpoint, safe='')}",
        }
        patch = self._request(
            "PATCH",
            f"/api/cloudstorages/{self.cloud_storage_id}",
            json=payload,
        )
        patch.raise_for_status()
        return patch.json()

    def get_label_mapping(self):
        """Lấy danh sách label từ API labels."""
        resp = self._request(
            "GET",
            "/api/labels",
            params={"project_id": self.project_id},
        )
        resp.raise_for_status()

        results = resp.json().get("results", [])
        return {label["name"]: label["id"] for label in results}

    def create_task(self, name, filenames):
        """Tạo task mới từ danh sách file trên Cloud Storage."""
        self.ensure_cloud_storage()

        resp = self._request(
            "POST",
            "/api/tasks",
            json={"name": name, "project_id": self.project_id, "image_quality": 85},
        )
        resp.raise_for_status()
        task_id = resp.json()["id"]

        print(
            f"📦 [CVAT] Creating data for task {task_id} "
            f"using Cloud Storage ID: {self.cloud_storage_id}"
        )
        payload = {
            "image_quality": 85,
            "storage": "cloud_storage",
            "cloud_storage_id": self.cloud_storage_id,
            "server_files": filenames,
            "copy_data": False,
            "use_zip_chunks": True,
            "use_cache": True,
        }
        data_resp = self._request("POST", f"/api/tasks/{task_id}/data/", json=payload)
        if data_resp.status_code >= 400:
            print(f"❌ [CVAT ERROR] Status: {data_resp.status_code}")
            print(f"❌ [CVAT ERROR] Body: {data_resp.text}")
        data_resp.raise_for_status()

        self._wait_for_task_status(task_id)
        return task_id

    def upload_annotations(self, task_id, shapes):
        """Upload nhãn giả lên task."""
        self._request(
            "PUT",
            f"/api/tasks/{task_id}/annotations/",
            json={"shapes": shapes, "tracks": [], "tags": []},
        ).raise_for_status()

    def export_task_annotations(self, task_id, original_filenames):
        """Xuất nhãn từ CVAT, giải nén và đổi tên về nguyên bản."""
        import zipfile
        import io
        import re

        trigger_url = f"/api/tasks/{task_id}/dataset/export"
        params = {"format": "YOLO 1.1", "save_images": "false"}

        print(f"📦 [CVAT] Exporting annotations for Task {task_id}...")
        resp = self._request("POST", trigger_url, params=params, timeout=10)
        resp.raise_for_status()

        request_id = resp.json().get("id") or resp.json().get("rq_id")

        poll_url = f"/api/requests/{request_id}"
        download_url = None
        for _ in range(20):
            time.sleep(5)
            p_resp = self._request("GET", poll_url, timeout=10)
            status = p_resp.json().get("status")
            if status == "finished":
                raw_url = p_resp.json().get("result_url")
                if raw_url:
                    download_url = self._resolve_result_url(raw_url)
                break
        else:
            raise Exception("Export timeout")

        if not download_url:
            raise ValueError("CVAT export finished but result_url is missing")

        print(f"✨ [CVAT] Downloading and mapping labels from {download_url}...")
        d_resp = requests.get(
            download_url,
            auth=self.auth,
            headers=self._headers(),
            timeout=60,
        )
        d_resp.raise_for_status()

        extracted_labels = {}

        with zipfile.ZipFile(io.BytesIO(d_resp.content)) as z:
            for zip_info in z.infolist():
                if zip_info.filename.endswith(".txt") and "obj_train_data" in zip_info.filename:
                    base_name = zip_info.filename.split("/")[-1]

                    if base_name.startswith("frame_"):
                        match = re.search(r"frame_(\d+)", base_name)
                        if match:
                            frame_id = int(match.group(1))
                            if frame_id < len(original_filenames):
                                final_name = original_filenames[frame_id].rsplit(".", 1)[0] + ".txt"
                                extracted_labels[final_name] = z.read(zip_info.filename).decode("utf-8")
                    else:
                        extracted_labels[base_name] = z.read(zip_info.filename).decode("utf-8")

        return extracted_labels

    def get_task_export_status(self, task_id):
        """Trả về trạng thái export: worker chỉ export khi job/task đã hoàn thành trên CVAT."""
        task_resp = self._request("GET", f"/api/tasks/{task_id}")
        if task_resp.status_code == 404:
            return {"ready": False, "reason": "task not found on CVAT"}

        task = task_resp.json()
        task_status = (task.get("status") or "").lower()

        resp = self._request("GET", "/api/jobs", params={"task_id": task_id})
        if resp.status_code == 404:
            resp = self._request("GET", f"/api/tasks/{task_id}/jobs")

        jobs = []
        if resp.ok:
            payload = resp.json()
            jobs = payload.get("results", payload if isinstance(payload, list) else [])

        if not jobs:
            if task_status == "completed":
                return {"ready": True, "reason": "task status completed (no jobs list)"}
            return {"ready": False, "reason": "no jobs on CVAT", "task_status": task_status}

        job_states = [(j.get("state"), j.get("stage")) for j in jobs]
        jobs_completed = all((j.get("state") or "").lower() == "completed" for j in jobs)

        if jobs_completed or task_status == "completed":
            return {"ready": True, "reason": "completed", "jobs": job_states, "task_status": task_status}

        return {
            "ready": False,
            "reason": "job chưa Submit — trên CVAT bấm Menu → Submit annotations (Ctrl+Enter)",
            "jobs": job_states,
            "task_status": task_status,
        }

    def is_task_ready_for_export(self, task_id):
        return self.get_task_export_status(task_id)["ready"]

    def _wait_for_task_status(self, task_id, timeout=120):
        start_time = time.time()
        while time.time() - start_time < timeout:
            resp = self._request("GET", f"/api/tasks/{task_id}")
            if resp.json().get("status") in ["Completed", "Finished", "validation"]:
                return True
            time.sleep(2)
        return False
