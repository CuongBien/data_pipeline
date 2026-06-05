import os
import re
import requests

# Cấu hình cứng (bạn có thể thay đổi nếu cần)
CVAT_URL = "http://172.16.0.252:8080"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

NEW_USER = "django"
NEW_PASS = "Rmr2612+"

PROJECT_NAME = "Traffic Detection"
LABELS = [
    {"name": "Bus"},
    {"name": "Car"},
    {"name": "Motor"},
    {"name": "Truck"},
]

CLOUD_STORAGE_NAME = "minio_raw_data"
BUCKET_NAME = "raw-data"
MINIO_ENDPOINT = "http://172.16.0.252:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadminpassword"

ENV_FILE_PATH = r"d:\datas\Final.yolov8\.env"

def main():
    print(f"🚀 Bắt đầu cấu hình CVAT tại {CVAT_URL}...")
    
    # 1. Đăng nhập Admin
    session = requests.Session()
    session.headers.update({"Accept": "application/vnd.cvat+json; version=2.0"})
    
    login_resp = session.post(f"{CVAT_URL}/api/auth/login", json={
        "username": ADMIN_USER,
        "password": ADMIN_PASS
    })
    
    if login_resp.status_code >= 400:
        print(f"❌ Không thể đăng nhập bằng {ADMIN_USER}:{ADMIN_PASS}. Vui lòng kiểm tra lại tài khoản hoặc CVAT chưa chạy.")
        return
        
    print(f"✅ Đăng nhập Admin thành công.")

    # 1.5 Cấp CSRF token cho các request POST tiếp theo nếu có (CVAT dùng Token auth or Session)
    # Tốt nhất là dùng Token lấy được:
    token = login_resp.json().get("key")
    if token:
        session.headers.update({"Authorization": f"Token {token}"})

    # 2. Tạo User django
    print(f"⏳ Đang kiểm tra/tạo user '{NEW_USER}'...")
    users_resp = session.get(f"{CVAT_URL}/api/users", params={"search": NEW_USER})
    users_resp.raise_for_status()
    users = users_resp.json().get("results", [])
    
    if any(u["username"] == NEW_USER for u in users):
        print(f"✅ User '{NEW_USER}' đã tồn tại.")
    else:
        create_user_resp = session.post(f"{CVAT_URL}/api/users", json={
            "username": NEW_USER,
            "password": NEW_PASS,
            "email": "django@local.com",
            "first_name": "Service",
            "last_name": "Account"
        })
        if create_user_resp.status_code == 201:
            print(f"✅ Tạo thành công user '{NEW_USER}'.")
            # Cấp quyền admin/superuser nếu cần (CVAT API v2: PATCH /api/users/{id} groups)
            user_id = create_user_resp.json()["id"]
            # Lấy list groups (thường admin group là role: admin)
            session.patch(f"{CVAT_URL}/api/users/{user_id}", json={"is_superuser": True})
        else:
            print(f"⚠️ Không thể tạo user (hoặc đã tồn tại): {create_user_resp.text}")

    # 3. Tạo Project
    print(f"⏳ Đang kiểm tra/tạo Project '{PROJECT_NAME}'...")
    proj_resp = session.get(f"{CVAT_URL}/api/projects", params={"search": PROJECT_NAME})
    proj_resp.raise_for_status()
    projects = proj_resp.json().get("results", [])
    
    project_id = None
    for p in projects:
        if p["name"] == PROJECT_NAME:
            project_id = p["id"]
            print(f"✅ Project '{PROJECT_NAME}' đã tồn tại (ID: {project_id}).")
            break
            
    if not project_id:
        create_proj_resp = session.post(f"{CVAT_URL}/api/projects", json={
            "name": PROJECT_NAME,
            "labels": LABELS
        })
        if create_proj_resp.status_code == 201:
            project_id = create_proj_resp.json()["id"]
            print(f"✅ Tạo thành công Project '{PROJECT_NAME}' (ID: {project_id}).")
        else:
            print(f"❌ Lỗi tạo Project: {create_proj_resp.text}")
            return

    # 4. Tạo Cloud Storage
    print(f"⏳ Đang kiểm tra/tạo Cloud Storage '{CLOUD_STORAGE_NAME}'...")
    cs_resp = session.get(f"{CVAT_URL}/api/cloudstorages", params={"search": CLOUD_STORAGE_NAME})
    cs_resp.raise_for_status()
    storages = cs_resp.json().get("results", [])
    
    storage_id = None
    for s in storages:
        if s["display_name"] == CLOUD_STORAGE_NAME:
            storage_id = s["id"]
            print(f"✅ Cloud Storage '{CLOUD_STORAGE_NAME}' đã tồn tại (ID: {storage_id}).")
            break
            
    if not storage_id:
        # Trong CVAT API, khi POST provider S3 với region US-East-1 và custom endpoint
        payload = {
            "display_name": CLOUD_STORAGE_NAME,
            "provider_type": "AWS_S3_BUCKET",
            "resource": BUCKET_NAME,
            "credentials_type": "KEY_SECRET_KEY_PAIR",
            "key": MINIO_ACCESS_KEY,
            "secret_key": MINIO_SECRET_KEY,
            "specific_attributes": f"region=us-east-1&endpoint_url={MINIO_ENDPOINT}"
        }
        create_cs_resp = session.post(f"{CVAT_URL}/api/cloudstorages", json=payload)
        if create_cs_resp.status_code == 201:
            storage_id = create_cs_resp.json()["id"]
            print(f"✅ Tạo thành công Cloud Storage '{CLOUD_STORAGE_NAME}' (ID: {storage_id}).")
        else:
            print(f"❌ Lỗi tạo Cloud Storage: {create_cs_resp.text}")
            return

    # 5. Cập nhật file .env
    print(f"⏳ Đang cập nhật {ENV_FILE_PATH}...")
    if not os.path.exists(ENV_FILE_PATH):
        print(f"❌ Không tìm thấy file {ENV_FILE_PATH}")
        return

    with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
        env_content = f.read()

    # Regex thay thế hoặc thêm mới
    if re.search(r"^CVAT_PROJECT_ID=.*$", env_content, re.MULTILINE):
        env_content = re.sub(r"^CVAT_PROJECT_ID=.*$", f"CVAT_PROJECT_ID={project_id}", env_content, flags=re.MULTILINE)
    else:
        env_content += f"\nCVAT_PROJECT_ID={project_id}\n"

    if re.search(r"^CVAT_CLOUD_STORAGE_ID=.*$", env_content, re.MULTILINE):
        env_content = re.sub(r"^CVAT_CLOUD_STORAGE_ID=.*$", f"CVAT_CLOUD_STORAGE_ID={storage_id}", env_content, flags=re.MULTILINE)
    else:
        env_content += f"CVAT_CLOUD_STORAGE_ID={storage_id}\n"

    with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print("🎉 Hoàn tất! File .env đã được cập nhật.")

if __name__ == "__main__":
    main()
