"""
IoU Tracker — assigns persistent tracking IDs per camera feed.
Greedy IoU matching (no Kalman). PerCameraTracker manages one IouTracker per camera_id.
"""

import numpy as np

CLASS_NAME_TO_ID: dict[str, int] = {
    "car": 0,
    "motor": 1,
    "bus": 2,
    "truck": 3,
}


def _iou(a: list, b: list) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, (a[2] - a[0]) * (a[3] - a[1]))
    area_b = max(0.0, (b[2] - b[0]) * (b[3] - b[1]))
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _xywh_to_xyxy(bbox: list) -> list:
    x, y, w, h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    return [x, y, x + w, y + h]


class _Track:
    __slots__ = ("track_id", "bbox", "class_name", "class_id", "confidence", "missed")

    def __init__(self, track_id, bbox, class_name, class_id, confidence):
        self.track_id = track_id
        self.bbox = bbox
        self.class_name = class_name
        self.class_id = class_id
        self.confidence = confidence
        self.missed = 0


def _to_dict(t: _Track) -> dict:
    return {
        "tracking_id": t.track_id,
        "class_name": t.class_name,
        "class_id": t.class_id,
        "confidence": round(t.confidence, 4),
        "bbox": [round(v, 2) for v in t.bbox],
    }


class IouTracker:
    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 5):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self._tracks: list[_Track] = []
        self._next_id: int = 1

    def update(self, detections: list[dict], timestamp: float) -> list[dict]:
        # Normalize + filter
        norm = []
        for det in detections:
            class_name = str(det.get("class", "unknown"))
            class_id = CLASS_NAME_TO_ID.get(class_name)
            if class_id is None:
                print(f"[IOU_TRACKER] Unknown class '{class_name}', skipping")
                continue
            try:
                bbox_xyxy = _xywh_to_xyxy(det["bbox"])
            except Exception as e:
                print(f"[IOU_TRACKER] Bad bbox {det.get('bbox')}: {e}, skipping")
                continue
            norm.append(
                {
                    "class_name": class_name,
                    "class_id": class_id,
                    "confidence": float(det.get("conf", 0.0)),
                    "bbox": bbox_xyxy,
                }
            )

        # Age all tracks
        for t in self._tracks:
            t.missed += 1

        if not norm:
            self._tracks = [t for t in self._tracks if t.missed <= self.max_missed]
            return []

        results = []

        if not self._tracks:
            for d in norm:
                t = _Track(
                    self._next_id,
                    d["bbox"],
                    d["class_name"],
                    d["class_id"],
                    d["confidence"],
                )
                self._next_id += 1
                self._tracks.append(t)
                results.append(_to_dict(t))
            return results

        n_t, n_d = len(self._tracks), len(norm)
        iou_mat = np.zeros((n_t, n_d), dtype=np.float32)
        for i, track in enumerate(self._tracks):
            for j, d in enumerate(norm):
                iou_mat[i, j] = _iou(track.bbox, d["bbox"])

        matched_t: set[int] = set()
        matched_d: set[int] = set()
        for idx in np.argsort(-iou_mat, axis=None):
            i, j = divmod(int(idx), n_d)
            if iou_mat[i, j] < self.iou_threshold:
                break
            if i in matched_t or j in matched_d:
                continue
            self._tracks[i].bbox = norm[j]["bbox"]
            self._tracks[i].confidence = norm[j]["confidence"]
            self._tracks[i].missed = 0
            matched_t.add(i)
            matched_d.add(j)

        for i in matched_t:
            results.append(_to_dict(self._tracks[i]))

        for j, d in enumerate(norm):
            if j not in matched_d:
                t = _Track(
                    self._next_id,
                    d["bbox"],
                    d["class_name"],
                    d["class_id"],
                    d["confidence"],
                )
                self._next_id += 1
                self._tracks.append(t)
                results.append(_to_dict(t))

        self._tracks = [t for t in self._tracks if t.missed <= self.max_missed]
        return results


class PerCameraTracker:
    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 5):
        self._iou_threshold = iou_threshold
        self._max_missed = max_missed
        self._cameras: dict[str, IouTracker] = {}

    def update(
        self, camera_id: str, detections: list[dict], timestamp: float
    ) -> list[dict]:
        if camera_id not in self._cameras:
            self._cameras[camera_id] = IouTracker(self._iou_threshold, self._max_missed)
            print(f"[PER_CAMERA_TRACKER] New tracker for '{camera_id}'")
        return self._cameras[camera_id].update(detections, timestamp)
