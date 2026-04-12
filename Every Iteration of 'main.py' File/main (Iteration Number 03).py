import cv2
import torch
import numpy as np
import collections
import collections.abc
import sys
import os

# --- MONKEY PATCH FOR COMPATIBILITY ---
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping # type: ignore
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping # type: ignore
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable # type: ignore

# Ensure we can import from the local module
sys.path.append(os.getcwd())

from ultralytics import YOLO # type: ignore
from uvtp import UVTPTrackerLoop, VehicleObservation, Detection, BoundingBox, UVTPConfig
from uvtp.feature_extractor import FastReIDVehicleExtractor

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_SOURCE = "test_video.mp4" 
YOLO_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "yolov10_custom.pt")
REID_CONFIG = os.path.join(BASE_DIR, "fast-reid", "configs", "VERI", "bagtricks_R50.yml")
REID_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "veri_resnet50.pth")

# Mapping COCO Classes (2=Car, 3=Motorcycle, 5=Bus, 7=Truck)
CLASS_MAP = { 1: "bike", 2: "car", 3: "bike", 5: "bus", 7: "truck" }
VEHICLE_CLASSES = ["car", "bike", "bus", "truck"]
PLATE_CLASSES = ["license_plate"]

def main():
    # 1. Initialize Models
    print("[INFO] Loading YOLO...")
    model = YOLO(YOLO_WEIGHTS)
    
    print("[INFO] Loading Vehicle-ReID...")
    reid_extractor = FastReIDVehicleExtractor(
        config_file=REID_CONFIG,
        weights_path=REID_WEIGHTS,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )

    # 2. CONFIGURE TRACKER
    # FIX: We increase 'max_age' (lost frames) specifically to help bikes stay alive
    # even if YOLO misses them for 0.5 seconds.
    config = UVTPConfig(
        reid_cosine_match_threshold=0.60, # Moderate strictness
        ghost_min_consecutive_no_plate_frames=5
    )

    tracker = UVTPTrackerLoop(
        camera_id="CAM-01",
        reid_matcher=reid_extractor,
        config=config, 
        evidence_root="./output/evidence",
        # CRITICAL FIX: Keep "lost" vehicles in memory for 10 frames (approx 0.5s)
        # This prevents the ID from resetting just because the bike flickered.
        session_close_after_lost_frames=10 
    )

    cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    # PROCESSING SETTINGS
    TARGET_WIDTH = 1024 
    FRAME_SKIP = 2
    frame_count = 0

    print("[INFO] Starting Stream...")
    
    while cap.isOpened():
        ret, raw_frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue

        # Resize
        h, w = raw_frame.shape[:2]
        scale = TARGET_WIDTH / w
        new_h = int(h * scale)
        frame = cv2.resize(raw_frame, (TARGET_WIDTH, new_h))
        frame_h, frame_w = frame.shape[:2]
        
        # --- ROI DEFINITION ---
        # We only want to track vehicles in the "Active Zone" (Middle 60%)
        zone_top = frame_h * 0.15     # Ignore top 15%
        zone_bottom = frame_h * 0.85  # Ignore bottom 15%

        # Draw ROI Lines for debugging (Visual Aid)
        cv2.line(frame, (0, int(zone_top)), (frame_w, int(zone_top)), (255, 0, 0), 1)
        cv2.line(frame, (0, int(zone_bottom)), (frame_w, int(zone_bottom)), (255, 0, 0), 1)

        # 4. YOLO Inference
        # FIX: Lower confidence to 0.25 to ensure we catch every bike
        results = model(frame, verbose=False, conf=0.25)[0] 
        
        observations = []
        plates = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            label = CLASS_MAP.get(cls_id, None)
            if not label: continue

            bbox = BoundingBox(x1, y1, x2, y2)
            
            # --- ROI FILTER LOGIC ---
            # If the center of the box is outside the zone, skip it.
            box_cy = (y1 + y2) / 2
            if box_cy < zone_top or box_cy > zone_bottom:
                continue

            if label in VEHICLE_CLASSES:
                # Clip crop
                cx1, cy1 = max(0, int(x1)), max(0, int(y1))
                cx2, cy2 = min(frame_w, int(x2)), min(frame_h, int(y2))
                vehicle_crop = frame[cy1:cy2, cx1:cx2]
                
                # FIX: "Bike Booster" - Accept smaller/blurrier crops for bikes
                min_size = 5 if label == "bike" else 15

                if vehicle_crop.size > 0 and vehicle_crop.shape[0] > min_size and vehicle_crop.shape[1] > min_size:
                    embedding = reid_extractor.extract_embedding(vehicle_crop)
                    
                    obs = VehicleObservation(
                        label=label,
                        bbox=bbox,
                        confidence=conf,
                        embedding=embedding,
                        frame_size=(frame_w, frame_h),
                        snapshot_jpeg_bytes=None
                    )
                    observations.append(obs)

        # 6. Step Tracker
        events = tracker.process_frame(observations, plates)

        # 7. Visualization
        for track_id, track in tracker.active_tracks.items():
            # Filter: Only draw active tracks inside the zone
            if (tracker.frame_index - track.last_seen_frame) > 2:
                 continue # Don't draw "stale" boxes

            # Color Logic: RED = Ghost (No Plate), GREEN = Safe/New
            color = (0, 0, 255) if track.state.is_ghost else (0, 255, 0)
            
            b = track.last_bbox
            cv2.rectangle(frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
            
            # Label
            text = f"{track_id}"
            cv2.putText(frame, text, (int(b.x1), int(b.y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("UVTP Final Optimized", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    tracker.flush_closed_sessions()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()