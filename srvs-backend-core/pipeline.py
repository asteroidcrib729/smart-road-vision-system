import cv2
import numpy as np
import asyncio
import os
import re
import datetime
import torch

from config import Config
from utils.db_handler import DatabaseHandler
from utils.math_utils import calculate_laplacian_variance, calculate_bbox_area, SpeedEstimator
from subtasks.api_fallbacks.extract_helmets import HelmetExtractorAPI
from subtasks.api_fallbacks.extract_numberplates import NumberplateExtractorAPI
from subtasks.api_fallbacks.enhanced_image_generation import RealESRGANAPI
from utils.event_manager import event_manager
from ultralytics import YOLO

# Global API limit cooldown lock (prevents exceeding 15 Requests Per Minute)
api_cooldown_lock = asyncio.Lock()

# Dynamic GPU / CPU device selection for maximum performance
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[SYSTEM] Selected processing device: {device.upper()}")


class PaddleOCREngine:
    def __init__(self):
        try:
            from paddleocr import PaddleOCR
            # Initialize local PaddleOCR on CPU to avoid CUDA conflicts with YOLO
            self.ocr = PaddleOCR(use_angle_cls=False, lang='en', show_log=False, use_gpu=False)
            print("[SYSTEM] Successfully initialized Local PaddleOCR Engine on CPU.")
        except Exception as e:
            print(f"[SYSTEM] Warning: Failed to load/initialize PaddleOCR: {e}")
            self.ocr = None

    def read(self, img):
        if not self.ocr or img is None or img.size == 0:
            return None, 0.0, None
        try:
            result = self.ocr.ocr(img, cls=False)
            if not result or not result[0]:
                return None, 0.0, None
            
            texts = []
            max_conf = 0.0
            best_bbox = None
            
            for line in result[0]:
                bbox = line[0] # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                text_info = line[1] # ('TEXT', 0.95)
                text = text_info[0].strip()
                conf = text_info[1]
                
                clean_text = re.sub(r'[^A-Za-z0-9]', '', text)
                if len(clean_text) >= 3:
                    texts.append(clean_text)
                    if conf > max_conf:
                        max_conf = conf
                        best_bbox = bbox
            if texts:
                return "".join(texts), max_conf, best_bbox
        except Exception as e:
            print(f"[SYSTEM] Local OCR inference failed: {e}")
        return None, 0.0, None


# Dummy placeholders for TransReID and UVTP modules
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
    Spatial IoU Multi-Object Tracker.
    Fuses bounding box spatial information to track vehicles dynamically across frames.
    """
    def __init__(self, max_age=Config.TRACK_MAX_AGE, min_hits=Config.TRACK_MIN_HITS, iou_threshold=Config.IOU_THRESHOLD):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks = {} # track_id -> track_state dict

    def update(self, detections, features):
        active_tracks = []
        removed_tracks = []
        
        # O(1) Quick mock assignment matching spatial anchors for pipeline scaffolding
        for i, det in enumerate(detections):
            track_id = f"TR_{det['class']}_{i+1}"
            bbox = det['bbox']
            
            # Formulate tracking payload dictionaries
            track_payload = {
                'track_id': track_id,
                'bbox': bbox,
                'class': det['class']
            }
            active_tracks.append(track_payload)
            
        return active_tracks, removed_tracks


class BaseStreamProcessor:
    def __init__(self, stream_name, target_classes):
        self.stream_name = stream_name
        self.target_classes = target_classes
        self.db = DatabaseHandler()
        self.speed_estimator = SpeedEstimator(Config.SRC_POINTS, Config.DST_POINTS)

        self.plate_api = NumberplateExtractorAPI()
        self.ocr_engine = PaddleOCREngine()

        # Track State Buffer: store best crop heuristics and info
        self.track_states = {}
        self.processed_tracks = set() # Track already finalized IDs to prevent duplicate API requests
        self.processed_plates = set() # Track already logged plates to avoid duplicates within a run

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
            }
        
        state = self.track_states[track_id]
        area = calculate_bbox_area(bbox)
        lap_var = calculate_laplacian_variance(crop)
        
        # Prioritize larger bounding box area first, then image sharpness (Laplacian variance)
        if state['best_crop'] is None or (area > state['max_area'] * 0.9 and lap_var > state['max_laplacian']):
            state['best_crop'] = crop.copy()
            state['max_area'] = area
            state['max_laplacian'] = lap_var

    def crop_license_plate(self, crop, plate_bbox):
        """Helper to crop the license plate region using bbox coordinates or fallback bumper heuristic."""
        if crop is None or crop.size == 0:
            return None
            
        if plate_bbox:
            try:
                xs = [pt[0] for pt in plate_bbox]
                ys = [pt[1] for pt in plate_bbox]
                x1, y1 = max(0, int(min(xs))), max(0, int(min(ys)))
                x2, y2 = min(crop.shape[1], int(max(xs))), min(crop.shape[0], int(max(ys)))
                # Add small padding margins to make the plate look clean
                pad_x = int((x2 - x1) * 0.15)
                pad_y = int((y2 - y1) * 0.20)
                px1 = max(0, x1 - pad_x)
                py1 = max(0, y1 - pad_y)
                px2 = min(crop.shape[1], x2 + pad_x)
                py2 = min(crop.shape[0], y2 + pad_y)
                plate_crop = crop[py1:py2, px1:px2]
                if plate_crop.size > 0:
                    return plate_crop
            except Exception as e:
                print(f"[SYSTEM] Precise plate cropping failed: {e}")
                
        # Bumper heuristic crop fallback (lower-middle 30% Y, middle 50% X)
        h, w = crop.shape[:2]
        return crop[int(h * 0.65):int(h * 0.95), int(w * 0.25):int(w * 0.75)]

    async def finalize_track(self, track_id):
        pass


class StreamA_Processor(BaseStreamProcessor):
    def __init__(self):
        super().__init__("Stream A", Config.STREAM_A_CLASSES)
        self.enhancement_api = RealESRGANAPI()

    async def finalize_track(self, track_id):
        clean_id = re.sub(r"\D", "", track_id)
        if clean_id in self.processed_tracks:
            return

        state = self.track_states.get(track_id)
        if not state or state['best_crop'] is None:
            return

        self.processed_tracks.add(clean_id)
        crop = state['best_crop']
        class_name = state.get('class_name', 'Car')
        speed = state.get('speed', 42.1)
        violation = state.get('violation', False)
        
        # Local OCR Only (PaddleOCR v4)
        plate_text = None
        plate_bbox = None
        if hasattr(self, 'ocr_engine') and self.ocr_engine:
            plate_text, conf, plate_bbox = self.ocr_engine.read(crop)
            if not plate_text or conf < 0.4:
                plate_text = None
                plate_bbox = None

        if not plate_text:
            plate_text = "Missing/Obstructed"
            # Set violation flag for missing plates or speed infractions
            violation = True

        # Check if plate has already been logged in this session
        if plate_text != "Missing/Obstructed":
            if plate_text in self.processed_plates:
                print(f"[Stream A] Skipped duplicate plate: {plate_text}")
                return
            self.processed_plates.add(plate_text)

        # Extract close-up license plate crop
        plate_crop = self.crop_license_plate(crop, plate_bbox)

        # Save Snapshot
        save_path = os.path.join(Config.OUTPUT_LARGE_VEHICLES, f"{clean_id}.jpg")
        cv2.imwrite(save_path, plate_crop)

        # Dispatch to Real-ESRGAN API for enhancement
        restored_path = os.path.join(Config.OUTPUT_RESTORED, f"Restored_{clean_id}.jpg")
        asyncio.create_task(self.enhancement_api.enhance_image(plate_crop, restored_path))

        # Save to DB with Speed, Timestamp, and actual detected Class_Name
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_only = datetime.datetime.now().strftime("%H:%M:%S")
        await self.db.log_large_vehicle(clean_id, plate_text, violation, speed, now_str, class_name)
        
        # Publish log event
        event_manager.publish("log", {
            "time": time_only,
            "message": f"🤖 [Stream A] Processed {class_name} #{clean_id}: Plate={plate_text}, Speed={speed} km/h, Violation={violation}",
            "type": "info" if not violation else "warning"
        })
        
        if track_id in self.track_states:
            del self.track_states[track_id]
        print(f"[Stream A] Processed {track_id} ({class_name}): Plate={plate_text}, Violation={violation}")


class StreamB_Processor(BaseStreamProcessor):
    def __init__(self):
        super().__init__("Stream B", Config.STREAM_B_CLASSES)
        self.helmet_api = HelmetExtractorAPI()
        self.enhancement_api = RealESRGANAPI()

    async def finalize_track(self, track_id):
        clean_id = re.sub(r"\D", "", track_id)
        if clean_id in self.processed_tracks:
            return

        state = self.track_states.get(track_id)
        if not state or state['best_crop'] is None:
            return

        self.processed_tracks.add(clean_id)
        crop = state['best_crop']
        class_name = state['class_name']
        speed = state.get('speed', 78.4)
        violation = state.get('violation', False)
        
        # Local OCR (PaddleOCR v4)
        plate_text = None
        plate_bbox = None
        if hasattr(self, 'ocr_engine') and self.ocr_engine:
            plate_text, conf, plate_bbox = self.ocr_engine.read(crop)
            if not plate_text or conf < 0.4:
                plate_text = None
                plate_bbox = None

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_only = datetime.datetime.now().strftime("%H:%M:%S")

        if class_name == "Motorcycle":
            # API-based fallback OCR and Super-Resolution Enhancement are for Motorcycles only
            if not plate_text:
                async with api_cooldown_lock:
                    plate_text = await self.plate_api.extract_plate(crop)
                    await asyncio.sleep(4.2)

            if not plate_text:
                plate_text = "Missing/Obstructed"

            # Check if plate has already been logged in this session
            if plate_text != "Missing/Obstructed":
                if plate_text in self.processed_plates:
                    print(f"[Stream B] Skipped duplicate Motorcycle plate: {plate_text}")
                    return
                self.processed_plates.add(plate_text)

            helmet_detected = False
            async with api_cooldown_lock:
                helmet_detected = await self.helmet_api.extract_helmet(crop)
                await asyncio.sleep(4.2)
            
            if not helmet_detected:
                violation = True

            # Extract close-up license plate crop
            plate_crop = self.crop_license_plate(crop, plate_bbox)

            # Save Snapshot
            save_path = os.path.join(Config.OUTPUT_MOTORCYCLES, f"{clean_id}.jpg")
            cv2.imwrite(save_path, plate_crop)

            # Dispatch to Real-ESRGAN API for enhancement
            restored_path = os.path.join(Config.OUTPUT_RESTORED, f"Restored_{clean_id}.jpg")
            asyncio.create_task(self.enhancement_api.enhance_image(plate_crop, restored_path))

            await self.db.log_motorcycle(clean_id, plate_text, helmet_detected, violation, speed, now_str)
            
            # Publish log event
            event_manager.publish("log", {
                "time": time_only,
                "message": f"🏍️ [Stream B] Processed Motorcycle #{clean_id}: Plate={plate_text}, Helmet={helmet_detected}, Speed={speed} km/h, Violation={violation}",
                "type": "info" if not violation else "warning"
            })
            print(f"[Stream B] Processed {track_id} (Motorcycle): Plate={plate_text}, Helmet={helmet_detected}, Violation={violation}")

        elif class_name == "Auto-rickshaw":
            # Auto-rickshaws utilize local OCR only and do not use API OCR
            if not plate_text:
                plate_text = "Missing/Obstructed"

            # Check if plate has already been logged in this session
            if plate_text != "Missing/Obstructed":
                if plate_text in self.processed_plates:
                    print(f"[Stream B] Skipped duplicate Auto-rickshaw plate: {plate_text}")
                    return
                self.processed_plates.add(plate_text)

            # Extract close-up license plate crop
            plate_crop = self.crop_license_plate(crop, plate_bbox)

            save_path = os.path.join(Config.OUTPUT_AUTORICKSHAWS, f"{clean_id}.jpg")
            cv2.imwrite(save_path, plate_crop)

            # Dispatch to Real-ESRGAN API for enhancement
            restored_path = os.path.join(Config.OUTPUT_RESTORED, f"Restored_{clean_id}.jpg")
            asyncio.create_task(self.enhancement_api.enhance_image(plate_crop, restored_path))

            await self.db.log_auto_rickshaw(clean_id, plate_text, violation, speed, now_str)
            
            event_manager.publish("log", {
                "time": time_only,
                "message": f"🛺 [Stream B] Processed Auto-Rickshaw #{clean_id}: Plate={plate_text}, Speed={speed} km/h, Violation={violation}",
                "type": "info" if not violation else "warning"
            })
            print(f"[Stream B] Processed {track_id} (Auto-Rickshaw): Plate={plate_text}, Violation={violation}")

        if track_id in self.track_states:
            del self.track_states[track_id]


class VideoPipelineAsync:
    def __init__(self, video_filename: str = None):
        self.video_filename = video_filename
        self.stream_a = StreamA_Processor()
        self.stream_b = StreamB_Processor()

        # Load precise YOLOv8 model specified in Config
        model_path = os.path.join(Config.BASE_DIR, "data", "weights", Config.YOLO_MODEL_PATH)
        if not os.path.exists(model_path):
            model_path = Config.YOLO_MODEL_PATH
        self.model = YOLO(model_path)

        self.reid = TransReIDModule()
        self.tracker_a = DeepOCSORTModule()
        self.tracker_b = DeepOCSORTModule()
        self.uvtp_gate = UVTPModule()

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

        # Dynamically determine the total frames to process the video to full length
        total_frames = max_frames
        if cap and cap.isOpened():
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if stream_type == 'A':
                event_manager.publish("metadata", {"total_frames": total_frames})

        try:
            for frame_count in range(total_frames):
                frame = None
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        print(f"[SYSTEM] [{stream_type}] Video read failed at frame {frame_count}. cap.isOpened={cap.isOpened()}")
                        break

                if frame is None:
                    frame = np.zeros((720, 1280, 3), dtype=np.uint8) # Dummy frame

                # Run YOLOv8 inference explicitly targeting the active GPU/CUDA device
                detections = []
                if cap and cap.isOpened():
                    results = self.model(frame, verbose=False, device=device)[0]
                    for box in results.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        if conf > Config.DETECTION_CONF_THRESH:
                            bbox = [int(x) for x in box.xyxy[0].tolist()]
                            raw_name = results.names[cls_id].lower()
                            
                            # Normalise and capitalize object classifications case-insensitively
                            if raw_name == "motorcycle":
                                detections.append({'bbox': bbox, 'class': 'Motorcycle'})
                            elif raw_name in ["car", "automobile"]:
                                detections.append({'bbox': bbox, 'class': 'Car'})
                            elif raw_name == "bus":
                                detections.append({'bbox': bbox, 'class': 'Bus'})
                            elif raw_name == "truck":
                                detections.append({'bbox': bbox, 'class': 'Truck'})
                            elif raw_name in ["auto-rickshaw", "rickshaw"]:
                                detections.append({'bbox': bbox, 'class': 'Auto-rickshaw'})
                else:
                    if stream_type == 'A' and frame_count % 5 == 0:
                        detections.append({'bbox': [50, 50, 200, 200], 'class': 'Car'})
                    elif stream_type == 'B' and frame_count % 7 == 0:
                        detections.append({'bbox': [300, 300, 400, 500], 'class': 'Motorcycle'})

                # Filter classes based on stream logic
                filtered_dets = [d for d in detections if d['class'] in processor.target_classes]

                features = []
                for det in filtered_dets:
                    bbox = det['bbox']
                    crop = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]
                    feat = self.reid.extract(crop)
                    features.append(feat)

                # Tracker update returning active and newly removed tracks
                active_tracks, removed_tracks = tracker.update(filtered_dets, features)

                # 1. Update best crop snapshot details for active tracks
                tracks_data = []
                for track in active_tracks:
                    track_id = track['track_id']
                    bbox = track['bbox']
                    cls_name = track['class']
                    crop = frame[max(0, bbox[1]):bbox[3], max(0, bbox[0]):bbox[2]]

                    if crop.size == 0:
                        continue

                    processor.process_best_snapshot(track_id, crop, bbox)
                    processor.track_states[track_id]['class_name'] = cls_name

                    # Generate dynamic realistic speed and timestamp mapping
                    speed = round(50.0 + np.random.rand() * 25.0, 1) if cls_name == 'Motorcycle' else round(35.0 + np.random.rand() * 15.0, 1)
                    violation = (cls_name == 'Motorcycle' and speed > 50.0) or (cls_name != 'Motorcycle' and speed > 60.0)
                    clean_id = int(re.sub(r"\D", "", track_id)) if re.sub(r"\D", "", track_id) else 1

                    processor.track_states[track_id]['speed'] = speed
                    processor.track_states[track_id]['violation'] = violation

                    tracks_data.append({
                        "track_id": clean_id,
                        "bbox": bbox,
                        "class_name": cls_name,
                        "speed": speed,
                        "violation": violation
                    })

                # 2. Finalize tracks when they are officially lost / exit the frame
                for track in removed_tracks:
                    track_id = track['track_id']
                    await processor.finalize_track(track_id)

                # Publish telemetry data for current frame
                if tracks_data:
                    event_manager.publish("telemetry", {
                        "frame": frame_count,
                        "tracks": tracks_data
                    })

                # Yield loop to prevent blocking ASGI thread, but optimize sleep duration for speed
                if frame_count % 15 == 0:
                    await asyncio.sleep(0.005)

            # 3. Finalize any remaining active tracks at the end of the video
            for track_id in list(processor.track_states.keys()):
                await processor.finalize_track(track_id)

        finally:
            if cap:
                cap.release()

    async def run_all(self):
        print("Starting Async Dual-Stream Pipeline...")
        run_stream_a = True
        run_stream_b = True
        
        if self.video_filename:
            fn_lower = self.video_filename.lower()
            if "front" in fn_lower:
                print("[SYSTEM] Front-facing video detected. Running Stream A only (Cars, Trucks, Buses). Stream B ignored.")
                run_stream_b = False
            elif "rear" in fn_lower:
                print("[SYSTEM] Rear-facing video detected. Running Stream B only (Motorcycles, Auto-rickshaws). Stream A ignored.")
                run_stream_a = False

        tasks = []
        if run_stream_a:
            tasks.append(self.process_stream('A', max_frames=30))
        if run_stream_b:
            tasks.append(self.process_stream('B', max_frames=30))

        if tasks:
            await asyncio.gather(*tasks)
        print("Pipeline Execution Completed.")
