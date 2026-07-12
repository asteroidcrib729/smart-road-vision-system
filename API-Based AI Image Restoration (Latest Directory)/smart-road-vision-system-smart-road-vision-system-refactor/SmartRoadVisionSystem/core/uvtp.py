import json
import os
import cv2
import time
from utils.storage import save_snapshot

class UVTPGate:
    def __init__(self, anpr_conf_thresh=0.85):
        self.anpr_conf_thresh = anpr_conf_thresh

    def evaluate(self, track_state):
        """
        Evaluates a finalized track state to determine if UVTP should activate.
        Returns True if the vehicle is deemed unidentifiable.
        """
        # Trigger conditions: Plate is missing, empty, or low confidence
        plate_text = track_state.get('plate_text')
        plate_conf = track_state.get('plate_conf', 0.0)

        if not plate_text or plate_text.strip() == "" or plate_conf < self.anpr_conf_thresh:
            return True
        return False

class EvidenceBuffer:
    def __init__(self):
        # track_id -> { 'best_area': 0, 'best_conf': 0, 'best_crop': None }
        self.buffers = {}

    def update(self, track_id, crop, bbox, conf):
        if crop is None or crop.size == 0:
            return

        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

        if track_id not in self.buffers:
            self.buffers[track_id] = {'best_area': area, 'best_conf': conf, 'best_crop': crop.copy()}
            return

        current_best = self.buffers[track_id]

        # Heuristic: Larger bounding box implies closer to camera -> better resolution
        if area > current_best['best_area'] and conf >= current_best['best_conf']:
            self.buffers[track_id] = {'best_area': area, 'best_conf': conf, 'best_crop': crop.copy()}

    def get_best_crop(self, track_id):
        return self.buffers.get(track_id, {}).get('best_crop', None)

    def clear(self, track_id):
        if track_id in self.buffers:
            del self.buffers[track_id]

class OutputDispatcher:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def dispatch(self, track_id, track_state, best_crop, is_uvtp):
        # 1. Save Snapshot Locally
        snapshot_path = None
        if best_crop is not None:
            snapshot_name = f"track_{track_id}_{int(time.time())}.jpg"
            if is_uvtp:
                snapshot_name = f"UVTP_{snapshot_name}"
            snapshot_path = os.path.join(self.output_dir, snapshot_name)
            cv2.imwrite(snapshot_path, best_crop)

        # 2. Package Metadata
        payload = {
            "track_id": track_id,
            "timestamp": time.time(),
            "vehicle_class": track_state.get('class_id'),
            "is_uvtp_alert": is_uvtp,
            "plate_text": track_state.get('plate_text'),
            "plate_conf": track_state.get('plate_conf'),
            "has_helmet": track_state.get('has_helmet'),
            "snapshot_path": snapshot_path
        }

        # 3. Save JSON Locally
        json_path = os.path.join(self.output_dir, f"event_{track_id}.json")
        with open(json_path, 'w') as f:
            json.dump(payload, f, indent=4)

        return payload
