import time
import json
import psycopg2
from typing import TypedDict, List, Optional
from ..config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_TABLE,
    DB_RETRY_MAX_ATTEMPTS, DB_RETRY_BASE_SECONDS
)

class DetectionRecord(TypedDict):
    id: int
    camera_id: str
    image_url: str
    timestamp: any
    trigger_reason: str
    status: str
    cvat_task_id: Optional[int]
    edge_predictions: Optional[dict]

class DBHandler:
    def __init__(self):
        self.connection = None

    def connect(self):
        print(f"[DB] Connecting to {DB_NAME} at {DB_HOST}:{DB_PORT}...")
        try:
            self.connection = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            self.connection.autocommit = True
            print("[DB] Connected.")
        except Exception as exc:
            raise ConnectionError(f"Failed to connect PostgreSQL: {exc}") from exc

    def get_records_by_status(self, status: str, limit=10) -> List[DetectionRecord]:
        """Lấy các bản ghi theo trạng thái."""
        sql = f"SELECT * FROM {DB_TABLE} WHERE status = %s ORDER BY timestamp ASC LIMIT %s"
        try:
            if not self.connection or self.connection.closed: self.connect()
            with self.connection.cursor() as cur:
                cur.execute(sql, (status, limit))
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"[DB] Error fetching records by status {status}: {e}")
            return []

    def get_new_records(self, limit=10) -> List[DetectionRecord]:
        """Lấy các bản ghi mới (Tương thích ngược)."""
        return self.get_records_by_status('NEW', limit)

    def update_status(self, record_ids: List[int], new_status: str, cvat_task_id: Optional[int] = None):
        """Cập nhật trạng thái và cvat_task_id cho danh sách bản ghi."""
        if not record_ids: return
        
        if cvat_task_id:
            sql = f"UPDATE {DB_TABLE} SET status = %s, cvat_task_id = %s WHERE id IN %s"
            params = (new_status, cvat_task_id, tuple(record_ids))
        else:
            sql = f"UPDATE {DB_TABLE} SET status = %s WHERE id IN %s"
            params = (new_status, tuple(record_ids))
            
        try:
            if not self.connection or self.connection.closed: self.connect()
            with self.connection.cursor() as cur:
                cur.execute(sql, params)
        except Exception as e:
            print(f"[DB] Error updating status: {e}")

    def get_active_cvat_tasks(self):
        """Lấy danh sách các task_id đang ở trạng thái IN_CVAT."""
        sql = f"SELECT DISTINCT cvat_task_id FROM {DB_TABLE} WHERE status = 'IN_CVAT' AND cvat_task_id IS NOT NULL"
        try:
            if not self.connection or self.connection.closed: self.connect()
            with self.connection.cursor() as cur:
                cur.execute(sql)
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"[DB] Error fetching active tasks: {e}")
            return []

    def update_status_by_task(self, cvat_task_id, status):
        """Cập nhật trạng thái cho tất cả bản ghi thuộc 1 task."""
        sql = f"UPDATE {DB_TABLE} SET status = %s WHERE cvat_task_id = %s"
        try:
            if not self.connection or self.connection.closed: self.connect()
            with self.connection.cursor() as cur:
                cur.execute(sql, (status, cvat_task_id))
        except Exception as e:
            print(f"[DB] Error updating status by task: {e}")

    def get_task_filenames(self, task_id):
        """Lấy danh sách tên file gốc của một task theo đúng thứ tự (để map với frame_id)."""
        sql = f"SELECT image_url FROM {DB_TABLE} WHERE cvat_task_id = %s ORDER BY id ASC"
        try:
            if not self.connection or self.connection.closed: self.connect()
            with self.connection.cursor() as cur:
                cur.execute(sql, (task_id,))
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"❌ [DB] Error getting filenames for task {task_id}: {e}")
            return []

    def insert_record(self, data: dict):
        """Thêm bản ghi mới từ MQTT (Kèm nhãn từ Jetson)."""
        sql = f"""
            INSERT INTO {DB_TABLE} (camera_id, image_url, timestamp, trigger_reason, status, edge_predictions)
            VALUES (%s, %s, TO_TIMESTAMP(%s), %s, 'NEW', %s)
        """
        params = (
            data["camera_id"],
            data["image_url"],
            data["timestamp"],
            data["trigger_reason"],
            json.dumps(data["edge_predictions"])
        )
        try:
            if not self.connection or self.connection.closed: self.connect()
            with self.connection.cursor() as cur:
                cur.execute(sql, params)
        except Exception as e:
            print(f"[DB] Error inserting record: {e}")
            raise e

    def insert_with_retry(self, data: dict):
        """Thêm bản ghi với cơ chế retry."""
        for attempt in range(DB_RETRY_MAX_ATTEMPTS):
            try:
                self.insert_record(data)
                return
            except Exception as e:
                print(f"[DB] Insert attempt {attempt+1} failed: {e}")
                time.sleep(DB_RETRY_BASE_SECONDS * (attempt + 1))
        raise Exception("Failed to insert record after multiple attempts")
