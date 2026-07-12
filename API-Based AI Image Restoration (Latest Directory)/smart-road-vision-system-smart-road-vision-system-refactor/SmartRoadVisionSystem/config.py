# Configuration settings for Smart Road Vision System

class Config:
    # --- Paths ---
    WEIGHTS_DIR = "data/weights"
    OUTPUT_DIR = "output"

    # --- Object Detection (YOLOv11) ---
    YOLO_MODEL_PATH = f"{WEIGHTS_DIR}/yolov11_custom.pt"
    VEHICLE_CLASSES = [2, 3, 5, 7] # COCO: car, motorcycle, bus, truck. (Adjust if using custom YOLOv11)
    DETECTION_CONF_THRESH = 0.4

    # --- ReID (TransReID) ---
    TRANSREID_MODEL_PATH = f"{WEIGHTS_DIR}/transreid_vit_base.pth"
    TRANSREID_INPUT_SIZE = (256, 256)

    # --- DeepOCSORT Tracking ---
    TRACK_MAX_AGE = 30
    TRACK_MIN_HITS = 3
    IOU_THRESHOLD = 0.3

    # --- ANPR ---
    N_FRAME_BUFFER = 7
    ANPR_CONF_THRESH = 0.85

    # --- Camera & System ---
    CAMERA_ID = "CAM_KHI_01"
