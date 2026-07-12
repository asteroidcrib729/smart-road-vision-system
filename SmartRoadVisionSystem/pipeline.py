import cv2
import numpy as np
import asyncio
import os

from config import Config
from models.transreid import TransReIDExtractor
from core.tracker import DeepOCSORT
from core.uvtp import UVTPGate, EvidenceBuffer, OutputDispatcher
from subtasks.anpr import ANPRProcessor
from subtasks.helmet import HelmetDetector
from utils.db_handler import DatabaseHandler
from utils.math_utils import calculate_laplacian_variance, calculate_bbox_area, SpeedEstimator
from subtasks.api_fallbacks.extract_helmets import HelmetExtractorAPI
from subtasks.api_fallbacks.extract_numberplates import NumberplateExtractorAPI
from subtasks.api_fallbacks.enhanced_image_generation import RealESRGANAPI

# Dummy placeholders for TransReID and DeepOCSORT tracking logic.
# In a real environment, you'd import `from models.transreid import TransReIDExtractor` and `from core.tracker import DeepOCSORT`









class BaseStreamProcessor:
    def __init__(self, stream_name, target_classes):
        self.stream_name = stream_name
        self.target_classes = target_classes
        self.db = DatabaseHandler()
        self.speed_estimator = SpeedEstimator(Config.SRC_POINTS, Config.DST_POINTS)

        self.plate_api = NumberplateExtractorAPI()

        # Instantiate your local high-performance processing modules
        self.ocr_engine = ANPRProcessor(buffer_size=Config.N_FRAME_BUFFER)

        self.uvtp_gate = UVTPGate(anpr_conf_thresh=Config.ANPR_CONF_THRESH)
        self.evidence_buffer = EvidenceBuffer()
        self.output_dispatcher = OutputDispatcher(Config.OUTPUT_DIR)

        # Track State Buffer: store best crop heuristics and info: store best crop heuristics and info
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
                'class_name': None,
                'speed': 0.0,
                'plate_text': None,
                'plate_conf': 0.0,
                'has_helmet': True,
                'violation': False
            }
        # Utilize central Evidence Buffer for state heuristic resolution
        self.evidence_buffer.update(track_id, crop, bbox, conf=1.0) # conf proxy
        state = self.track_states[track_id]
        state['best_crop'] = self.evidence_buffer.get_best_crop(track_id)

    async def finalize_track(self, track_id):
        # Must be implemented by subclasses
        pass

class StreamA_Processor(BaseStreamProcessor):
    def __init__(self):
        super().__init__("Stream A", Config.STREAM_A_CLASSES)

    async def finalize_track(self, track_id):
        state = self.track_states.get(track_id)
        if not state or state['best_crop'] is None:
            return

        crop = state['best_crop']

        # Tier 1 & 2: Plate Extraction (using API Fallback directly here for simulation)
        # Tier 1: Local Detection (N-Frame Voting Buffer via ANPRProcessor)
        plate_text = state.get('plate_text')

        if not plate_text:
            # Tier 2: API Fallback
            plate_text = await self.plate_api.extract_plate(crop)
            if plate_text:
                state['plate_text'] = plate_text
                state['plate_conf'] = 0.99  # API Override confidence



        # Tier 3: Final State
        if not plate_text:
            plate_text = "Missing/Obstructed"
            violation = True
        else:
            violation = False # Add speeding logic if desired: state['speed'] > Config.SPEED_LIMIT_KMH

        state['plate_text'] = plate_text
        state['violation'] = violation

        # Dispatch output payload
        is_uvtp = self.uvtp_gate.evaluate(state)
        self.output_dispatcher.dispatch(track_id, state, crop, is_uvtp)

        # Save to DB
        await self.db.log_large_vehicle(track_id, plate_text, violation)

        # Free memory locks explicitly
        self.evidence_buffer.clear(track_id)
        if hasattr(self, 'anpr_processor'): self.anpr_processor.clear_buffer(track_id)
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

        # Tier 1: Local Detection (N-Frame Voting Buffer via ANPRProcessor)
        plate_text = state.get('plate_text')

        if not plate_text:
            # Tier 2: API Fallback
            plate_text = await self.plate_api.extract_plate(crop)
            if plate_text:
                state['plate_text'] = plate_text
                state['plate_conf'] = 0.99  # API Override confidence


        if not plate_text:
            plate_text = "Missing/Obstructed"

        violation = (plate_text == "Missing/Obstructed")

        if class_name == "Motorcycle":
            helmet_detected = await self.helmet_api.extract_helmet(crop)
            if not helmet_detected:
                violation = True
            state['plate_text'] = plate_text
            state['has_helmet'] = helmet_detected if helmet_detected is not None else False
            state['violation'] = violation

            is_uvtp = self.uvtp_gate.evaluate(state)
            self.output_dispatcher.dispatch(track_id, state, crop, is_uvtp)

            # Dispatch to Real-ESRGAN API
            restored_path = os.path.join(Config.OUTPUT_RESTORED, f"Restored_{track_id}.jpg")
            asyncio.create_task(self.enhancement_api.enhance_image(crop, restored_path))

            await self.db.log_motorcycle(track_id, plate_text, helmet_detected, violation)
            print(f"[Stream B] Processed {track_id} (Motorcycle): Plate={plate_text}, Helmet={helmet_detected}, Violation={violation}")

        elif class_name == "Auto-rickshaw":
            state['plate_text'] = plate_text
            state['violation'] = violation

            is_uvtp = self.uvtp_gate.evaluate(state)
            self.output_dispatcher.dispatch(track_id, state, crop, is_uvtp)

            await self.db.log_auto_rickshaw(track_id, plate_text, violation)
            print(f"[Stream B] Processed {track_id} (Auto-Rickshaw): Plate={plate_text}, Violation={violation}")

        # Free memory locks explicitly
        self.evidence_buffer.clear(track_id)
        if hasattr(self, 'anpr_processor'): self.anpr_processor.clear_buffer(track_id)
        del self.track_states[track_id]


class VideoPipelineAsync:
    def __init__(self):
        self.stream_a = StreamA_Processor()
        self.stream_b = StreamB_Processor()

        self.reid = TransReIDExtractor(Config.TRANSREID_MODEL_PATH)
        self.tracker_a = DeepOCSORT(max_age=Config.TRACK_MAX_AGE, min_hits=Config.TRACK_MIN_HITS, iou_threshold=Config.IOU_THRESHOLD)
        self.tracker_b = DeepOCSORT(max_age=Config.TRACK_MAX_AGE, min_hits=Config.TRACK_MIN_HITS, iou_threshold=Config.IOU_THRESHOLD)

        # Initialize UVTP Gate to finalize spatial-temporal state violations
        self.uvtp_gate = UVTPGate(anpr_conf_thresh=Config.ANPR_CONF_THRESH)

    def dummy_detect(self, frame_count, stream_type):
        # Simulate detections for test
        detections = []
        if stream_type == 'A' and frame_count % 5 == 0:
            detections.append({'bbox': [50, 50, 200, 200], 'class': 'Car'})
        elif stream_type == 'B' and frame_count % 7 == 0:
            detections.append({'bbox': [300, 300, 400, 500], 'class': 'Motorcycle'})
        return detections

    async def process_stream(self, stream_type, max_frames=20):
        processor = self.stream_a if stream_type == 'A' else self.stream_b
        tracker = self.tracker_a if stream_type == 'A' else self.tracker_b

        frame = np.zeros((720, 1280, 3), dtype=np.uint8) # Dummy frame

        for frame_count in range(max_frames):
            detections = self.dummy_detect(frame_count, stream_type)

            # Filter classes based on stream logic
            filtered_dets = [d for d in detections if d['class'] in processor.target_classes]

            features = []
            for det in filtered_dets:
                bbox = det['bbox']
                crop = frame[max(0, int(bbox[1])):min(frame.shape[0], int(bbox[3])), max(0, int(bbox[0])):min(frame.shape[1], int(bbox[2]))]
                feat = self.reid.extract(crop)
                features.append(feat)

            # TransReID + DeepOCSORT (Simulated)
            active_tracks, removed_tracks = tracker.update(filtered_dets, features)

            # Step 1: Accumulate temporal evidence for active tracks
            for track in active_tracks:
                if not track['active']: continue
                track_id = track['track_id']
                bbox = track['bbox']
                cls_name = track['class']

                # Secure upper bounds during crop slicing (Addresses Flaw 9)
                crop = frame[max(0, int(bbox[1])):min(frame.shape[0], int(bbox[3])),
                             max(0, int(bbox[0])):min(frame.shape[1], int(bbox[2]))]
                if crop.size == 0: continue

                processor.process_best_snapshot(track_id, crop, bbox)
                processor.track_states[track_id]['class_name'] = cls_name

                # Utilize ANPR voting buffer while the vehicle is actively tracked
                if hasattr(processor, 'ocr_engine') and processor.ocr_engine:
                    plate_text, p_conf = processor.ocr_engine.process(track_id, crop)
                    if plate_text:
                        processor.track_states[track_id]['plate_text'] = plate_text
                        processor.track_states[track_id]['plate_conf'] = p_conf

            # Step 2: Only finalize lifecycle events when targets exit the frame boundaries
            for dead_track in removed_tracks:
                await processor.finalize_track(dead_track.track_id)

            await asyncio.sleep(0.01) # Simulate processing time and yield loop

    async def run_all(self):
        print("Starting Async Dual-Stream Pipeline...")
        await asyncio.gather(
            self.process_stream('A', max_frames=30),
            self.process_stream('B', max_frames=30)
        )

        # Flush remaining tracks at end of stream to prevent memory leak
        for track in self.tracker_a.tracks:
            if track.track_id in self.stream_a.track_states:
                await self.stream_a.finalize_track(track.track_id)
        for track in self.tracker_b.tracks:
            if track.track_id in self.stream_b.track_states:
                await self.stream_b.finalize_track(track.track_id)

        print("Pipeline Execution Completed.")
