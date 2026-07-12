import cv2
import torch
import numpy as np
import collections
import collections.abc
import sys
import os

# --- MONKEY PATCH (Keep this) ---
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
# DYNAMIC PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_SOURCE = "test_video.mp4" 
YOLO_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "yolov10_custom.pt")
REID_CONFIG = os.path.join(BASE_DIR, "fast-reid", "configs", "VERI", "bagtricks_R50.yml") # Check path!
REID_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "veri_resnet50.pth")

# NEW (Updated)
# We map both 'bicycle' (1) and 'motorcycle' (3) to the concept of a "bike"
CLASS_MAP = { 1: "bike", 2: "car", 3: "bike", 5: "bus", 7: "truck" }
VEHICLE_CLASSES = ["car", "bike", "bus", "truck"]
PLATE_CLASSES = ["license_plate"] # Won't be found by standard YOLO, that's expected for now.

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

    # 2. CONFIGURE TRACKER (The Tuning Fix)
    config = UVTPConfig(
        # Increase to 0.65. This says: "Even if it's only 35% similar, it's the SAME car."
        # This prevents the "New ID" creation.
        reid_cosine_match_threshold=0.65,  
        
        # Trigger the "Ghost" alert faster (after 5 frames instead of 10)
        ghost_min_consecutive_no_plate_frames=5
    )

    tracker = UVTPTrackerLoop(
        camera_id="CAM-01",
        reid_matcher=reid_extractor,
        config=config, 
        evidence_root="./output/evidence",
        # CRITICAL: If we don't see the car for 2 frames, DELETE IT.
        # This stops the "Floating Box" effect immediately.
        session_close_after_lost_frames=2  
    )

    # 3. Open Video
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    # PROCESSING SETTINGS
    TARGET_WIDTH = 1024  # Resize big videos to this width
    FRAME_SKIP = 2       # Process every Nth frame (Speed up)
    frame_count = 0

    print("[INFO] Starting Stream...")
    
    while cap.isOpened():
        ret, raw_frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue

        # Resize for speed
        h, w = raw_frame.shape[:2]
        scale = TARGET_WIDTH / w
        new_h = int(h * scale)
        frame = cv2.resize(raw_frame, (TARGET_WIDTH, new_h))
        frame_h, frame_w = frame.shape[:2]

        # 4. YOLO Inference
        results = model(frame, verbose=False, conf=0.3)[0] # Confidence 0.5 to reduce noise
        
        observations = []
        plates = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            label = CLASS_MAP.get(cls_id, None)
            if not label: continue # Skip non-vehicles

            bbox = BoundingBox(x1, y1, x2, y2)

            if label in VEHICLE_CLASSES:
                # Clip crop
                cx1, cy1 = max(0, int(x1)), max(0, int(y1))
                cx2, cy2 = min(frame_w, int(x2)), min(frame_h, int(y2))
                vehicle_crop = frame[cy1:cy2, cx1:cx2]

                # --- BIKE BOOSTER LOGIC ---
                # Bikes are small. We must accept smaller crops for them.
                min_size = 10  # Default for cars
                if label == "bike":
                    min_size = 5 # Allow smaller bike crops

                if vehicle_crop.size > 0 and vehicle_crop.shape[0] > min_size and vehicle_crop.shape[1] > min_size:
                    embedding = reid_extractor.extract_embedding(vehicle_crop)
                    
                    # --- ROI FILTER (NEW) ---
                    # Calculate the center Y-coordinate of the box
                    box_cy = (bbox.y1 + bbox.y2) / 2

                    # Define the "Active Zone" (Middle 60% of the frame)
                    # We ignore the top 20% (Entry) and bottom 20% (Exit)
                    zone_top = frame_h * 0.20
                    zone_bottom = frame_h * 0.80

                    # If the vehicle is too high (entering) or too low (leaving), SKIP IT.
                    if box_cy < zone_top or box_cy > zone_bottom:
                        continue 
                    # ------------------------

                    # ... (Only then do we append to observations) ...
                    obs = VehicleObservation(
                        label=label,
                        bbox=bbox,
                        confidence=conf,
                        embedding=embedding,
                        frame_size=(frame_w, frame_h),
                        snapshot_jpeg_bytes=None # Disable JPG encoding for speed during test
                    )
                    observations.append(obs)

        # 6. Step Tracker
        events = tracker.process_frame(observations, plates)

        # 7. Visualization (Strict Filter)
        for track_id, track in tracker.active_tracks.items():
            # FILTER 1: Skip "stale" tracks. 
            # If the track wasn't updated in THIS specific frame, do not draw it.
            # This makes the "Floating Green Boxes" disappear instantly.
            if track.last_seen_frame != tracker.frame_index:
                continue

            # FILTER 2: Skip very new tracks (flicker reduction)
            if (tracker.frame_index - track.first_seen_frame) < 3:
                continue

            color = (0, 0, 255) if track.state.is_ghost else (0, 255, 0)
            b = track.last_bbox
            
            # Draw Box
            cv2.rectangle(frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
            
            # Simple Label with Confidence
            text = f"ID:{track_id}"
            cv2.putText(frame, text, (int(b.x1), int(b.y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imshow("UVTP Optimized", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    tracker.flush_closed_sessions()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()