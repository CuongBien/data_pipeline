import requests

# Thay đổi bằng User/Pass của bạn
AUTH = ("django", "Rmr2612+")
BASE_URLS = [
    "http://cvat_server:8080",
    "http://cvat_server:8000",
]
ENDPOINTS = [
    "/api/projects/1/",
    "/api/v1/projects/1/",
    "/api/labels/",
]

print("🔍 Starting CVAT API Discovery...")
for base in BASE_URLS:
    for ep in ENDPOINTS:
        url = f"{base}{ep}"
        try:
            print(f"Testing: {url} ...", end=" ")
            resp = requests.get(url, auth=AUTH, timeout=3)
            print(f"Result: {resp.status_code}")
            if resp.status_code == 200:
                print(f"✨ FOUND WORKING ENDPOINT: {url}")
        except Exception as e:
            print(f"FAILED: {e}")

print("🏁 Discovery finished.")
