import requests
import sys
import os

# Thêm đường dẫn để import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from pipeline.config import CVAT_URL, CVAT_USER, CVAT_PASS

def discovery():
    auth = (CVAT_USER, CVAT_PASS)
    headers = {"Host": "localhost"}
    base_url = CVAT_URL.rstrip('/')
    
    print(f"🔍 Testing connection to: {base_url}")
    
    endpoints = [
        "/api/server/about",
        "/api/projects",
        "/api/tasks",
        "/api/labels",
        "/api/cloudstorages"
    ]
    
    for ep in endpoints:
        url = f"{base_url}{ep}"
        try:
            resp = requests.get(url, auth=auth, headers=headers, timeout=5)
            print(f"--- {ep} ---")
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if ep == "/api/projects":
                    projects = data.get('results', [])
                    print(f"Projects found: {[ (p['id'], p['name']) for p in projects ]}")
                else:
                    print(f"Response: {str(data)[:200]}...")
            else:
                print(f"Error: {resp.text[:100]}")
        except Exception as e:
            print(f"❌ Failed to reach {url}: {e}")

if __name__ == "__main__":
    discovery()
