import requests

def cleanup():
    auth = ('django', 'Rmr2612+')
    base = 'http://cvat-server:8080/api/'
    
    # 1. Delete all tasks
    print("🗑️ Deleting all tasks...")
    while True:
        resp = requests.get(base + 'tasks', auth=auth).json()
        tasks = resp.get('results', [])
        if not tasks:
            break
        for t in tasks:
            tid = t['id']
            r = requests.delete(f"{base}tasks/{tid}", auth=auth)
            if r.status_code == 204:
                print(f"  ✅ Deleted Task {tid}")
            else:
                print(f"  ❌ Failed to delete Task {tid}: {r.status_code} {r.text}")
                # Nếu không xóa được thì thoát để tránh lặp vô hạn
                return
            
    # 2. Delete all cloud storages
    print("🗑️ Deleting all cloud storages...")
    while True:
        resp = requests.get(base + 'cloudstorages', auth=auth).json()
        storages = resp.get('results', [])
        if not storages:
            break
        for s in storages:
            sid = s['id']
            r = requests.delete(f"{base}cloudstorages/{sid}", auth=auth)
            if r.status_code == 204:
                print(f"  ✅ Deleted Storage {sid}")
            else:
                print(f"  ❌ Failed to delete Storage {sid}: {r.status_code} {r.text}")
                return

if __name__ == "__main__":
    cleanup()
