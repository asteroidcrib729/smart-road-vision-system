import cv2
import numpy as np

from config import Config
from models.transreid import TransReIDExtractor
from core.tracker import DeepOCSORT
from subtasks.helmet import HelmetDetector
from subtasks.anpr import ANPRProcessor
from core.uvtp import UVTPGate, EvidenceBuffer, OutputDispatcher

class VideoPipeline:
    def __init__(self, video_source="0"):
        self.video_source = video_source
        self.cap = cv2.VideoCapture(self.video_source)

        # In a real deployment, load YOLOv11 model here.
        # self.detector = YOLO(Config.YOLO_MODEL_PATH)

        # Initialize Core Components
        self.reid = TransReIDExtractor(Config.TRANSREID_MODEL_PATH)
        self.tracker = DeepOCSORT(max_age=Config.TRACK_MAX_AGE, min_hits=Config.TRACK_MIN_HITS, iou_threshold=Config.IOU_THRESHOLD)
        self.helmet_detector = HelmetDetector()
        self.anpr_processor = ANPRProcessor(buffer_size=Config.N_FRAME_BUFFER)
        self.uvtp_gate = UVTPGate(anpr_conf_thresh=Config.ANPR_CONF_THRESH)
        self.evidence_buffer = EvidenceBuffer()
        self.dispatcher = OutputDispatcher(Config.OUTPUT_DIR)

        # Track persistent states (for sub-task aggregation)
        self.track_states = {}

    def get_dummy_detections(self, frame):
        """
        Generates dummy YOLO detections for testing without model weights.
        Returns format: [{'bbox': [x1,y1,x2,y2], 'conf': float, 'class': int}]
        """
        h, w = frame.shape[:2]
        # Simulate a car moving across the screen
        return [{
            'bbox': [int(w*0.3), int(h*0.3), int(w*0.6), int(h*0.6)],
            'conf': 0.88,
            'class': 2 # Car
        }]

    def process_frame(self, frame):
        # 1. Primary Detection (YOLO)
        # results = self.detector.predict(frame, conf=Config.DETECTION_CONF_THRESH)
        # parse results into `detections`
        detections = self.get_dummy_detections(frame)

        features = []
        for det in detections:
            bbox = det['bbox']
            # 2. Extract Appearance (TransReID)
            crop = frame[bbox[1]:bbox[3], bbox[0]:bbox[2]]
            feat = self.reid.extract(crop)
            features.append(feat)

        # 3. MOT (DeepOCSORT)
        active_tracks, removed_tracks = self.tracker.update(detections, features)

        # 4. Handle Sub-Tasks on Active Tracks
        for track in active_tracks:
            track_id = track['track_id']
            bbox = track['bbox']
            cls_id = track['class']

            crop = frame[max(0, bbox[1]):bbox[3], max(0, bbox[0]):bbox[2]]

            # Update Evidence Buffer
            self.evidence_buffer.update(track_id, crop, bbox, 0.90) # using fixed conf for dummy

            # Initialize track state if new
            if track_id not in self.track_states:
                self.track_states[track_id] = {'class_id': cls_id, 'plate_text': None, 'plate_conf': 0.0, 'has_helmet': True}

            state = self.track_states[track_id]

            # Helmet Detection (Bikes only - assume class 3 is bike)
            if cls_id == 3:
                # Top half crop
                h = crop.shape[0]
                upper_half = crop[0:int(h/2), :]
                has_helmet, hm_conf = self.helmet_detector.detect(upper_half)
                state['has_helmet'] = has_helmet

            # ANPR Pipeline
            plate_text, p_conf = self.anpr_processor.process(track_id, crop)
            if plate_text:
                state['plate_text'] = plate_text
                state['plate_conf'] = p_conf

        # 5. Process Finalized/Exited Tracks
        for r_track in removed_tracks:
            track_id = r_track.track_id
            if track_id in self.track_states:
                state = self.track_states[track_id]

                # Check UVTP condition
                is_uvtp = self.uvtp_gate.evaluate(state)

                # Retrieve Best Crop
                best_crop = self.evidence_buffer.get_best_crop(track_id)

                # Dispatch Event
                self.dispatcher.dispatch(track_id, state, best_crop, is_uvtp)

                # Cleanup
                self.evidence_buffer.clear(track_id)
                self.anpr_processor.clear_buffer(track_id)
                del self.track_states[track_id]

    def run(self):
        print(f"Starting pipeline on source: {self.video_source}")
        frame_count = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            self.process_frame(frame)
            frame_count += 1

            if frame_count > 10: # Run for a few frames for testing
                break

        # Force flush remaining tracks at end of stream
        for track in self.tracker.tracks:
            track_id = track.track_id
            if track_id in self.track_states:
                state = self.track_states[track_id]
                is_uvtp = self.uvtp_gate.evaluate(state)
                best_crop = self.evidence_buffer.get_best_crop(track_id)
                self.dispatcher.dispatch(track_id, state, best_crop, is_uvtp)

        self.cap.release()
        print("Pipeline finished successfully.")

if __name__ == "__main__":
    # Test on a dummy blank image stream
    pipeline = VideoPipeline(video_source=0) # Note: 0 might fail if no webcam. Will test via script.
