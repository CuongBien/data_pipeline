-- Khởi tạo bảng detections với schema mới
CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY,
    camera_id VARCHAR(50) NOT NULL,
    image_url TEXT NOT NULL,
    "timestamp" TIMESTAMP NOT NULL,
    trigger_reason TEXT,
    status VARCHAR(20) DEFAULT 'NEW',
    cvat_task_id INTEGER,
    edge_predictions JSONB
);

-- Index để tìm kiếm theo trạng thái nhanh hơn
CREATE INDEX IF NOT EXISTS idx_detections_status ON detections(status);
