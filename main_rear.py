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
    collections.Mapping = collections.abc.Mapping  # type: ignore
if not hasattr(collections, "MutableMapping"):
    collections.MutableMapping = collections.abc.MutableMapping  # type: ignore
if not hasattr(collections, "Iterable"):
    collections.Iterable = collections.abc.Iterable  # type: ignore

# --- NEW: PyTorch 2.0+ Compatibility Patch for Fast-ReID ---
if getattr(torch, "_six", None) is None:

    class _Six:
        string_classes = (str, bytes)

    torch._six = _Six()
    sys.modules["torch._six"] = torch._six
# -----------------------------------------------------------

sys.path.append(os.getcwd())

from ultralytics import YOLO  # type: ignore
from uvtp import UVTPTrackerLoop, VehicleObservation, Detection, BoundingBox, UVTPConfig
from uvtp.feature_extractor import FastReIDVehicleExtractor

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_SOURCE = os.path.join(BASE_DIR, "test_video_rear.mp4")
YOLO_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "yolov10_custom.pt")
REID_CONFIG = os.path.join(
    BASE_DIR, "fast-reid", "configs", "VERI", "bagtricks_R50.yml"
)
REID_WEIGHTS = os.path.join(BASE_DIR, "checkpoints", "veri_resnet50.pth")

SNAPSHOT_DIR = os.path.join(BASE_DIR, "output", "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

CLASS_MAP = {1: "bike", 2: "car", 3: "bike", 5: "bus", 7: "truck"}
VEHICLE_CLASSES = ["car", "bike", "bus", "truck"]


def get_box_details(boxA, boxB):
    # Standard Intersection
    xA = max(boxA.x1, boxB.x1)
    yA = max(boxA.y1, boxB.y1)
    xB = min(boxA.x2, boxB.x2)
    yB = min(boxA.y2, boxB.y2)
    interArea = max(0, xB - xA) * max(0, yB - yA)

    boxAArea = (boxA.x2 - boxA.x1) * (boxA.y2 - boxA.y1)
    boxBArea = (boxB.x2 - boxB.x1) * (boxB.y2 - boxB.y1)

    # 1. IoU
    iou = 0.0
    if (boxAArea + boxBArea - interArea) > 0:
        iou = interArea / float(boxAArea + boxBArea - interArea)

    # 2. Containment (How much of Small is inside Large?)
    min_area = min(boxAArea, boxBArea)
    containment = 0.0
    if min_area > 0:
        containment = interArea / min_area

    # 3. Scale Ratio
    max_area = max(boxAArea, boxBArea)
    ratio = 0.0 if max_area == 0 else min_area / max_area

    # 4. Centroid Distance
    cA = ((boxA.x1 + boxA.x2) / 2, (boxA.y1 + boxA.y2) / 2)
    cB = ((boxB.x1 + boxB.x2) / 2, (boxB.y1 + boxB.y2) / 2)
    dist = math.sqrt((cA[0] - cB[0]) ** 2 + (cA[1] - cB[1]) ** 2)

    return iou, containment, ratio, dist


def main():
    print("[INFO] Loading YOLO...")
    model = YOLO(YOLO_WEIGHTS)

    print("[INFO] Loading Vehicle-ReID...")
    reid_extractor = FastReIDVehicleExtractor(
        config_file=REID_CONFIG,
        weights_path=REID_WEIGHTS,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )

    # 2. CONFIGURE TRACKER
    config = UVTPConfig(
        reid_cosine_match_threshold=0.65, ghost_min_consecutive_no_plate_frames=5
    )

    tracker = UVTPTrackerLoop(
        camera_id="CAM-01",
        reid_matcher=reid_extractor,
        config=config,
        evidence_root="./output/evidence",
        session_close_after_lost_frames=10,
    )

    cap = cv2.VideoCapture(VIDEO_SOURCE)

    # --- NEW: Safety check to ensure the video actually loads ---
    if not cap.isOpened():
        print(f"[ERROR] Could not open video file at: {VIDEO_SOURCE}")
        print("Please verify the video is uploaded to your Azure server.")
        sys.exit(1)
    # ------------------------------------------------------------

    TARGET_WIDTH = 1024
    FRAME_SKIP = 2
    frame_count = 0

    # --- NEW: Configure Headless Video Writer ---
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = TARGET_WIDTH / orig_w
    new_h = int(orig_h * scale)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    output_path = os.path.join(BASE_DIR, "output", "output_tracked.mp4")
    out = cv2.VideoWriter(output_path, fourcc, fps, (TARGET_WIDTH, new_h))
    # --------------------------------------------

    track_start_positions = {}
    vehicle_registry = {}

    print("[INFO] Starting Stream...")

    while cap.isOpened():
        ret, raw_frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue

        h, w = raw_frame.shape[:2]
        frame = cv2.resize(raw_frame, (TARGET_WIDTH, new_h))
        frame_h, frame_w = frame.shape[:2]

        zone_top = frame_h * 0.15
        zone_bottom = frame_h * 0.90

        # 4. YOLO Inference
        results = model(frame, verbose=False, conf=0.15)[0]

        # --- LAYER 1: NESTED NMS (The Fix for Double Detection) ---
        raw_candidates = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            label = CLASS_MAP.get(cls_id, None)

            if not label:
                continue
            cy = (y1 + y2) / 2
            if cy < zone_top or cy > zone_bottom:
                continue

            raw_candidates.append(
                {"bbox": BoundingBox(x1, y1, x2, y2), "conf": conf, "label": label}
            )

        raw_candidates.sort(key=lambda x: x["conf"], reverse=True)
        filtered_candidates = []

        while raw_candidates:
            current = raw_candidates.pop(0)
            filtered_candidates.append(current)

            survivors = []
            for c in raw_candidates:
                iou, containment, size_ratio, dist = get_box_details(
                    current["bbox"], c["bbox"]
                )
                is_diff_class = current["label"] != c["label"]

                # RULE 1: SAME CLASS CONTAINMENT (Bike inside Bike) -> KILL
                if not is_diff_class and containment > 0.70:
                    continue  # KILL IT. It's a duplicate part-detection.

                # RULE 2: DIFFERENT CLASS PROTECTION (Bike inside Van) -> KEEP
                if is_diff_class and size_ratio < 0.40:
                    survivors.append(c)  # Keep it.
                elif is_diff_class:
                    if iou < 0.85:
                        survivors.append(c)
                else:
                    # Same class, similar size -> Standard NMS
                    if iou < 0.50:
                        survivors.append(c)

            raw_candidates = survivors

        # 5. Extract Features
        observations = []
        for cand in filtered_candidates:
            x1, y1, x2, y2 = (
                cand["bbox"].x1,
                cand["bbox"].y1,
                cand["bbox"].x2,
                cand["bbox"].y2,
            )
            cx1, cy1 = max(0, int(x1)), max(0, int(y1))
            cx2, cy2 = min(frame_w, int(x2)), min(frame_h, int(y2))
            vehicle_crop = frame[cy1:cy2, cx1:cx2]

            min_size = 5 if cand["label"] == "bike" else 15

            if (
                vehicle_crop.size > 0
                and vehicle_crop.shape[0] > min_size
                and vehicle_crop.shape[1] > min_size
            ):
                embedding = reid_extractor.extract_embedding(vehicle_crop)
                obs = VehicleObservation(
                    label=cand["label"],
                    bbox=cand["bbox"],
                    confidence=cand["conf"],
                    embedding=embedding,
                    frame_size=(frame_w, frame_h),
                    snapshot_jpeg_bytes=None,
                )
                observations.append(obs)

        # 6. Step Tracker
        tracker.process_frame(observations, [])

        # --- LAYER 2: VISUAL DEDUPLICATION (The Accuracy Booster) ---
        track_ids = list(tracker.active_tracks.keys())
        removal_list = []

        for i in range(len(track_ids)):
            id_a = track_ids[i]
            if id_a in removal_list:
                continue
            track_a = tracker.active_tracks[id_a]

            for j in range(i + 1, len(track_ids)):
                id_b = track_ids[j]
                if id_b in removal_list:
                    continue
                track_b = tracker.active_tracks[id_b]

                iou, containment, size_ratio, dist = get_box_details(
                    track_a.last_bbox, track_b.last_bbox
                )

                class_a = track_a.state.vehicle_class
                class_b = track_b.state.vehicle_class
                is_diff_class = class_a != class_b

                try:
                    visual_dist = reid_extractor.cosine_distance(
                        track_a.last_embedding, track_b.last_embedding
                    )  # type: ignore
                    is_visually_identical = visual_dist < 0.15
                except:
                    is_visually_identical = False

                should_merge = False

                # Case A: Same Class, Nested/Overlapping
                if not is_diff_class:
                    if (
                        iou > 0.40
                        or containment > 0.60
                        or (is_visually_identical and dist < 50)
                    ):
                        should_merge = True

                # Case B: Diff Class
                else:
                    if iou > 0.85:
                        should_merge = True

                if should_merge:
                    age_a = track_a.last_seen_frame - track_a.first_seen_frame
                    age_b = track_b.last_seen_frame - track_b.first_seen_frame
                    if age_a >= age_b:
                        removal_list.append(id_b)
                    else:
                        removal_list.append(id_a)

        for dead_id in removal_list:
            if dead_id in tracker.active_tracks:
                del tracker.active_tracks[dead_id]

                # 7. VISUALIZATION AND HIGH-RES SNAPSHOT REGISTRY
                for track_id, track in tracker.active_tracks.items():
                    if track_id in removal_list:
                        continue
                    if (tracker.frame_index - track.last_seen_frame) > 4:
                        continue

                    b = track.last_bbox
                    center_x = (b.x1 + b.x2) / 2
                    center_y = (b.y1 + b.y2) / 2

                    if track_id not in track_start_positions:
                        track_start_positions[track_id] = (center_x, center_y)

                    start_x, start_y = track_start_positions[track_id]

                    # Trajectory Math
                    delta_x = center_x - start_x
                    delta_y = center_y - start_y
                    displacement = math.sqrt(delta_x**2 + delta_y**2)

                    # --- IMPROVEMENT 2: OPPOSITE LANE FILTER ---
                    # Assuming incoming traffic moves from Top to Bottom (Y increases).
                    # If a vehicle has moved more than 40 pixels UP the screen, it is in the opposite lane.
                    if delta_y < -40:
                        continue

                        # --- IMPROVEMENT 3: STRICT STATIC VEHICLE FILTER ---
                    # A vehicle must move a minimum radial distance to prove it is not parked/static background noise.
                    if displacement < 75:
                        continue

                    age = tracker.frame_index - track.first_seen_frame
                    is_bike = track.state.vehicle_class == "bike"
                    if not is_bike and age < 3:
                        continue

                    # Map coordinates back to raw_frame dimensions
                    orig_x1 = max(0, int(b.x1 / scale))
                    orig_y1 = max(0, int(b.y1 / scale))
                    orig_x2 = min(w, int(b.x2 / scale))
                    orig_y2 = min(h, int(b.y2 / scale))
                    orig_cy = (orig_y1 + orig_y2) / 2

                    # --- IMPROVEMENT 4: THE FOCAL SWEET SPOT ---
                    # We define the ideal optical zone as the direct center of the vertical frame.
                    ideal_center_y = h * 0.50
                    distance_to_center = abs(orig_cy - ideal_center_y)

                    # The vehicle MUST be between 30% and 75% of the frame height to be captured.
                    in_capture_zone = (h * 0.30) < orig_cy < (h * 0.75)

                    if in_capture_zone:
                        is_new_track = track_id not in vehicle_registry

                        # Instead of 'max_area', we overwrite the snapshot only when it gets CLOSER to the true center.
                        is_better_shot = (
                            not is_new_track
                            and distance_to_center
                            < vehicle_registry[track_id].get(
                                "min_dist_to_center", float("inf")
                            )
                        )

                        if is_new_track or is_better_shot:
                            # --- IMPROVEMENT 1: DYNAMIC ASYMMETRIC PADDING ---
                            box_w = orig_x2 - orig_x1
                            box_h = orig_y2 - orig_y1

                            # Standard padding for the sides and bottom (15%)
                            pad_w = int(box_w * 0.15)
                            pad_h_bottom = int(box_h * 0.15)

                            # Massively extend the TOP boundary only if it is a bike
                            if track.state.vehicle_class == "bike":
                                # Stretch upward by 85% of the bike's height to catch the helmet
                                pad_h_top = int(box_h * 0.85)
                            else:
                                # Standard 15% top padding for cars, trucks, and buses
                                pad_h_top = int(box_h * 0.15)

                            px1 = max(0, orig_x1 - pad_w)
                            py1 = max(0, orig_y1 - pad_h_top)
                            px2 = min(w, orig_x2 + pad_w)
                            py2 = min(h, orig_y2 + pad_h_bottom)

                            snapshot_img = raw_frame[py1:py2, px1:px2]

                            if snapshot_img.size > 0:
                                snap_h_img, snap_w_img = snapshot_img.shape[:2]
                                max_dim = max(snap_h_img, snap_w_img)

                                # 1B. Force Minimum Resolution of 600p via Bicubic Interpolation
                                if max_dim < 600:
                                    upscale_factor = 600.0 / max_dim
                                    new_snap_w = int(snap_w_img * upscale_factor)
                                    new_snap_h = int(snap_h_img * upscale_factor)
                                    # INTER_CUBIC is computationally heavier but preserves edge details like text much better than linear.
                                    snapshot_img = cv2.resize(
                                        snapshot_img,
                                        (new_snap_w, new_snap_h),
                                        interpolation=cv2.INTER_CUBIC,
                                    )

                                if is_new_track:
                                    vehicle_registry[track_id] = {
                                        "id": track_id,
                                        "first_seen": datetime.now(),
                                        "min_dist_to_center": distance_to_center,
                                    }
                                    print(f"[REGISTERED] {track_id} in Sweet Spot")
                                else:
                                    vehicle_registry[track_id][
                                        "min_dist_to_center"
                                    ] = distance_to_center

                                filename = f"{track_id}_{track.state.vehicle_class}.jpg"
                                cv2.imwrite(
                                    os.path.join(SNAPSHOT_DIR, filename), snapshot_img
                                )

                    # Draw visualization on the downscaled frame
                    color = (0, 0, 255) if track.state.is_ghost else (0, 255, 0)
                    cv2.rectangle(
                        frame, (int(b.x1), int(b.y1)), (int(b.x2), int(b.y2)), color, 2
                    )
                    cv2.putText(
                        frame,
                        f"{track_id}",
                        (int(b.x1), int(b.y1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2,
                    )

        # --- NEW: Write the processed frame to the mp4 file ---
        out.write(frame)

    # --- NEW: Clean up and finalize the file ---
    tracker.flush_closed_sessions()
    cap.release()
    out.release()

    print(f"\n[INFO] Total Unique Vehicles Tracked: {len(vehicle_registry)}")
    print(f"[INFO] Tracking complete. Video saved to: {output_path}")


if __name__ == "__main__":
    main()
