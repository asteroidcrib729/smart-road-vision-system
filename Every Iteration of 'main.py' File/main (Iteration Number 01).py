import collections
import collections.abc

# --- MONKEY PATCH FOR PYTHON 3.10+ ---
# This fixes the "ImportError: cannot import name 'Mapping'" in FastReID
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping #type: ignore
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping #type: ignore
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable #type: ignore
# -------------------------------------

import cv2
import torch
import numpy as np
from ultralytics import YOLO #type: ignore
from datetime import datetime
import sys
import os

# --- IMPORTS ---
# Ensure we can import from the local module
sys.path.append(os.getcwd())

# 1. Standard UVTP imports
from uvtp import UVTPTrackerLoop, VehicleObservation, Detection, BoundingBox

# 2. Corrected Import Path for the Extractor
from uvtp.feature_extractor import FastReIDVehicleExtractor

# --- CONFIGURATION ---
# VIDEO_SOURCE = "test_video.mp4"  # Path to video or 0 for webcam
# YOLO_WEIGHTS = "checkpoints/yolov10_custom.pt" 
# REID_CONFIG = "fast-reid/configs/VERI/bagtricks_R50.yml"
# REID_WEIGHTS = "checkpoints/veri_resnet50.pth"

# --- DYNAMIC ABSOLUTE PATHS ---
# Get the folder where main.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEO_SOURCE = "test_video.mp4"
YOLO_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "yolov10_custom.pt")

# FastReID requires the path to be very specific to resolve the "_BASE_" include
# We will point deeper into the specific config
REID_CONFIG = os.path.join(BASE_DIR, "fast-reid", "configs", "VERI", "bagtricks_R50.yml")
REID_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "veri_resnet50.pth")

# Class IDs (Ensure these match your YOLO training data!)
CLASS_MAP = {
    0: "car",
    1: "bike",
    2: "license_plate" 
}
VEHICLE_CLASSES = ["car", "bike"]
PLATE_CLASSES = ["license_plate"]

def main():
    # --- CHECKS ---
    if not os.path.exists(YOLO_WEIGHTS):
        print(f"[ERROR] YOLO weights not found at: {YOLO_WEIGHTS}")
        return
    if not os.path.exists(REID_WEIGHTS):
        print(f"[ERROR] ReID weights not found at: {REID_WEIGHTS}")
        return

    # 1. Initialize Models
    print("[INFO] Loading YOLO...")
    model = YOLO(YOLO_WEIGHTS)
    
    print("[INFO] Loading Vehicle-ReID...")
    # NOTE: Ensure 'uvtp/feature_extractor.py' uses 'prev_embedding' 
    # and 'next_embedding' in arguments to match the Protocol!
    reid_extractor = FastReIDVehicleExtractor(
        config_file=REID_CONFIG,
        weights_path=REID_WEIGHTS,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )

    # 2. Initialize Tracker Loop
    tracker = UVTPTrackerLoop(
        camera_id="CAM-01",
        reid_matcher=reid_extractor, 
        evidence_root="./output/evidence"
    )

    # 3. Open Video Stream
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 4. Run YOLO Inference
        results = model(frame, verbose=False)[0]
        
        # 5. Parse Detections
        observations = []
        plates = []
        frame_h, frame_w = frame.shape[:2]

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            label = CLASS_MAP.get(cls_id, "unknown")
            bbox = BoundingBox(x1, y1, x2, y2)

            # --- PROCESS VEHICLES ---
            if label in VEHICLE_CLASSES:
                # Safe Cropping (Clip to frame boundaries)
                cx1, cy1 = max(0, int(x1)), max(0, int(y1))
                cx2, cy2 = min(frame_w, int(x2)), min(frame_h, int(y2))
                
                vehicle_crop = frame[cy1:cy2, cx1:cx2]

                # Extract Embedding (The "Brain")
                # Only process if crop is valid
                if vehicle_crop.size > 0 and vehicle_crop.shape[0] > 10 and vehicle_crop.shape[1] > 10:
                    embedding = reid_extractor.extract_embedding(vehicle_crop)
                    
                    # Create Observation
                    obs = VehicleObservation(
                        label=label,
                        bbox=bbox,
                        confidence=conf,
                        embedding=embedding,
                        frame_size=(frame_w, frame_h),
                        # Sharpness for "Best Shot" logic
                        sharpness_score=cv2.Laplacian(vehicle_crop, cv2.CV_64F).var(),
                        # Snapshot for evidence
                        snapshot_jpeg_bytes=cv2.imencode('.jpg', vehicle_crop)[1].tobytes()
                    )
                    observations.append(obs)

            # --- PROCESS PLATES ---
            elif label in PLATE_CLASSES:
                plates.append(Detection(
                    label=label,
                    bbox=bbox,
                    confidence=conf,
                    ocr_confidence=None 
                ))

        # 6. Step the Tracker
        events = tracker.process_frame(observations, plates)

        # 7. Visualization
        for track_id, track in tracker.active_tracks.items():
            # Color: Red for Ghost (No Plate), Green for OK
            color = (0, 0, 255) if track.state.is_ghost else (0, 255, 0)
            
            b = track.last_bbox
            cv2.rectangle(frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
            
            status = "GHOST" if track.state.is_ghost else "ID"
            caption = f"{track_id}|{status}"
            cv2.putText(frame, caption, (int(b.x1), int(b.y1)-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Alert for new Ghost Sessions
        for event in events:
            print(f"[ALERT] 🚨 Ghost Vehicle Detected: {event.event_id}")

        cv2.imshow("UVTP System", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    # 8. Cleanup
    print("[INFO] Finalizing Reports...")
    reports = tracker.flush_closed_sessions()
    print(f"[INFO] Generated {len(reports)} violation reports.")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()