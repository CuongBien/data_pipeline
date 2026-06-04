import pytest
import json
from unittest.mock import MagicMock
from pipeline.services.tracking_bridge import TrackingBridge

def test_tracking_bridge_initialization(monkeypatch):
    mock_client_module = MagicMock()
    monkeypatch.setattr("pipeline.services.tracking_bridge.mqtt_client", mock_client_module)
    
    bridge = TrackingBridge()
    assert bridge._tracker is not None
    assert bridge._sub is not None
    assert bridge._pub is not None

def test_tracking_bridge_on_message_valid(monkeypatch):
    mock_client_module = MagicMock()
    monkeypatch.setattr("pipeline.services.tracking_bridge.mqtt_client", mock_client_module)
    
    bridge = TrackingBridge()
    
    # Mock message
    msg = MagicMock()
    msg.payload.decode.return_value = json.dumps({
        "camera_id": "cam_1",
        "timestamp": 1234.5,
        "detections": [{"class": "car", "conf": 0.9, "bbox": [10, 10, 50, 50]}]
    })
    
    # Mock pub
    bridge._pub = MagicMock()
    
    # Call _on_message
    bridge._on_message(None, None, msg)
    
    # Verify pub was called
    bridge._pub.publish.assert_called_once()
    args, kwargs = bridge._pub.publish.call_args
    topic = args[0]
    payload = json.loads(args[1])
    
    assert "traffic/tracked" in topic
    assert payload["camera_id"] == "cam_1"
    assert len(payload["objects"]) == 1
    assert payload["objects"][0]["class_name"] == "car"

def test_tracking_bridge_on_message_invalid_json(monkeypatch):
    mock_client_module = MagicMock()
    monkeypatch.setattr("pipeline.services.tracking_bridge.mqtt_client", mock_client_module)
    
    bridge = TrackingBridge()
    
    # Mock message
    msg = MagicMock()
    msg.payload.decode.return_value = "invalid json"
    
    bridge._pub = MagicMock()
    
    # Call _on_message
    bridge._on_message(None, None, msg)
    
    # Verify pub was NOT called
    bridge._pub.publish.assert_not_called()
