import cv2
import torch
import numpy as np
import collections
import collections.abc
import sys
import os

# --- MONKEY PATCH ---
if not hasattr(collections, "Mapping"):
    collections.Mapping = collections.abc.Mapping # type: ignore
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping # type: ignore
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable # type: ignore

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

CLASS_MAP = { 1: "bike", 2: "car", 3: "bike", 5: "bus", 7: "truck" }
VEHICLE_CLASSES = ["car", "bike", "bus", "truck"]

# --- HELPER: IoU CALCULATION ---
def calculate_iou(boxA, boxB):
    # Determine the coordinates of the intersection rectangle
    xA = max(boxA.x1, boxB.x1)
    yA = max(boxA.y1, boxB.y1)
    xB = min(boxA.x2, boxB.x2)
    yB = min(boxA.y2, boxB.y2)

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0: return 0.0

    boxAArea = (boxA.x2 - boxA.x1) * (boxA.y2 - boxA.y1)
    boxBArea = (boxB.x2 - boxB.x1) * (boxB.y2 - boxB.y1)

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def main():
    print("[INFO] Loading YOLO...")
    model = YOLO(YOLO_WEIGHTS)
    
    print("[INFO] Loading Vehicle-ReID...")
    reid_extractor = FastReIDVehicleExtractor(
        config_file=REID_CONFIG,
        weights_path=REID_WEIGHTS,
        device="cuda" if torch.cuda.is_available() else "cpu"
    )

    # 2. CONFIGURE TRACKER
    config = UVTPConfig(
        reid_cosine_match_threshold=0.65, 
        ghost_min_consecutive_no_plate_frames=5
    )

    tracker = UVTPTrackerLoop(
        camera_id="CAM-01",
        reid_matcher=reid_extractor,
        config=config, 
        evidence_root="./output/evidence",
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
        if not ret: break
        
        frame_count += 1
        if frame_count % FRAME_SKIP != 0: continue

        # Resize
        h, w = raw_frame.shape[:2]
        scale = TARGET_WIDTH / w
        new_h = int(h * scale)
        frame = cv2.resize(raw_frame, (TARGET_WIDTH, new_h))
        frame_h, frame_w = frame.shape[:2]
        
        # Define ROI
        zone_top = frame_h * 0.15     
        zone_bottom = frame_h * 0.85 

        # 4. YOLO Inference (Low conf to catch bikes)
        results = model(frame, verbose=False, conf=0.25)[0] 
        
        # --- LAYER 1: CLASS-AGNOSTIC NMS ---
        # We collect ALL raw boxes first, then filter them.
        raw_candidates = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            label = CLASS_MAP.get(cls_id, None)
            
            if not label: continue
            
            # ROI Check
            cy = (y1 + y2) / 2
            if cy < zone_top or cy > zone_bottom: continue

            raw_candidates.append({
                "bbox": BoundingBox(x1, y1, x2, y2),
                "conf": conf,
                "label": label
            })

        # Logic: Sort by confidence. If a box overlaps heavily with a higher-conf box, KILL IT.
        # This stops "Car" and "Truck" boxes appearing on the same object.
        raw_candidates.sort(key=lambda x: x["conf"], reverse=True)
        filtered_candidates = []
        
        while raw_candidates:
            current = raw_candidates.pop(0)
            filtered_candidates.append(current)
            # Remove any remaining box that overlaps > 50% with 'current'
            # regardless of class label.
            raw_candidates = [
                c for c in raw_candidates 
                if calculate_iou(current["bbox"], c["bbox"]) < 0.50
            ]

        # 5. Extract Features for Filtered Candidates
        observations = []
        for cand in filtered_candidates:
            x1, y1, x2, y2 = cand["bbox"].x1, cand["bbox"].y1, cand["bbox"].x2, cand["bbox"].y2
            
            # Crop
            cx1, cy1 = max(0, int(x1)), max(0, int(y1))
            cx2, cy2 = min(frame_w, int(x2)), min(frame_h, int(y2))
            vehicle_crop = frame[cy1:cy2, cx1:cx2]
            
            min_size = 5 if cand["label"] == "bike" else 15

            if vehicle_crop.size > 0 and vehicle_crop.shape[0] > min_size and vehicle_crop.shape[1] > min_size:
                embedding = reid_extractor.extract_embedding(vehicle_crop)
                obs = VehicleObservation(
                    label=cand["label"],
                    bbox=cand["bbox"],
                    confidence=cand["conf"],
                    embedding=embedding,
                    frame_size=(frame_w, frame_h),
                    snapshot_jpeg_bytes=None
                )
                observations.append(obs)

        # 6. Step Tracker
        tracker.process_frame(observations, [])

        # --- LAYER 2: TRACK DEDUPLICATION (The Nuclear Fix) ---
        # If two ACTIVE tracks overlap significantly, delete the newer/shorter one.
        track_ids = list(tracker.active_tracks.keys())
        removal_list = []

        for i in range(len(track_ids)):
            id_a = track_ids[i]
            if id_a in removal_list: continue
            track_a = tracker.active_tracks[id_a]

            for j in range(i + 1, len(track_ids)):
                id_b = track_ids[j]
                if id_b in removal_list: continue
                track_b = tracker.active_tracks[id_b]

                # Check IoU between two Tracker IDs
                iou = calculate_iou(track_a.last_bbox, track_b.last_bbox)
                
                # If they overlap > 40%, they are the same physical car.
                if iou > 0.40:
                    # Keep the one that has been seen longer (more stable)
                    age_a = track_a.last_seen_frame - track_a.first_seen_frame
                    age_b = track_b.last_seen_frame - track_b.first_seen_frame
                    
                    if age_a >= age_b:
                        removal_list.append(id_b) # Kill B
                    else:
                        removal_list.append(id_a) # Kill A

        # Perform the deletion
        for dead_id in removal_list:
            if dead_id in tracker.active_tracks:
                del tracker.active_tracks[dead_id]

        # 7. Visualization
        for track_id, track in tracker.active_tracks.items():
            # Don't show tracks we explicitly killed
            if track_id in removal_list: continue
            
            # Stale check
            if (tracker.frame_index - track.last_seen_frame) > 2: continue

            # "Tentative" Check: Don't show box until we've tracked it for 3 frames
            # This hides the split-second "flicker" IDs.
            if (track.last_seen_frame - track.first_seen_frame) < 3: continue

            color = (0, 0, 255) if track.state.is_ghost else (0, 255, 0)
            b = track.last_bbox
            cv2.rectangle(frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
            cv2.putText(frame, f"{track_id}", (int(b.x1), int(b.y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("UVTP Final Hardened", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    tracker.flush_closed_sessions()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()