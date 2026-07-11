# Configuration settings for Smart Road Vision System (V4 Backend Plan)
import os

class Config:
    # --- Paths ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    WEIGHTS_DIR = os.path.join(BASE_DIR, "data", "weights")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    DB_PATH = os.path.join(OUTPUT_DIR, "srvs_database.db")

    # Subdirectories for Image Storage
    OUTPUT_LARGE_VEHICLES = os.path.join(OUTPUT_DIR, "Large_Vehicles")
    OUTPUT_MOTORCYCLES = os.path.join(OUTPUT_DIR, "Motorcycles")
    OUTPUT_AUTORICKSHAWS = os.path.join(OUTPUT_DIR, "Auto_Rickshaws")
    OUTPUT_RESTORED = os.path.join(OUTPUT_DIR, "Restored_Dashboards")

    # --- Object Detection (YOLOv8-OIV7) ---
    YOLO_MODEL_PATH = "yolov8s-oiv7.pt"
    # Open Images V7 Classes (Estimates: Need to map exactly or filter dynamically. Usually Cars, Trucks, Buses, Motorcycles)
    # Using generalized string names instead of raw IDs for Ultralytics OIV7 to be safe.
    STREAM_A_CLASSES = ["Car", "Truck", "Bus"]
    STREAM_B_CLASSES = ["Motorcycle", "Auto-rickshaw"]
    DETECTION_CONF_THRESH = 0.4

    # --- ReID (TransReID) ---
    TRANSREID_MODEL_PATH = os.path.join(WEIGHTS_DIR, "transreid_vit_base.pth")
    TRANSREID_INPUT_SIZE = (256, 256)

    # --- DeepOCSORT Tracking ---
    TRACK_MAX_AGE = 30
    TRACK_MIN_HITS = 3
    IOU_THRESHOLD = 0.3

    # --- ANPR & Subtasks ---
    N_FRAME_BUFFER = 7
    ANPR_CONF_THRESH = 0.85

    # --- Speed & Physical Mapping ---
    # Placeholder Homography Matrix Reference Points
    SRC_POINTS = [(0, 0), (100, 0), (100, 100), (0, 100)]
    DST_POINTS = [(0, 0), (10, 0), (10, 10), (0, 10)] # Mapping to meters
    SPEED_LIMIT_KMH = 60.0

    # --- Camera & System ---
    CAMERA_ID = "CAM_KHI_01"
