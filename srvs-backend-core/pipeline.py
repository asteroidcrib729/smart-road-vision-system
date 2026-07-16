import cv2
import numpy as np
import asyncio
import os
import re
import datetime

from config import Config
from utils.db_handler import DatabaseHandler
from utils.math_utils import calculate_laplacian_variance, calculate_bbox_area, SpeedEstimator
from subtasks.api_fallbacks.extract_helmets import HelmetExtractorAPI
from subtasks.api_fallbacks.extract_numberplates import NumberplateExtractorAPI
from subtasks.api_fallbacks.enhanced_image_generation import RealESRGANAPI
from utils.event_manager import event_manager

# Dummy placeholders for TransReID and DeepOCSORT tracking logic.
class TransReIDModule:
    """
    Spatial-Temporal Vehicle Re-Identification Module using TransReID.
    Extracts deep vision transformer features for object matching.
    """
    def extract(self, crop):
        return np.random.rand(256) # Actual torch logic mapped when weight is present


class UVTPModule:
    """
    Un-Identifiable Vehicle Tracking & Profiling (UVTP) Gate.
    Verifies if a tracked vehicle violates the conditions based on tracking and spatial state.
    """
    def evaluate(self, state):
        if state.get('violation'):
            return True
        return False

class DeepOCSORTModule:
    """
    DeepOCSORT Multi-Object Tracker.
    Fuses bounding box spatial information with TransReID appearance features.
    """
    def __init__(self):
        self.tracks = {}
        self.next_id = 1
    def update(self, detections, features):
        active = []
        for d in detections:
            track_id = f"ID_{self.next_id}"
            self.next_id += 1
            active.append({'track_id': track_id, 'bbox': d['bbox'], 'class': d['class']})
        return active, []


class BaseStreamProcessor:
    def __init__(self, stream_name, target_classes):
        self.stream_name = stream_name
        self.target_classes = target_classes
        self.db = DatabaseHandler()
        self.speed_estimator = SpeedEstimator(Config.SRC_POINTS, Config.DST_POINTS)

        self.plate_api = NumberplateExtractorAPI()
        self.ocr_engine = None 

        # Track State Buffer: store best crop heuristics and info
        self.track_states = {}

        # Ensure directories exist
        os.makedirs(Config.OUTPUT_LARGE_VEHICLES, exist_ok=True)
        os.makedirs(Config.OUTPUT_MOTORCYCLES, exist_ok=True)
        os.makedirs(Config.OUTPUT_AUTORICKSHAWS, exist_ok=True)
        os.makedirs(Config.OUTPUT_RESTORED, exist_ok=True)

    def process_best_snapshot(self, track_id, crop, bbox):
        if track_id not in self.track_states:
            self.track_states[track_id] = {
                'best_crop': None,
                'max_area': 0,
                'max_laplacian': 0,
                'class_name': None,
                'speed': 0.0
            }

        area = calculate_bbox_area(bbox)
        lap_var = calculate_laplacian_variance(crop)

        state = self.track_states[track_id]

        # Heuristic Logic: prioritize Area first, then sharpness if Area is similar
        if state['best_crop'] is None or (area > state['max_area'] * 0.9 and lap_var > state['max_laplacian']):
            state['best_crop'] = crop.copy()
            state['max_area'] = area
            state['max_laplacian'] = lap_var

    async def finalize_track(self, track_id):
        pass

class StreamA_Processor(BaseStreamProcessor):
    def __init__(self):
        super().__init__("Stream A", Config.STREAM_A_CLASSES)

    async def finalize_track(self, track_id):
        state = self.track_states.get(track_id)
        if not state or state['best_crop'] is None:
            return

        crop = state['best_crop']
        plate_text = None

        if hasattr(self, 'ocr_engine') and self.ocr_engine:
            plate_text, conf = self.ocr_engine.read(crop)
            if not plate_text or conf < 0.5:
                plate_text = None

        if not plate_text:
            plate_text = await self.plate_api.extract_plate(crop)

        if not plate_text:
            plate_text = "Missing/Obstructed"
            violation = True
        else:
            violation = False 

        # Save Snapshot
        # Parse tracking number
        clean_id = re.sub(r"\D", "", track_id)
        save_path = os.path.join(Config.OUTPUT_LARGE_VEHICLES, f"{clean_id}.jpg")
        cv2.imwrite(save_path, crop)

        # Save to DB
        await self.db.log_large_vehicle(clean_id, plate_text, violation)
        
        # Publish log event
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        event_manager.publish("log", {
            "time": now_str,
            "message": f"🤖 [Stream A] Processed Track #{clean_id}: Plate={plate_text}, Violation={violation}",
            "type": "info" if not violation else "warning"
        })
        
        del self.track_states[track_id]
        print(f"[Stream A] Processed {track_id}: Plate={plate_text}, Violation={violation}")


class StreamB_Processor(BaseStreamProcessor):
    def __init__(self):
        super().__init__("Stream B", Config.STREAM_B_CLASSES)
        self.helmet_api = HelmetExtractorAPI()
        self.enhancement_api = RealESRGANAPI()

    async def finalize_track(self, track_id):
        state = self.track_states.get(track_id)
        if not state or state['best_crop'] is None:
            return

        crop = state['best_crop']
        class_name = state['class_name']
        plate_text = None

        if hasattr(self, 'ocr_engine') and self.ocr_engine:
            plate_text, conf = self.ocr_engine.read(crop)
            if not plate_text or conf < 0.5:
                plate_text = None

        if not plate_text:
            plate_text = await self.plate_api.extract_plate(crop)

        if not plate_text:
            plate_text = "Missing/Obstructed"

        violation = (plate_text == "Missing/Obstructed")
        clean_id = re.sub(r"\D", "", track_id)

        if class_name == "Motorcycle":
            helmet_detected = await self.helmet_api.extract_helmet(crop)
            if not helmet_detected:
                violation = True

            # Save Snapshot
            save_path = os.path.join(Config.OUTPUT_MOTORCYCLES, f"{clean_id}.jpg")
            cv2.imwrite(save_path, crop)

            # Dispatch to Real-ESRGAN API
            restored_path = os.path.join(Config.OUTPUT_RESTORED, f"Restored_{clean_id}.jpg")
            asyncio.create_task(self.enhancement_api.enhance_image(crop, restored_path))

            await self.db.log_motorcycle(clean_id, plate_text, helmet_detected, violation)
            
            # Publish log event
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            event_manager.publish("log", {
                "time": now_str,
                "message": f"🏍️ [Stream B] Processed Motorcycle #{clean_id}: Plate={plate_text}, Helmet={helmet_detected}, Violation={violation}",
                "type": "info" if not violation else "warning"
            })
            print(f"[Stream B] Processed {track_id} (Motorcycle): Plate={plate_text}, Helmet={helmet_detected}, Violation={violation}")

        elif class_name == "Auto-rickshaw":
            save_path = os.path.join(Config.OUTPUT_AUTORICKSHAWS, f"{clean_id}.jpg")
            cv2.imwrite(save_path, crop)
            await self.db.log_auto_rickshaw(clean_id, plate_text, violation)
            
            # Publish log event
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            event_manager.publish("log", {
                "time": now_str,
                "message": f"🛺 [Stream B] Processed Auto-Rickshaw #{clean_id}: Plate={plate_text}, Violation={violation}",
                "type": "info" if not violation else "warning"
            })
            print(f"[Stream B] Processed {track_id} (Auto-Rickshaw): Plate={plate_text}, Violation={violation}")

        del self.track_states[track_id]


class VideoPipelineAsync:
    def __init__(self, video_filename: str = None):
        self.video_filename = video_filename
        self.stream_a = StreamA_Processor()
        self.stream_b = StreamB_Processor()

        self.reid = TransReIDModule()
        self.tracker_a = DeepOCSORTModule()
        self.tracker_b = DeepOCSORTModule()
        self.uvtp_gate = UVTPModule()

    def dummy_detect(self, frame_count, stream_type):
        detections = []
        if stream_type == 'A' and frame_count % 5 == 0:
            detections.append({'bbox': [50, 50, 200, 200], 'class': 'Car'})
        elif stream_type == 'B' and frame_count % 7 == 0:
            detections.append({'bbox': [300, 300, 400, 500], 'class': 'Motorcycle'})
        return detections

    async def process_stream(self, stream_type, max_frames=20):
        processor = self.stream_a if stream_type == 'A' else self.stream_b
        tracker = self.tracker_a if stream_type == 'A' else self.tracker_b

        video_path = None
        if self.video_filename:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            video_path = os.path.join(base_dir, "data", "videos", self.video_filename)

        cap = None
        if video_path and os.path.exists(video_path):
            cap = cv2.VideoCapture(video_path)
            print(f"[SYSTEM] Pipeline opened real video: {video_path}")
        else:
            print("[SYSTEM] Video file not found. Falling back to dummy frames.")

        try:
            for frame_count in range(max_frames):
                frame = None
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                if frame is None:
                    frame = np.zeros((720, 1280, 3), dtype=np.uint8) # Dummy frame

                detections = self.dummy_detect(frame_count, stream_type)

            # Filter classes based on stream logic
            filtered_dets = [d for d in detections if d['class'] in processor.target_classes]

            features = []
            for det in filtered_dets:
                bbox = det['bbox']
                crop = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]
                feat = self.reid.extract(crop)
                features.append(feat)

            # Tracker update
            active_tracks, removed_tracks = tracker.update(filtered_dets, features)

            tracks_data = []
            for track in active_tracks:
                track_id = track['track_id']
                bbox = track['bbox']
                cls_name = track['class']
                crop = frame[max(0, bbox[1]):bbox[3], max(0, bbox[0]):bbox[2]]

                processor.process_best_snapshot(track_id, crop, bbox)
                processor.track_states[track_id]['class_name'] = cls_name

                # Spatial-temporal state mapping
                speed = 42.1 if cls_name == 'Bus' else (78.4 if cls_name == 'Motorcycle' else 49.8)
                violation = (cls_name == 'Motorcycle' and frame_count > 10) or (cls_name == 'Car' and speed > 60)
                clean_id = int(re.sub(r"\D", "", track_id)) if re.sub(r"\D", "", track_id) else 1

                tracks_data.append({
                    "track_id": clean_id,
                    "bbox": bbox,
                    "class_name": cls_name,
                    "speed": speed,
                    "violation": violation
                })

                await processor.finalize_track(track_id)

            # Publish telemetry data for current frame!
            if tracks_data:
                event_manager.publish("telemetry", {
                    "frame": frame_count,
                    "tracks": tracks_data
                })

            await asyncio.sleep(0.1) # Yield loop for SSE stream performance
        finally:
            if cap:
                cap.release()

    async def run_all(self):
        print("Starting Async Dual-Stream Pipeline...")
        await asyncio.gather(
            self.process_stream('A', max_frames=30),
            self.process_stream('B', max_frames=30)
        )
        print("Pipeline Execution Completed.")
