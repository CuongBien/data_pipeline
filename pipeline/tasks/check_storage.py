import requests
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pipeline.config import CVAT_URL, CVAT_USER, CVAT_PASS

def check_storage():
    auth = (CVAT_USER, CVAT_PASS)
    headers = {"Host": "localhost"}
    storage_id = 1
    
    print(f"🔍 Checking Cloud Storage {storage_id}...")
    url = f"{CVAT_URL}/api/cloudstorages/{storage_id}/content"
    
    try:
        resp = requests.get(url, auth=auth, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            content = resp.json()
            print(f"Files found in storage: {content[:10]}...")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_storage()
