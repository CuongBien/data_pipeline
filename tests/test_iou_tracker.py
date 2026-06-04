import pytest
from pipeline.utils.iou_tracker import IouTracker, PerCameraTracker

def test_iou_tracker_initialization():
    tracker = IouTracker(iou_threshold=0.4, max_missed=3)
    assert tracker.iou_threshold == 0.4
    assert tracker.max_missed == 3
    assert len(tracker._tracks) == 0

def test_iou_tracker_update_valid_boxes():
    tracker = IouTracker(iou_threshold=0.3, max_missed=5)
    
    # Simulate valid detection
    detections = [
        {
            "class": "car",
            "conf": 0.9,
            "bbox": [100, 100, 200, 200]
        }
    ]
    
    results = tracker.update(detections, timestamp=1.0)
    
    assert len(results) == 1
    assert results[0]["tracking_id"] == 1
    assert results[0]["class_name"] == "car"
    assert results[0]["class_id"] == 0
    assert results[0]["bbox"] == [100.0, 100.0, 200.0, 200.0]

def test_iou_tracker_update_invalid_class():
    tracker = IouTracker()
    
    detections = [
        {
            "class": "alien", # Unknown class
            "conf": 0.9,
            "bbox": [100, 100, 200, 200]
        }
    ]
    
    results = tracker.update(detections, timestamp=1.0)
    assert len(results) == 0

def test_iou_tracker_update_invalid_bbox():
    tracker = IouTracker()
    
    detections = [
        {
            "class": "car",
            "conf": 0.9,
            "bbox": [100, 100, 200] # Only 3 coordinates
        }
    ]
    
    results = tracker.update(detections, timestamp=1.0)
    assert len(results) == 0

def test_per_camera_tracker():
    tracker = PerCameraTracker()
    
    # Update camera 1
    det1 = [{"class": "car", "conf": 0.8, "bbox": [10, 10, 50, 50]}]
    res1 = tracker.update("cam_1", det1, timestamp=1.0)
    
    # Update camera 2
    det2 = [{"class": "bus", "conf": 0.9, "bbox": [100, 100, 300, 300]}]
    res2 = tracker.update("cam_2", det2, timestamp=1.0)
    
    assert len(res1) == 1
    assert len(res2) == 1
    assert "cam_1" in tracker._cameras
    assert "cam_2" in tracker._cameras
