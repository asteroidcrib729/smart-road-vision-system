import cv2
import torch
import numpy as np
import collections
import collections.abc
import sys
import os
import math
import time
from datetime import datetime

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

SNAPSHOT_DIR = os.path.join(BASE_DIR, "output", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

CLASS_MAP = { 1: "bike", 2: "car", 3: "bike", 5: "bus", 7: "truck" }
VEHICLE_CLASSES = ["car", "bike", "bus", "truck"]

def calculate_iou_and_area_ratio(boxA, boxB):
    xA = max(boxA.x1, boxB.x1)
    yA = max(boxA.y1, boxB.y1)
    xB = min(boxA.x2, boxB.x2)
    yB = min(boxA.y2, boxB.y2)
    interArea = max(0, xB - xA) * max(0, yB - yA)
    
    boxAArea = (boxA.x2 - boxA.x1) * (boxA.y2 - boxA.y1)
    boxBArea = (boxB.x2 - boxB.x1) * (boxB.y2 - boxB.y1)
    
    iou = 0.0
    if (boxAArea + boxBArea - interArea) > 0:
        iou = interArea / float(boxAArea + boxBArea - interArea)

    min_area = min(boxAArea, boxBArea)
    max_area = max(boxAArea, boxBArea)
    ratio = 0.0 if max_area == 0 else min_area / max_area
    return iou, ratio

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
    TARGET_WIDTH = 1024 
    FRAME_SKIP = 2
    frame_count = 0

    # --- RUNTIME REGISTRIES ---
    # 1. Stores the first position of every track to calculate movement
    track_start_positions = {} 
    
    # 2. The Master Registry: Stores data for every unique vehicle we have officially "accepted"
    # Format: { "T001": { "class": "car", "first_seen": time, "snapshot": path } }
    vehicle_registry = {}

    print("[INFO] Starting Stream...")
    
    while cap.isOpened():
        ret, raw_frame = cap.read()
        if not ret: break
        
        frame_count += 1
        if frame_count % FRAME_SKIP != 0: continue

        h, w = raw_frame.shape[:2]
        scale = TARGET_WIDTH / w
        new_h = int(h * scale)
        frame = cv2.resize(raw_frame, (TARGET_WIDTH, new_h))
        frame_h, frame_w = frame.shape[:2]
        
        zone_top = frame_h * 0.15     
        zone_bottom = frame_h * 0.90 

        # 4. YOLO Inference
        results = model(frame, verbose=False, conf=0.15)[0] 
        
        # --- LAYER 1: SCALE-AWARE NMS ---
        raw_candidates = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            label = CLASS_MAP.get(cls_id, None)
            
            if not label: continue
            cy = (y1 + y2) / 2
            if cy < zone_top or cy > zone_bottom: continue

            raw_candidates.append({
                "bbox": BoundingBox(x1, y1, x2, y2),
                "conf": conf,
                "label": label
            })

        raw_candidates.sort(key=lambda x: x["conf"], reverse=True)
        filtered_candidates = []
        
        while raw_candidates:
            current = raw_candidates.pop(0)
            filtered_candidates.append(current)
            survivors = []
            for c in raw_candidates:
                iou, size_ratio = calculate_iou_and_area_ratio(current["bbox"], c["bbox"])
                is_diff_class = (current["label"] != c["label"])
                is_scale_mismatch = (size_ratio < 0.40)

                if is_diff_class and is_scale_mismatch: survivors.append(c)
                elif is_diff_class:
                     if iou < 0.90: survivors.append(c)
                else:
                    if iou < 0.50: survivors.append(c)
            raw_candidates = survivors

        # 5. Extract Features
        observations = []
        for cand in filtered_candidates:
            x1, y1, x2, y2 = cand["bbox"].x1, cand["bbox"].y1, cand["bbox"].x2, cand["bbox"].y2
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

        # --- LAYER 2: SCALE-AWARE TRACK MERGER ---
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

                iou, size_ratio = calculate_iou_and_area_ratio(track_a.last_bbox, track_b.last_bbox)
                
                if size_ratio < 0.40: continue 

                class_a = track_a.state.vehicle_class
                class_b = track_b.state.vehicle_class
                is_diff_class = (class_a != class_b)
                threshold = 0.85 if is_diff_class else 0.40

                if iou > threshold:
                    age_a = track_a.last_seen_frame - track_a.first_seen_frame
                    age_b = track_b.last_seen_frame - track_b.first_seen_frame
                    if age_a >= age_b: removal_list.append(id_b)
                    else: removal_list.append(id_a)

        for dead_id in removal_list:
            if dead_id in tracker.active_tracks:
                del tracker.active_tracks[dead_id]

        # 7. VISUALIZATION & REGISTRY LOGIC
        for track_id, track in tracker.active_tracks.items():
            if track_id in removal_list: continue
            if (tracker.frame_index - track.last_seen_frame) > 4: continue

            # --- STATIONARY FILTER (PARKED VEHICLE REMOVAL) ---
            b = track.last_bbox
            center = ((b.x1 + b.x2)/2, (b.y1 + b.y2)/2)

            if track_id not in track_start_positions:
                track_start_positions[track_id] = center
            
            start_pos = track_start_positions[track_id]
            # Calculate distance moved since first appearance
            displacement = math.sqrt((center[0]-start_pos[0])**2 + (center[1]-start_pos[1])**2)
            
            # AGE CHECK: If track is > 15 frames old but has moved < 50 pixels, it is PARKED.
            # We SKIP it. (It won't be drawn, won't be registered, won't be snapshotted)
            age = tracker.frame_index - track.first_seen_frame
            if age > 15 and displacement < 50:
                continue 

            # --- "NEW ID" WAIT ---
            # Don't register tracks that are too young (flicker protection)
            is_bike = (track.state.vehicle_class == "bike")
            if not is_bike and age < 3: 
                continue

            # --- REGISTRY & SNAPSHOT ---
            # If this is a valid moving vehicle we haven't seen before...
            if track_id not in vehicle_registry:
                # 1. Add to Dictionary
                vehicle_registry[track_id] = {
                    "id": track_id,
                    "class": track.state.vehicle_class,
                    "first_seen": datetime.now().strftime("%H:%M:%S"),
                    "status": "MOVING"
                }
                
                # 2. TAKE SNAPSHOT IMMEDIATELY
                # Crop the vehicle
                cx1, cy1 = max(0, int(b.x1)), max(0, int(b.y1))
                cx2, cy2 = min(frame_w, int(b.x2)), min(frame_h, int(b.y2))
                snapshot_img = frame[cy1:cy2, cx1:cx2]
                
                if snapshot_img.size > 0:
                    filename = f"{track_id}_{track.state.vehicle_class}.jpg"
                    save_path = os.path.join(SNAPSHOT_DIR, filename)
                    cv2.imwrite(save_path, snapshot_img)
                    print(f"[REGISTERED] {track_id} - Snapshot saved: {filename}")

            # --- DRAWING ---
            # Only draw if it passed the Stationary Check
            color = (0, 0, 255) if track.state.is_ghost else (0, 255, 0)
            cv2.rectangle(frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2)
            cv2.putText(frame, f"{track_id}", (int(b.x1), int(b.y1)-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("UVTP Final Registry", frame)
        if cv2.waitKey(1) == ord('q'): break

    tracker.flush_closed_sessions()
    cap.release()
    cv2.destroyAllWindows()
    
    # Print Final Registry Summary
    print(f"\n[INFO] Total Unique Vehicles Tracked: {len(vehicle_registry)}")

if __name__ == "__main__":
    main()