import pytest
import json
from unittest.mock import MagicMock
from pipeline.utils.mqtt_handler import MQTTHandler
from pipeline.utils.minio_handler import MinioHandler

def test_mqtt_handler_initialization(mock_db_handler, monkeypatch):
    mock_client_module = MagicMock()
    monkeypatch.setattr("pipeline.utils.mqtt_handler.mqtt_client", mock_client_module)
    
    handler = MQTTHandler(mock_db_handler)
    assert handler.db_handler == mock_db_handler
    mock_client_module.Client.assert_called_once()

def test_mqtt_handler_on_message_valid(mock_db_handler, monkeypatch):
    mock_client_module = MagicMock()
    monkeypatch.setattr("pipeline.utils.mqtt_handler.mqtt_client", mock_client_module)
    
    handler = MQTTHandler(mock_db_handler)
    
    # Mock message
    msg = MagicMock()
    msg.topic = "test/topic"
    payload = {
        "camera_id": "cam_01",
        "image_url": "http://example.com/img.jpg",
        "timestamp": 123456789.0,
        "trigger_reason": "motion",
        "detections": [{"class": "car", "bbox": [0,0,10,10]}]
    }
    msg.payload.decode.return_value = json.dumps(payload)
    
    # Mock db_handler insert_with_retry
    mock_db_handler.insert_with_retry = MagicMock()
    
    handler._on_message(None, None, msg)
    
    mock_db_handler.insert_with_retry.assert_called_once()
    called_payload = mock_db_handler.insert_with_retry.call_args[0][0]
    
    assert called_payload["camera_id"] == "cam_01"
    assert len(called_payload["edge_predictions"]) == 1

def test_minio_handler_list_objects(monkeypatch):
    mock_minio = MagicMock()
    monkeypatch.setattr("pipeline.utils.minio_handler.Minio", mock_minio)
    
    handler = MinioHandler()
    
    mock_obj1 = MagicMock()
    mock_obj1.object_name = "file1.jpg"
    mock_obj2 = MagicMock()
    mock_obj2.object_name = "file2.jpg"
    
    handler.client.list_objects.return_value = [mock_obj1, mock_obj2]
    
    objects = handler.list_objects("test-bucket")
    
    assert len(objects) == 2
    assert "file1.jpg" in objects

def test_minio_handler_download_file_as_str(monkeypatch):
    mock_minio = MagicMock()
    monkeypatch.setattr("pipeline.utils.minio_handler.Minio", mock_minio)
    
    handler = MinioHandler()
    
    mock_response = MagicMock()
    mock_response.read.return_value = b'test content'
    handler.client.get_object.return_value = mock_response
    
    content = handler.download_file_as_str("bucket", "file.txt")
    
    assert content == "test content"
    mock_response.close.assert_called_once()
    mock_response.release_conn.assert_called_once()
