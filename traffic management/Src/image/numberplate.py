"""
=============================================================================
  TRAFFIC VISION  v2.0  —  NUMBER PLATE DETECTION MODULE
  Vehicle Detection · ANPR (PaddleOCR)
  ─────────────────────────────────────────────────────────────────
  INPUT   : Single image file
  OUTPUT  : Annotated image · plate crops · CSV log · JSON report
=============================================================================
"""

# ── stdlib ────────────────────────────────────────────────────────────────
import csv
import json
import re
import sys
import time
import warnings
from difflib import SequenceMatcher
from pathlib import Path

# ── third-party ───────────────────────────────────────────────────────────
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    sys.exit("[FATAL] ultralytics not installed.  pip install ultralytics")

try:
    from paddleocr import PaddleOCR
    _PADDLE_OK = True
except ImportError:
    _PADDLE_OK = False
    warnings.warn("[WARN] PaddleOCR not installed — OCR disabled.")


# =============================================================================
#  USER CONFIGURATION
# =============================================================================

VEHICLE_MODEL_PATH = "yolo11n.pt"
PLATE_MODEL_PATH   = r"C:\Users\asadr\Downloads\traffic management\models\numberplate\best.pt"
INPUT_PATH         = r"C:\Users\asadr\Downloads\traffic management\input\image\numberplate\image5.jpg"
# ── class mappings ─────────────────────────────────────────────────────────
COCO_LABELS       = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VEHICLE_CLASS_IDS = set(COCO_LABELS.keys())
BIKE_CLASS_IDS    = {1, 3}          # bicycle + motorcycle

# ── detection thresholds ───────────────────────────────────────────────────
VEHICLE_CONF = 0.35
PLATE_CONF   = 0.25
IOU_THRESH   = 0.45

# ── plate filtering ────────────────────────────────────────────────────────
MIN_PLATE_W          = 50
MIN_PLATE_H          = 15
MIN_PLATE_TEXT_LEN   = 3
MAX_PLATE_TEXT_LEN   = 12
PLATE_BOX_IOU_THRESH = 0.30
PLATE_FUZZY_THRESH   = 0.80

# ── OCR ───────────────────────────────────────────────────────────────────
OCR_MIN_CONF  = 0.35
OCR_UPSCALE_H = 64

# ── confidence fusion weights ─────────────────────────────────────────────
W_DET = 0.6
W_OCR = 0.4

# ── misc ───────────────────────────────────────────────────────────────────
SHOW_PREVIEW = True
FONT         = cv2.FONT_HERSHEY_SIMPLEX


# =============================================================================
#  OUTPUT FOLDERS
# =============================================================================

OUTPUT_DIR      = Path(r"C:\Users\asadr\Downloads\traffic management\output\image\numberplate")
ANNOTATED_DIR   = OUTPUT_DIR / "annotated"
PLATE_CROPS_DIR = OUTPUT_DIR / "plate_crops"
PLATE_LOG       = OUTPUT_DIR / "plate_log.csv"
JSON_REPORT     = OUTPUT_DIR / "report.json"

for _d in [ANNOTATED_DIR, PLATE_CROPS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# =============================================================================
#  GEOMETRY HELPERS
# =============================================================================

def iou(a, b) -> float:
    """Intersection-over-Union for two [x1,y1,x2,y2] boxes."""
    ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union else 0.0


def centre(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def dist(a, b):
    ca, cb = centre(a), centre(b)
    return ((ca[0]-cb[0])**2 + (ca[1]-cb[1])**2) ** 0.5


def safe_crop(frame, x1, y1, x2, y2, pad=0):
    """Crop with boundary clamping; returns None if degenerate."""
    H, W = frame.shape[:2]
    x1 = max(0, int(x1) - pad); y1 = max(0, int(y1) - pad)
    x2 = min(W, int(x2) + pad); y2 = min(H, int(y2) + pad)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2].copy()


# =============================================================================
#  PLATE-TO-VEHICLE ASSIGNMENT
# =============================================================================

def assign_plate(plate_box, vehicles):
    """
    Priority:
      1. Plate centre is inside vehicle box AND in lower 60 % of vehicle
         (plates are never on a car's roof).
      2. Plate centre is inside any vehicle box.
      3. Nearest vehicle by centre distance.
    """
    px, py = centre(plate_box)

    # Priority-1: inside + lower region
    for v in vehicles:
        vx1, vy1, vx2, vy2 = v["box"]
        lower_threshold = vy1 + 0.4 * (vy2 - vy1)
        if vx1 <= px <= vx2 and lower_threshold <= py <= vy2:
            return v

    # Priority-2: anywhere inside
    for v in vehicles:
        vx1, vy1, vx2, vy2 = v["box"]
        if vx1 <= px <= vx2 and vy1 <= py <= vy2:
            return v

    # Priority-3: nearest
    if vehicles:
        return min(vehicles, key=lambda v: dist(plate_box, v["box"]))
    return None


# =============================================================================
#  DUPLICATE REGISTRY
# =============================================================================

class PlateRegistry:
    def __init__(self):
        self.entries = []
        self._count  = 0

    def is_duplicate(self, box, text: str) -> bool:
        for e in self.entries:
            if iou(box, e["box"]) >= PLATE_BOX_IOU_THRESH:
                return True
            if text and e["text"] and (
                text == e["text"]
                or SequenceMatcher(None, text, e["text"]).ratio() >= PLATE_FUZZY_THRESH
            ):
                return True
        return False

    def add(self, box, text, det_conf, ocr_conf, vid, vtype) -> dict:
        self._count += 1
        fused = round(W_DET * det_conf + W_OCR * ocr_conf, 4)
        entry = {
            "pid":      f"P{self._count:03d}",
            "box":      box,
            "text":     text,
            "det_conf": det_conf,
            "ocr_conf": ocr_conf,
            "fused":    fused,
            "vid":      vid,
            "vtype":    vtype,
        }
        self.entries.append(entry)
        return entry

    def __len__(self):
        return self._count


# =============================================================================
#  DRAWING HELPERS
# =============================================================================

def _label_rect(frame, x1, y1, x2, text, color, font_scale=0.52, thickness=2):
    """Draw filled label band above (or below) a box."""
    (tw, th), base = cv2.getTextSize(text, FONT, font_scale, thickness)
    ty = y1 - th - base - 4 if y1 > th + 10 else y1 - th - base - 4
    ty = max(th + base + 4, ty)
    cv2.rectangle(frame, (x1, ty - th - base - 2), (x1 + tw + 6, ty + 2), color, cv2.FILLED)
    cv2.putText(frame, text, (x1 + 3, ty - base), FONT, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)


def draw_box(frame, x1, y1, x2, y2, text, color, thickness=2):
    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    _label_rect(frame, x1, y1, x2, text, color)


# =============================================================================
#  OCR ENGINE
# =============================================================================

class OCREngine:
    def __init__(self):
        self._ocr = None
        if not _PADDLE_OK:
            return
        try:
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                use_gpu=False,
                show_log=False,
                det_db_thresh=0.25,
                det_db_box_thresh=0.35,
                rec_algorithm="CRNN",
                use_space_char=False,
            )
            print("[INFO] PaddleOCR ready.")
        except Exception as exc:
            warnings.warn(f"[WARN] PaddleOCR init failed: {exc}")

    @staticmethod
    def _preprocess(crop: np.ndarray) -> np.ndarray:
        """Resize → CLAHE → sharpen (single pass)."""
        h, w = crop.shape[:2]
        if h < OCR_UPSCALE_H:
            scale = OCR_UPSCALE_H / h
            crop  = cv2.resize(crop, (max(1, int(w * scale)), OCR_UPSCALE_H),
                               interpolation=cv2.INTER_CUBIC)
        # CLAHE in LAB
        lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
        l, a, b_ch = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4)).apply(l)
        crop = cv2.cvtColor(cv2.merge([l, a, b_ch]), cv2.COLOR_LAB2BGR)
        # unsharp mask
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(crop, -1, kernel)

    @staticmethod
    def _clean(raw: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", raw.upper().strip())

    def read(self, crop_bgr: np.ndarray) -> tuple[str, float]:
        """
        Returns (cleaned_text, ocr_confidence).
        Text is "" and conf is 0.0 on any failure.
        """
        if self._ocr is None or crop_bgr is None or crop_bgr.size == 0:
            return "", 0.0

        processed = self._preprocess(crop_bgr.copy())

        try:
            raw = self._ocr.ocr(processed, cls=True)
        except Exception as exc:
            warnings.warn(f"[WARN] OCR exception: {exc}")
            return "", 0.0

        if not raw or raw[0] is None:
            return "", 0.0

        # Multi-line: sort lines by top-Y coordinate then merge
        lines = []
        for line in raw[0]:
            if not line or len(line) < 2:
                continue
            box_pts, (text, conf) = line[0], line[1]
            if conf < OCR_MIN_CONF:
                continue
            top_y = min(pt[1] for pt in box_pts)
            lines.append((top_y, text, conf))

        if not lines:
            return "", 0.0

        lines.sort(key=lambda x: x[0])
        combined_text = self._clean(" ".join(t for _, t, _ in lines))
        avg_conf      = float(np.mean([c for _, _, c in lines]))

        if len(combined_text) < MIN_PLATE_TEXT_LEN:
            return "", 0.0
        if len(combined_text) > MAX_PLATE_TEXT_LEN:
            combined_text = combined_text[:MAX_PLATE_TEXT_LEN]

        return combined_text, avg_conf


# =============================================================================
#  MODEL LOADING
# =============================================================================

def load_models():
    if not Path(PLATE_MODEL_PATH).exists():
        sys.exit(f"[FATAL] Plate model not found:\n  {PLATE_MODEL_PATH}")

    print("[INFO] Loading vehicle model …")
    vm = YOLO(VEHICLE_MODEL_PATH)
    print("[INFO] Loading plate   model …")
    pm = YOLO(PLATE_MODEL_PATH)
    ocr = OCREngine()
    print("[INFO] All models loaded.\n")
    return vm, pm, ocr


# =============================================================================
#  MAIN PIPELINE
# =============================================================================

def run(vm, pm, ocr: OCREngine):
    input_path = Path(INPUT_PATH)
    if not input_path.exists():
        sys.exit(f"[FATAL] Image not found:\n  {INPUT_PATH}")

    frame = cv2.imread(str(input_path))
    if frame is None:
        sys.exit(f"[FATAL] Cannot read image:\n  {INPUT_PATH}")

    H, W = frame.shape[:2]
    print(f"[INFO] Input : {input_path.name}  ({W}×{H})\n")

    canvas    = frame.copy()
    plate_reg = PlateRegistry()
    vehicle_json = {}
    t0        = time.time()

    # ── CSV writer ────────────────────────────────────────────────────────
    plog_f = open(PLATE_LOG, "w", newline="", encoding="utf-8")
    pw     = csv.writer(plog_f)
    pw.writerow(["vehicle_id", "vehicle_type", "plate_id",
                 "plate_number", "det_conf", "ocr_conf", "fused_conf"])

    # ══════════════════════════════════════════════════════════════════════
    # STEP 1 — VEHICLE DETECTION
    # ══════════════════════════════════════════════════════════════════════
    v_res    = vm(frame, conf=VEHICLE_CONF, iou=IOU_THRESH, imgsz=640, verbose=False)
    vehicles = []

    for i, box in enumerate(v_res[0].boxes, 1):
        cls_id = int(box.cls[0])
        if cls_id not in VEHICLE_CLASS_IDS:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        vconf   = float(box.conf[0])
        vid     = f"V{i:02d}"
        vtype   = COCO_LABELS.get(cls_id, "vehicle")
        is_bike = cls_id in BIKE_CLASS_IDS

        vehicles.append({
            "vid": vid, "cls_id": cls_id, "vtype": vtype,
            "is_bike": is_bike, "box": [x1, y1, x2, y2], "conf": vconf,
        })
        vehicle_json[vid] = {
            "vehicle_id":   vid,
            "vehicle_type": vtype,
            "is_bike":      is_bike,
            "plate_number": "UNREADABLE",
            "plate_conf":   0.0,
        }

        color = (0, 165, 255) if is_bike else (180, 180, 180)
        draw_box(canvas, x1, y1, x2, y2,
                 f"{vid} {vtype} ({vconf:.2f})", color)

    print(f"[STEP 1] Vehicles detected : {len(vehicles)}")
    for v in vehicles:
        tag = "  ← BIKE" if v["is_bike"] else ""
        print(f"         {v['vid']}  {v['vtype']}{tag}")
    print()

    # ══════════════════════════════════════════════════════════════════════
    # STEP 2 — PLATE DETECTION + OCR
    # ══════════════════════════════════════════════════════════════════════
    p_res = pm(frame, conf=PLATE_CONF, iou=IOU_THRESH, imgsz=1280, verbose=False)
    print(f"[STEP 2] Raw plate detections : {len(p_res[0].boxes)}")

    for pbox in p_res[0].boxes:
        if int(pbox.cls) != 0:
            continue
        px1, py1, px2, py2 = map(int, pbox.xyxy[0])
        det_conf = float(pbox.conf[0])
        pbbox    = [px1, py1, px2, py2]

        plate_crop = safe_crop(frame, px1, py1, px2, py2)
        if (plate_crop is None
                or plate_crop.shape[0] < MIN_PLATE_H
                or plate_crop.shape[1] < MIN_PLATE_W):
            continue

        text, ocr_conf = ocr.read(plate_crop)
        display_text   = text if text else "UNREADABLE"

        if plate_reg.is_duplicate(pbbox, text):
            continue

        owner = assign_plate(pbbox, vehicles)
        vid   = owner["vid"]   if owner else "NONE"
        vtype = owner["vtype"] if owner else "unknown"

        entry = plate_reg.add(pbbox, display_text, det_conf, ocr_conf, vid, vtype)
        pid   = entry["pid"]

        # save crop
        fname = f"{pid}_{vid}_{display_text}.jpg"
        cv2.imwrite(str(PLATE_CROPS_DIR / fname), plate_crop)
        pw.writerow([vid, vtype, pid, display_text,
                     f"{det_conf:.3f}", f"{ocr_conf:.3f}", f"{entry['fused']:.3f}"])

        print(f"         {pid}  veh={vid}  '{display_text}'  "
              f"det={det_conf:.2f} ocr={ocr_conf:.2f} fused={entry['fused']:.3f}")

        # update JSON
        if vid in vehicle_json and display_text != "UNREADABLE":
            vj = vehicle_json[vid]
            if entry["fused"] > vj["plate_conf"]:
                vj["plate_number"] = display_text
                vj["plate_conf"]   = round(entry["fused"], 4)

        # draw
        draw_box(canvas, px1, py1, px2, py2,
                 f"{pid}: {display_text} ({det_conf:.2f})", (0, 230, 0))

    if len(plate_reg) == 0:
        print("         [WARNING] No plates detected — continuing.\n")
    print()

    plog_f.close()

    # ══════════════════════════════════════════════════════════════════════
    # STEP 3 — SAVE OUTPUTS
    # ══════════════════════════════════════════════════════════════════════

    # JSON report
    report = {
        "image":    str(input_path),
        "vehicles": list(vehicle_json.values()),
        "summary": {
            "total_vehicles": len(vehicles),
            "total_plates":   len(plate_reg),
        },
    }
    with open(JSON_REPORT, "w", encoding="utf-8") as jf:
        json.dump(report, jf, indent=2)

    # Annotated image
    out_img = ANNOTATED_DIR / f"ann_{input_path.stem}{input_path.suffix}"
    cv2.imwrite(str(out_img), canvas)

    # Preview
    if SHOW_PREVIEW:
        cv2.imshow("Traffic Vision v2.0 — Plate Detection  (any key to close)", canvas)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # ══════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    elapsed = time.time() - t0
    sep     = "═" * 65
    print(f"\n{sep}")
    print(f"  DONE in {elapsed:.1f}s")
    print(sep)
    print(f"\n  Vehicles detected    : {len(vehicles)}")
    print(f"  Unique plates found  : {len(plate_reg)}")

    if plate_reg.entries:
        print(f"\n  {'ID':<6}  {'VEH':<5}  {'TYPE':<12}  {'PLATE':<14}  "
              f"{'DET':>5}  {'OCR':>5}  {'FUSED':>5}")
        print(f"  {'─'*60}")
        for e in plate_reg.entries:
            print(f"  {e['pid']:<6}  {e['vid']:<5}  {e['vtype']:<12}  "
                  f"{e['text']:<14}  {e['det_conf']:>5.3f}  "
                  f"{e['ocr_conf']:>5.3f}  {e['fused']:>5.3f}")

    print(f"\n  Annotated image  →  {out_img}")
    print(f"  Plate crops      →  {PLATE_CROPS_DIR}")
    print(f"  Plate CSV        →  {PLATE_LOG}")
    print(f"  JSON report      →  {JSON_REPORT}\n")


# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    vehicle_model, plate_model, ocr_engine = load_models()
    run(vehicle_model, plate_model, ocr_engine)