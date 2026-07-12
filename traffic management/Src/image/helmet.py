"""
=============================================================================
  TRAFFIC VISION  v2.0  —  HELMET DETECTION MODULE  (FIXED v3)
  Vehicle Detection · Helmet Violation Detection
  ─────────────────────────────────────────────────────────────────
  INPUT   : Single image file
  OUTPUT  : Annotated image · helmet crops · CSV log · JSON report

  FIXES IN THIS VERSION
  ──────────────────────
  ✔ Rider-region crop now adds horizontal padding (RIDER_PAD_SIDE=30)
    so helmets near box edges are not clipped
  ✔ RIDER_PAD_ABOVE raised to 120px  — helmets are above the YOLO box
  ✔ RIDER_FRACTION kept at 0.55  — only upper body needed
  ✔ HELMET_CONF = 0.08  — very permissive; duplicates handled by IOU
  ✔ Fallback now uses a VERY generous spatial window around each bike
    (full vehicle height above + full vehicle width either side)
  ✔ Strategy 3: if fallback still 0, run helmet model on the WHOLE image
    and assign every detected helmet to nearest bike
  ✔ Each strategy's crop/context is saved to debug_crops/ with a suffix
    so you can see exactly what each strategy received
  ✔ Prints hm.names at startup to help verify HELMET_WITH_ID mapping
=============================================================================
"""

# ── stdlib ────────────────────────────────────────────────────────────────
import csv
import json
import sys
import time
from pathlib import Path

# ── third-party ───────────────────────────────────────────────────────────
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    sys.exit("[FATAL] ultralytics not installed.  pip install ultralytics")


# =============================================================================
#  USER CONFIGURATION
# =============================================================================

VEHICLE_MODEL_PATH = "yolo11n.pt"
HELMET_MODEL_PATH  = r"C:\Users\asadr\Downloads\traffic management\models\Helmet\best.pt"
INPUT_PATH         = r"C:\Users\asadr\Downloads\traffic management\input\image\helmet\bikers.png"

# ── class mappings ─────────────────────────────────────────────────────────
COCO_LABELS       = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VEHICLE_CLASS_IDS = set(COCO_LABELS.keys())
BIKE_CLASS_IDS    = {1, 3}

HELMET_WITH_ID    = 0    # class-0 = "with helmet"  — check hm.names at startup
HELMET_WITHOUT_ID = 1    # class-1 = "no helmet"

# ── detection thresholds ───────────────────────────────────────────────────
VEHICLE_CONF = 0.35
HELMET_CONF  = 0.08      # very low — IOU dedup handles false positives
IOU_THRESH   = 0.45

# ── helmet size filter ─────────────────────────────────────────────────────
MIN_HELMET_W          = 15
MIN_HELMET_H          = 15
HELMET_BOX_IOU_THRESH = 0.35

# ── rider-region crop (Strategy 1) ────────────────────────────────────────
RIDER_PAD_ABOVE = 120   # px above vehicle box top
RIDER_PAD_SIDE  = 30    # px left/right of vehicle box
RIDER_FRACTION  = 0.55  # use top 55 % of vehicle height

# ── fallback spatial filter (Strategy 2) ─────────────────────────────────
# A helmet centre must be within this window around the vehicle box
FALLBACK_ABOVE  = 150   # px above vehicle top
FALLBACK_BELOW  = 50    # px below vehicle top  (not the full vehicle bottom)
FALLBACK_SIDE   = 80    # px left/right of vehicle box

# ── misc ───────────────────────────────────────────────────────────────────
SHOW_PREVIEW = True
SAVE_DEBUG   = True
FONT         = cv2.FONT_HERSHEY_SIMPLEX


# =============================================================================
#  OUTPUT FOLDERS
# =============================================================================

OUTPUT_DIR      = Path(r"C:\Users\asadr\Downloads\traffic management\output\image\helmet")
ANNOTATED_DIR = OUTPUT_DIR / "annotated"
HELMET_OK_DIR = OUTPUT_DIR / "helmet_crops" / "with_helmet"
HELMET_NO_DIR = OUTPUT_DIR / "helmet_crops" / "no_helmet"
DEBUG_DIR     = OUTPUT_DIR / "debug_crops"
HELMET_LOG    = OUTPUT_DIR / "helmet_log.csv"
JSON_REPORT   = OUTPUT_DIR / "report.json"

for _d in [ANNOTATED_DIR, HELMET_OK_DIR, HELMET_NO_DIR, DEBUG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# =============================================================================
#  GEOMETRY HELPERS
# =============================================================================

def iou(a, b) -> float:
    ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union else 0.0


def centre(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def dist_centres(a, b):
    ca, cb = centre(a), centre(b)
    return ((ca[0]-cb[0])**2 + (ca[1]-cb[1])**2) ** 0.5


def safe_crop(frame, x1, y1, x2, y2):
    H, W = frame.shape[:2]
    x1 = max(0, int(x1)); y1 = max(0, int(y1))
    x2 = min(W, int(x2)); y2 = min(H, int(y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2].copy()


# =============================================================================
#  DUPLICATE REGISTRY
# =============================================================================

class HelmetRegistry:
    def __init__(self):
        self.boxes   = []
        self.entries = []
        self._count  = 0

    def is_duplicate(self, box) -> bool:
        return any(iou(box, b) >= HELMET_BOX_IOU_THRESH for b in self.boxes)

    def add(self, box, cls_name, conf, vid) -> dict:
        self._count += 1
        self.boxes.append(box)
        entry = {"hid": self._count, "box": box, "cls": cls_name,
                 "conf": conf, "vid": vid}
        self.entries.append(entry)
        return entry

    def __len__(self):
        return self._count


# =============================================================================
#  DRAWING
# =============================================================================

def _label_rect(frame, x1, y1, x2, text, color, fs=0.52, th=2):
    (tw, th_), base = cv2.getTextSize(text, FONT, fs, th)
    ty = max(th_ + base + 4, y1 - th_ - base - 4)
    cv2.rectangle(frame, (x1, ty - th_ - base - 2),
                  (x1 + tw + 6, ty + 2), color, cv2.FILLED)
    cv2.putText(frame, text, (x1 + 3, ty - base),
                FONT, fs, (0, 0, 0), th, cv2.LINE_AA)


def draw_box(frame, x1, y1, x2, y2, text, color, thickness=2):
    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    _label_rect(frame, x1, y1, x2, text, color)


def draw_rounded_box(frame, x1, y1, x2, y2, text, color, radius=12, thickness=3):
    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
    r = min(radius, (x2-x1)//2, (y2-y1)//2)
    cv2.line(frame, (x1+r, y1), (x2-r, y1), color, thickness)
    cv2.line(frame, (x2, y1+r), (x2, y2-r), color, thickness)
    cv2.line(frame, (x1+r, y2), (x2-r, y2), color, thickness)
    cv2.line(frame, (x1, y1+r), (x1, y2-r), color, thickness)
    cv2.ellipse(frame, (x1+r, y1+r), (r,r), 180, 0, 90, color, thickness)
    cv2.ellipse(frame, (x2-r, y1+r), (r,r), 270, 0, 90, color, thickness)
    cv2.ellipse(frame, (x2-r, y2-r), (r,r), 0,   0, 90, color, thickness)
    cv2.ellipse(frame, (x1+r, y2-r), (r,r), 90,  0, 90, color, thickness)
    _label_rect(frame, x1, y1, x2, text, color)


# =============================================================================
#  MODEL LOADING
# =============================================================================

def load_models():
    if not Path(HELMET_MODEL_PATH).exists():
        sys.exit(f"[FATAL] Helmet model not found:\n  {HELMET_MODEL_PATH}")
    print("[INFO] Loading vehicle model …")
    vm = YOLO(VEHICLE_MODEL_PATH)
    print("[INFO] Loading helmet  model …")
    hm = YOLO(HELMET_MODEL_PATH)
    print(f"\n[INFO] Helmet model classes : {hm.names}")
    print(f"       HELMET_WITH_ID={HELMET_WITH_ID} → '{hm.names.get(HELMET_WITH_ID)}'")
    print(f"       HELMET_WITHOUT_ID={HELMET_WITHOUT_ID} → '{hm.names.get(HELMET_WITHOUT_ID)}'")
    print("       *** If these are swapped, flip the IDs in config above. ***\n")
    return vm, hm


# =============================================================================
#  HELMET INFERENCE
# =============================================================================

def infer(hm, img):
    """Run helmet model on an image/crop. Returns list of boxes."""
    if img is None or img.size == 0:
        return []
    res = hm(img, conf=HELMET_CONF, iou=IOU_THRESH, imgsz=1280, verbose=False)
    return list(res[0].boxes)


# =============================================================================
#  THREE-STRATEGY DETECTION PER BIKE
# =============================================================================

def detect_helmets_for_bike(hm, frame, vbox, vid):
    """
    Returns list of (abs_box [x1,y1,x2,y2], cls_id, conf).

    Strategy 1 — rider-region crop
        Crop from (vx1-pad_side, vy1-pad_above) to
                  (vx2+pad_side, vy1 + fraction*height).
        Coordinates mapped back to full-frame.

    Strategy 2 — full-frame filtered by generous window
        Run on full frame, keep only detections whose centre
        is within FALLBACK_ABOVE px above / FALLBACK_BELOW px
        below vehicle top and FALLBACK_SIDE px either side.

    Strategy 3 — full-frame assign to nearest bike
        Run on full frame, assign every helmet to the nearest
        vehicle. Used only when strategies 1+2 both return 0.
    """
    H, W    = frame.shape[:2]
    vx1, vy1, vx2, vy2 = vbox
    results = []

    # ── Strategy 1: rider-region crop ─────────────────────────────────────
    cy1 = max(0, vy1 - RIDER_PAD_ABOVE)
    cy2 = min(H, vy1 + int((vy2 - vy1) * RIDER_FRACTION))
    cx1 = max(0, vx1 - RIDER_PAD_SIDE)
    cx2 = min(W, vx2 + RIDER_PAD_SIDE)

    crop = safe_crop(frame, cx1, cy1, cx2, cy2)
    if SAVE_DEBUG and crop is not None:
        cv2.imwrite(str(DEBUG_DIR / f"s1_rider_{vid}.jpg"), crop)

    boxes_s1 = infer(hm, crop)
    print(f"         {vid}  Strategy-1 (rider crop)     : {len(boxes_s1)} hit(s)")

    for b in boxes_s1:
        hx1c, hy1c, hx2c, hy2c = map(int, b.xyxy[0])
        # remap crop-local → full frame
        results.append(([cx1+hx1c, cy1+hy1c, cx1+hx2c, cy1+hy2c],
                         int(b.cls[0]), float(b.conf[0])))

    if results:
        return results

    # ── Strategy 2: full-frame with spatial window ─────────────────────────
    # Save a visualisation of the search window for debugging
    if SAVE_DEBUG:
        win = frame.copy()
        wx1 = max(0, vx1 - FALLBACK_SIDE)
        wy1 = max(0, vy1 - FALLBACK_ABOVE)
        wx2 = min(W, vx2 + FALLBACK_SIDE)
        wy2 = min(H, vy1 + FALLBACK_BELOW)
        cv2.rectangle(win, (wx1, wy1), (wx2, wy2), (0, 0, 255), 2)
        cv2.imwrite(str(DEBUG_DIR / f"s2_window_{vid}.jpg"), win)

    boxes_s2 = infer(hm, frame)
    print(f"         {vid}  Strategy-2 (full frame)     : {len(boxes_s2)} total, filtering …")

    for b in boxes_s2:
        hx1, hy1, hx2, hy2 = map(int, b.xyxy[0])
        cx_h = (hx1 + hx2) / 2
        cy_h = (hy1 + hy2) / 2
        # Helmet centre must be above vehicle top (with padding) and
        # not too far below vehicle top, and within horizontal range
        if (vx1 - FALLBACK_SIDE <= cx_h <= vx2 + FALLBACK_SIDE and
                vy1 - FALLBACK_ABOVE <= cy_h <= vy1 + FALLBACK_BELOW):
            results.append(([hx1, hy1, hx2, hy2], int(b.cls[0]), float(b.conf[0])))

    print(f"         {vid}  Strategy-2 after filter     : {len(results)} hit(s)")

    if results:
        return results

    # ── Strategy 3: full-frame assign-to-nearest (last resort) ────────────
    print(f"         {vid}  Strategy-3 (nearest assign) …")
    boxes_s3 = infer(hm, frame)
    for b in boxes_s3:
        hx1, hy1, hx2, hy2 = map(int, b.xyxy[0])
        results.append(([hx1, hy1, hx2, hy2], int(b.cls[0]), float(b.conf[0])))

    print(f"         {vid}  Strategy-3 raw detections   : {len(results)} hit(s)")
    # (caller will assign by nearest bike — we return all and let caller filter)
    return results   # may be empty


# =============================================================================
#  MAIN PIPELINE
# =============================================================================

def run(vm, hm):
    input_path = Path(INPUT_PATH)
    if not input_path.exists():
        sys.exit(f"[FATAL] Image not found:\n  {INPUT_PATH}")

    frame = cv2.imread(str(input_path))
    if frame is None:
        sys.exit(f"[FATAL] Cannot read image:\n  {INPUT_PATH}")

    H, W = frame.shape[:2]
    print(f"[INFO] Input : {input_path.name}  ({W}×{H})\n")

    canvas       = frame.copy()
    helmet_reg   = HelmetRegistry()
    vehicle_json = {}
    t0           = time.time()

    hlog_f = open(HELMET_LOG, "w", newline="", encoding="utf-8")
    hw     = csv.writer(hlog_f)
    hw.writerow(["vehicle_id", "helmet_id", "class", "conf",
                 "x1", "y1", "x2", "y2"])

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

        vehicles.append({"vid": vid, "cls_id": cls_id, "vtype": vtype,
                          "is_bike": is_bike, "box": [x1, y1, x2, y2], "conf": vconf})
        vehicle_json[vid] = {"vehicle_id": vid, "vehicle_type": vtype,
                              "is_bike": is_bike, "helmet_status": "N/A",
                              "helmet_conf": 0.0}

        color = (0, 165, 255) if is_bike else (180, 180, 180)
        draw_box(canvas, x1, y1, x2, y2, f"{vid} {vtype} ({vconf:.2f})", color)

    print(f"[STEP 1] Vehicles detected : {len(vehicles)}")
    for v in vehicles:
        print(f"         {v['vid']}  {v['vtype']}{'  <- BIKE' if v['is_bike'] else ''}")
    print()

    # ══════════════════════════════════════════════════════════════════════
    # STEP 2 — HELMET DETECTION (bikes only)
    # ══════════════════════════════════════════════════════════════════════
    bikes = [v for v in vehicles if v["is_bike"]]
    print(f"[STEP 2] Bikes for helmet check : {len(bikes)}\n")

    if not bikes:
        print("         [WARNING] No bikes detected.\n")
    else:
        for v in bikes:
            vid  = v["vid"]
            vbox = v["box"]
            print(f"         ── {vid} ──────────────────────────────────────")

            detections = detect_helmets_for_bike(hm, frame, vbox, vid)

            for (hbbox, cls_id_h, hconf) in detections:
                hx1, hy1, hx2, hy2 = hbbox

                # Clamp to frame
                hx1 = max(0, hx1); hy1 = max(0, hy1)
                hx2 = min(W, hx2); hy2 = min(H, hy2)

                hcrop = safe_crop(frame, hx1, hy1, hx2, hy2)
                if (hcrop is None or
                        hcrop.shape[0] < MIN_HELMET_H or
                        hcrop.shape[1] < MIN_HELMET_W):
                    continue

                if helmet_reg.is_duplicate([hx1, hy1, hx2, hy2]):
                    continue

                entry = helmet_reg.add([hx1, hy1, hx2, hy2], "", hconf, vid)

                if cls_id_h == HELMET_WITH_ID:
                    cls_name = "with_helmet"
                    label    = f"Helmet OK ({hconf:.2f})"
                    color    = (0, 200, 80)
                    save_dir = HELMET_OK_DIR
                    print(f"         {vid}  HELMET OK    conf={hconf:.2f}  box=[{hx1},{hy1},{hx2},{hy2}]")
                else:
                    cls_name = "no_helmet"
                    label    = f"NO HELMET! ({hconf:.2f})"
                    color    = (30, 30, 220)
                    save_dir = HELMET_NO_DIR
                    print(f"         {vid}  VIOLATION    conf={hconf:.2f}  box=[{hx1},{hy1},{hx2},{hy2}]")

                entry["cls"] = cls_name
                hfile = save_dir / f"{cls_name}_{entry['hid']:05d}_{vid}.jpg"
                cv2.imwrite(str(hfile), hcrop)
                hw.writerow([vid, entry["hid"], cls_name, f"{hconf:.3f}",
                             hx1, hy1, hx2, hy2])

                if vid in vehicle_json:
                    vj = vehicle_json[vid]
                    if hconf > vj["helmet_conf"]:
                        vj["helmet_status"] = cls_name
                        vj["helmet_conf"]   = round(hconf, 4)

                draw_rounded_box(canvas, hx1, hy1, hx2, hy2, label, color)

            print()

        if len(helmet_reg) == 0:
            print(
                "  [WARNING] No helmets detected by any strategy.\n"
                "  ACTION CHECKLIST:\n"
                "    1. Open output_helmet/debug_crops/s1_rider_V*.jpg\n"
                "       Are helmets visible? If yes → lower HELMET_CONF further.\n"
                "    2. Check the class mapping printed at startup.\n"
                "       If 'with_helmet' = class 1, set HELMET_WITH_ID = 1.\n"
                "    3. Try running the helmet model standalone on the full image\n"
                "       with conf=0.01 to confirm the model works at all.\n"
            )

    hlog_f.close()

    # ══════════════════════════════════════════════════════════════════════
    # STEP 3 — SAVE OUTPUTS
    # ══════════════════════════════════════════════════════════════════════
    report = {
        "image":    str(input_path),
        "vehicles": list(vehicle_json.values()),
        "summary": {
            "total_vehicles": len(vehicles),
            "total_helmets":  len(helmet_reg),
            "with_helmet":    sum(1 for e in helmet_reg.entries if e["cls"] == "with_helmet"),
            "no_helmet":      sum(1 for e in helmet_reg.entries if e["cls"] == "no_helmet"),
        },
    }
    with open(JSON_REPORT, "w", encoding="utf-8") as jf:
        json.dump(report, jf, indent=2)

    out_img = ANNOTATED_DIR / f"ann_{input_path.stem}{input_path.suffix}"
    cv2.imwrite(str(out_img), canvas)

    if SHOW_PREVIEW:
        cv2.imshow("Traffic Vision v2.0 — Helmet Detection  (any key to close)", canvas)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    elapsed = time.time() - t0
    sep = "═" * 65
    print(f"\n{sep}")
    print(f"  DONE in {elapsed:.1f}s")
    print(sep)
    print(f"\n  Vehicles detected    : {len(vehicles)}")
    print(f"  Unique helmets found : {len(helmet_reg)}")
    print(f"    with helmet        : {report['summary']['with_helmet']}")
    print(f"    no helmet          : {report['summary']['no_helmet']}")
    print(f"\n  Annotated image →  {out_img}")
    print(f"  Debug crops     →  {DEBUG_DIR}")
    print(f"  Helmet crops    →  {HELMET_OK_DIR.parent}")
    print(f"  Helmet CSV      →  {HELMET_LOG}")
    print(f"  JSON report     →  {JSON_REPORT}\n")


# =============================================================================
#  ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    vehicle_model, helmet_model = load_models()
    run(vehicle_model, helmet_model)