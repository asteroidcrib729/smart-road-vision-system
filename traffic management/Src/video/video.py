"""
=============================================================================
  TRAFFIC VISION  –  ANPR  +  Helmet Detection
  ─────────────────────────────────────────────────────────────────
  INPUT     : Video file
  DETECT ONCE ONLY — 3-layer plate dedup, no limits, no restoration

  Plate dedup (3 layers):
    1. Box IoU overlap        (same spatial region)
    2. Exact text match       (identical OCR string)
    3. Fuzzy text similarity  (catches BYM992 vs BYW992 vs BYH992)

  Helmet dedup:
    Box IoU overlap only (each person saved once)

  NO limits / NO restoration / NO tracking / NO duplicates
  ─────────────────────────────────────────────────────────────────
  VERSIONS : PaddlePaddle 2.6.2  |  PaddleOCR 2.7.3
=============================================================================
"""

import cv2
import numpy as np
import time
import re
import csv
from pathlib import Path
from difflib import SequenceMatcher
from ultralytics import YOLO
from paddleocr import PaddleOCR

# ═════════════════════════════════════════════════════════════════════════════
#  USER CONFIG
# ═════════════════════════════════════════════════════════════════════════════

PLATE_MODEL_PATH  = r"C:\Users\asadr\Downloads\traffic management\models\numberplate\best.pt"
HELMET_MODEL_PATH = r"C:\Users\asadr\Downloads\traffic management\models\Helmet\best.pt"
INPUT_PATH        = r"C:\Users\asadr\Downloads\traffic management\input\video\video_1.mp4"

# ── Detection thresholds ──────────────────────────────────────────────────────
PLATE_CONF   = 0.35
HELMET_CONF  = 0.35
IOU_THRESH   = 0.45

MIN_PLATE_W  = 60
MIN_PLATE_H  = 20
MIN_HELMET_W = 30
MIN_HELMET_H = 30

# ── Plate dedup ───────────────────────────────────────────────────────────────
PLATE_BOX_IOU_THRESH = 0.35   # spatial overlap to consider same vehicle
PLATE_FUZZY_THRESH   = 0.80   # text similarity to consider same plate
MIN_PLATE_TEXT_LEN   = 3      # discard OCR results shorter than this

# ── Helmet dedup ──────────────────────────────────────────────────────────────
HELMET_BOX_IOU_THRESH = 0.40

# ── Helmet class IDs — check your model's data.yaml ──────────────────────────
HELMET_CLASS_ID    = 0        # 'with helmet'
NO_HELMET_CLASS_ID = 1        # 'no helmet' / violation

# ── OCR confidence threshold ──────────────────────────────────────────────────
OCR_MIN_CONF = 0.45

# ── Preview ───────────────────────────────────────────────────────────────────
SHOW_PREVIEW  = True
PREVIEW_EVERY = 15

# ═════════════════════════════════════════════════════════════════════════════
#  GROUND TRUTH  ← fill in for accuracy report
# ═════════════════════════════════════════════════════════════════════════════

PLATE_GROUND_TRUTH = [
    # "ABC123",
    # "XYZ789",
]

HELMET_GROUND_TRUTH = {
    "with_helmet": 0,
    "no_helmet":   0,
}

# ═════════════════════════════════════════════════════════════════════════════
#  FOLDERS
# ═════════════════════════════════════════════════════════════════════════════

OUTPUT_DIR      = Path(r"C:\Users\asadr\Downloads\traffic management\output\video")
ANNOTATED_DIR       = OUTPUT_DIR / "annotated"
PLATE_CROPS_DIR     = OUTPUT_DIR / "plate_crops"
HELMET_CROPS_DIR    = OUTPUT_DIR / "helmet_crops"
NO_HELMET_CROPS_DIR = OUTPUT_DIR / "no_helmet_crops"
PLATE_LOG           = OUTPUT_DIR / "plate_log.csv"
HELMET_LOG          = OUTPUT_DIR / "helmet_log.csv"

for d in [OUTPUT_DIR, ANNOTATED_DIR, PLATE_CROPS_DIR,
          HELMET_CROPS_DIR, NO_HELMET_CROPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ═════════════════════════════════════════════════════════════════════════════
#  MODEL LOADING
# ═════════════════════════════════════════════════════════════════════════════

def load_models():
    for label, path in [("Plate model",  PLATE_MODEL_PATH),
                         ("Helmet model", HELMET_MODEL_PATH)]:
        if not Path(path).exists():
            raise FileNotFoundError(f"{label} not found:\n  {path}")

    print("[INFO] Loading plate detection model ...")
    plate_model = YOLO(PLATE_MODEL_PATH)

    print("[INFO] Loading helmet detection model ...")
    helmet_model = YOLO(HELMET_MODEL_PATH)

    print("[INFO] Loading PaddleOCR ...")
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang="en",
        use_gpu=False,
        show_log=False,
        det_db_thresh=0.3,
        det_db_box_thresh=0.4,
        rec_algorithm="CRNN",
        use_space_char=False,
    )
    print("[INFO] All models ready.\n")
    return plate_model, helmet_model, ocr


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def box_iou(a, b):
    ix1 = max(a[0], b[0]);  iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]);  iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    return inter / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter)


def clean_text(raw):
    return re.sub(r"[^A-Z0-9]", "", raw.upper().strip())


def fuzzy_sim(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def draw_label(frame, x1, y1, x2, y2, text, color):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.60, 2)
    ty = y1 - th - base - 4 if y1 > th + 10 else y2 + 4
    cv2.rectangle(frame, (x1, ty), (x1+tw+4, ty+th+base+4), color, cv2.FILLED)
    cv2.putText(frame, text, (x1+2, ty+th+2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 0), 2, cv2.LINE_AA)


# ═════════════════════════════════════════════════════════════════════════════
#  PLATE REGISTRY  — 3-layer dedup
# ═════════════════════════════════════════════════════════════════════════════

class PlateRegistry:
    def __init__(self):
        self.plates = []
        self.count  = 0

    def is_duplicate(self, box, text):
        for p in self.plates:
            if box_iou(box, p["box"]) >= PLATE_BOX_IOU_THRESH:
                return True
            if text and p["text"]:
                if text == p["text"]:
                    return True
                if fuzzy_sim(text, p["text"]) >= PLATE_FUZZY_THRESH:
                    return True
        return False

    def register(self, box, text, conf, frame_idx):
        self.count += 1
        pid = f"P{self.count:03d}"
        self.plates.append(dict(box=box, text=text, conf=conf,
                                frame=frame_idx, pid=pid))
        return pid

    def readable_texts(self):
        return [p["text"] for p in self.plates if p["text"]]


# ═════════════════════════════════════════════════════════════════════════════
#  HELMET REGISTRY  — box IoU dedup
# ═════════════════════════════════════════════════════════════════════════════

class HelmetRegistry:
    def __init__(self):
        self.seen_boxes = []
        self.count      = 0

    def is_duplicate(self, box):
        for seen in self.seen_boxes:
            if box_iou(box, seen) >= HELMET_BOX_IOU_THRESH:
                return True
        return False

    def register(self, box):
        self.seen_boxes.append(box)
        self.count += 1


# ═════════════════════════════════════════════════════════════════════════════
#  OCR  (raw crop — no restoration)
# ═════════════════════════════════════════════════════════════════════════════

def run_ocr(ocr, crop_bgr):
    if crop_bgr is None or crop_bgr.size == 0:
        return ""
    try:
        results = ocr.ocr(crop_bgr, cls=True)
        if not results or results[0] is None:
            return ""
        parts = []
        for line in results[0]:
            if not line or len(line) < 2:
                continue
            text_str = line[1][0]
            conf     = line[1][1]
            if conf >= OCR_MIN_CONF and text_str:
                parts.append(text_str)
        text = clean_text(" ".join(parts))
        return text if len(text) >= MIN_PLATE_TEXT_LEN else ""
    except Exception:
        return ""


# ═════════════════════════════════════════════════════════════════════════════
#  ACCURACY EVALUATION
# ═════════════════════════════════════════════════════════════════════════════

def evaluate_accuracy(plate_reg, helmet_stats):
    sep = "=" * 65
    print(f"\n{sep}")
    print("  ACCURACY REPORT")
    print(sep)

    # ── Plate accuracy ────────────────────────────────────────────────────────
    print("\n  [ PLATE / ANPR ACCURACY ]")
    n          = plate_reg.count
    readable   = len(plate_reg.readable_texts())
    unreadable = n - readable

    print(f"\n  Total unique plates saved : {n}")
    if n:
        print(f"  Readable                  : {readable}  ({readable/n*100:.1f}%)")
        print(f"  Unreadable (blank OCR)    : {unreadable}  ({unreadable/n*100:.1f}%)")

    gt_clean = [clean_text(g) for g in PLATE_GROUND_TRUTH]
    detected = plate_reg.readable_texts()

    if gt_clean and detected:
        exact_hits = 0
        total_sim  = 0.0
        matched_gt = set()
        false_pos  = []

        print(f"\n  {'#':<4}  {'DETECTED':<15}  {'BEST GT MATCH':<15}  {'SIM':>6}  VERDICT")
        print(f"  {'-'*58}")

        for i, pred in enumerate(detected, 1):
            best_gt  = max(gt_clean, key=lambda g: fuzzy_sim(pred, g))
            sim      = fuzzy_sim(pred, best_gt)
            is_exact = (pred == best_gt)
            if is_exact:
                exact_hits += 1
                matched_gt.add(best_gt)
            total_sim += sim
            if sim < 0.5:
                false_pos.append(pred)
            verdict = "✓ EXACT" if is_exact else ("~ CLOSE" if sim >= 0.75 else "✗ WRONG")
            print(f"  {i:<4}  {pred:<15}  {best_gt:<15}  {sim:>5.1%}  {verdict}")

        missed = [g for g in gt_clean if g not in matched_gt]
        nd  = len(detected)
        tp  = exact_hits
        fp  = len(false_pos)
        fn  = len(missed)
        pre = tp/(tp+fp) if (tp+fp) > 0 else 0.0
        rec = tp/(tp+fn) if (tp+fn) > 0 else 0.0
        f1  = 2*pre*rec/(pre+rec) if (pre+rec) > 0 else 0.0

        print(f"\n  Ground truth plates     : {len(gt_clean)}")
        print(f"  Exact matches           : {exact_hits} / {len(gt_clean)}")
        print(f"  Exact match accuracy    : {exact_hits/len(gt_clean)*100:.1f}%")
        print(f"  Avg char similarity     : {total_sim/nd*100:.1f}%")
        if missed:
            print(f"  Missed plates           : {fn}  → {', '.join(missed)}")
        if false_pos:
            print(f"  False positives         : {fp}  → {', '.join(false_pos)}")
        print(f"\n  Precision : {pre:.1%}   Recall : {rec:.1%}   F1 : {f1:.1%}")
    else:
        print("\n  [NOTE] Fill PLATE_GROUND_TRUTH for full accuracy metrics.")
        if detected:
            print(f"  Plates detected: {', '.join(detected)}")

    # ── Helmet accuracy ───────────────────────────────────────────────────────
    print(f"\n  [ HELMET DETECTION ACCURACY ]")
    det_with  = helmet_stats["with_helmet"]
    det_no    = helmet_stats["no_helmet"]
    det_total = det_with + det_no
    gt_with   = HELMET_GROUND_TRUTH["with_helmet"]
    gt_no     = HELMET_GROUND_TRUTH["no_helmet"]
    gt_total  = gt_with + gt_no

    print(f"\n  {'CLASS':<20}  {'DETECTED':>9}  {'GROUND TRUTH':>13}  {'ACCURACY':>9}")
    print(f"  {'-'*56}")
    for label, det, gt in [("With Helmet", det_with, gt_with),
                            ("No Helmet",   det_no,   gt_no),
                            ("TOTAL",       det_total, gt_total)]:
        acc_str = f"{min(det,gt)/gt*100:.1f}%" if gt > 0 else "(no GT set)"
        print(f"  {label:<20}  {det:>9}  {gt:>13}  {acc_str:>9}")

    if gt_total > 0:
        for label, det, gt in [("With Helmet", det_with, gt_with),
                                ("No Helmet",   det_no,   gt_no)]:
            tp  = min(det, gt)
            fp  = max(0, det - gt)
            fn  = max(0, gt  - det)
            pre = tp/(tp+fp) if (tp+fp) > 0 else 0.0
            rec = tp/(tp+fn) if (tp+fn) > 0 else 0.0
            f1  = 2*pre*rec/(pre+rec) if (pre+rec) > 0 else 0.0
            print(f"\n    {label}  Precision:{pre:.1%}  Recall:{rec:.1%}  F1:{f1:.1%}")
        missed_v = max(0, gt_no - det_no)
        print(f"\n  Overall detection rate : {min(det_total,gt_total)/gt_total*100:.1f}%")
        if gt_no > 0:
            print(f"  Missed violations      : {missed_v}/{gt_no} ({missed_v/gt_no*100:.1f}%)")
    else:
        print("\n  [NOTE] Fill HELMET_GROUND_TRUTH for full accuracy metrics.")

    print(f"\n{sep}\n")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

def run(plate_model, helmet_model, ocr):
    # ── Validate input ────────────────────────────────────────────────────────
    input_path = Path(INPUT_PATH)
    if not input_path.exists():
        raise FileNotFoundError(f"Video not found:\n  {INPUT_PATH}")
    if input_path.suffix.lower() not in [".mp4", ".avi", ".mov", ".mkv", ".wmv"]:
        raise ValueError(f"INPUT_PATH must be a video file (.mp4 .avi .mov .mkv .wmv)\n"
                         f"Got: {INPUT_PATH}\n"
                         f"Please update INPUT_PATH in USER CONFIG.")

    cap = cv2.VideoCapture(INPUT_PATH)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video:\n  {INPUT_PATH}")

    fps   = cap.get(cv2.CAP_PROP_FPS) or 25.0
    W     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[INFO] {input_path.name}  {W}x{H} @ {fps:.1f} fps  |  {total} frames  ({total/fps:.1f}s)")
    print(f"[INFO] Processing full video — no limits")
    print(f"[INFO] Plate dedup: box IoU + exact text + fuzzy similarity")
    print(f"[INFO] Helmet dedup: box IoU\n")

    out_vid = ANNOTATED_DIR / ("ann_" + input_path.stem + ".mp4")
    writer  = cv2.VideoWriter(str(out_vid),
                              cv2.VideoWriter_fourcc(*"mp4v"),
                              fps, (W, H))

    plate_reg  = PlateRegistry()
    helmet_reg = HelmetRegistry()
    frame_idx  = 0
    t0         = time.time()
    stats      = dict(with_helmet=0, no_helmet=0)

    with open(PLATE_LOG,  "w", newline="") as plog, \
         open(HELMET_LOG, "w", newline="") as hlog:

        pw = csv.writer(plog)
        hw = csv.writer(hlog)
        pw.writerow(["frame", "plate_id", "plate_number", "conf"])
        hw.writerow(["frame", "helmet_id", "class", "conf", "x1", "y1", "x2", "y2"])

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] End of video.")
                break

            frame_idx += 1
            canvas = frame.copy()

            # ══════════════════════════════════════════════════════════════════
            #  TASK 1 — PLATE DETECTION  (3-layer dedup, detect once)
            # ══════════════════════════════════════════════════════════════════
            plate_res = plate_model(frame, conf=PLATE_CONF, iou=IOU_THRESH,
                                    imgsz=640, verbose=False)

            for box in plate_res[0].boxes:
                if int(box.cls) != 0:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf_val        = float(box.conf[0])
                bbox            = [x1, y1, x2, y2]
                crop            = frame[y1:y2, x1:x2]

                if (crop.size == 0
                        or crop.shape[0] < MIN_PLATE_H
                        or crop.shape[1] < MIN_PLATE_W):
                    continue

                # Run OCR first so fuzzy text dedup can work
                plate_text = run_ocr(ocr, crop)

                # 3-layer duplicate check — skip if already seen
                if plate_reg.is_duplicate(bbox, plate_text):
                    continue

                # New unique plate — register and save once
                pid = plate_reg.register(bbox, plate_text, conf_val, frame_idx)

                fname = f"{pid}_{plate_text or 'NOTEXT'}_f{frame_idx:06d}.jpg"
                cv2.imwrite(str(PLATE_CROPS_DIR / fname), crop)

                pw.writerow([frame_idx, pid, plate_text, f"{conf_val:.3f}"])
                plog.flush()

                num = plate_text if plate_text else "(unreadable)"
                print(f"  [PLATE] #{plate_reg.count:02d}  {pid}"
                      f"  NUMBER: {num}"
                      f"  frame {frame_idx}  conf {conf_val:.2f}")

                draw_label(canvas, x1, y1, x2, y2,
                           f"{pid}: {plate_text or '?'} ({conf_val:.2f})",
                           (0, 230, 0))

            # ══════════════════════════════════════════════════════════════════
            #  TASK 2 — HELMET DETECTION  (box dedup, detect once)
            # ══════════════════════════════════════════════════════════════════
            helmet_res = helmet_model(frame, conf=HELMET_CONF, iou=IOU_THRESH,
                                      imgsz=640, verbose=False)

            for box in helmet_res[0].boxes:
                cls_id   = int(box.cls[0])
                conf_val = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                bbox     = [x1, y1, x2, y2]
                crop     = frame[y1:y2, x1:x2]

                if (crop.size == 0
                        or crop.shape[0] < MIN_HELMET_H
                        or crop.shape[1] < MIN_HELMET_W):
                    continue

                if helmet_reg.is_duplicate(bbox):
                    continue

                helmet_reg.register(bbox)

                if cls_id == HELMET_CLASS_ID:
                    cls_name = "with_helmet"
                    label    = f"Helmet OK ({conf_val:.2f})"
                    color    = (255, 200, 0)
                    save_dir = HELMET_CROPS_DIR
                    stats["with_helmet"] += 1
                else:
                    cls_name = "no_helmet"
                    label    = f"NO HELMET! ({conf_val:.2f})"
                    color    = (0, 0, 230)
                    save_dir = NO_HELMET_CROPS_DIR
                    stats["no_helmet"] += 1
                    print(f"  [VIOLATION] NO HELMET  frame {frame_idx}"
                          f"  conf {conf_val:.2f}")

                hfile = save_dir / f"{cls_name}_{helmet_reg.count:05d}_f{frame_idx:06d}.jpg"
                cv2.imwrite(str(hfile), crop)

                hw.writerow([frame_idx, helmet_reg.count, cls_name,
                             f"{conf_val:.3f}", x1, y1, x2, y2])
                hlog.flush()

                draw_label(canvas, x1, y1, x2, y2, label, color)

            writer.write(canvas)

            # ── Live preview ──────────────────────────────────────────────────
            if SHOW_PREVIEW and frame_idx % PREVIEW_EVERY == 0:
                pct = frame_idx / total * 100 if total > 0 else 0
                hud = canvas.copy()
                for i, txt in enumerate([
                    f"Frame {frame_idx}/{total}  ({pct:.1f}%)",
                    f"Unique plates  : {plate_reg.count}",
                    f"With helmet    : {stats['with_helmet']}",
                    f"NO helmet      : {stats['no_helmet']}",
                    "Q = quit",
                ]):
                    cv2.putText(hud, txt, (10, 28 + i*26),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.70,
                                (255, 255, 0), 2, cv2.LINE_AA)
                cv2.imshow("Traffic Vision — Detect Once  (Q)", hud)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("[INFO] Quit by user.")
                    break
            elif frame_idx % PREVIEW_EVERY == 0:
                elapsed = time.time() - t0
                pct     = frame_idx / total * 100 if total > 0 else 0
                print(f"  frame {frame_idx}/{total} ({pct:.1f}%)"
                      f"  |  {frame_idx/max(elapsed,1):.1f} fps"
                      f"  |  plates {plate_reg.count}"
                      f"  |  helmets {helmet_reg.count}")

    cap.release()
    writer.release()
    if SHOW_PREVIEW:
        cv2.destroyAllWindows()

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    sep = "=" * 65
    print(f"\n{sep}")
    print(f"  DONE  {frame_idx} frames in {elapsed:.1f}s  ({elapsed/60:.1f} min)")
    print(sep)
    print(f"\n  {'ID':<6}  {'PLATE NUMBER':<18}  {'CONF':>5}  FRAME")
    print(f"  {'-'*42}")
    with open(PLATE_LOG, newline="") as f:
        for row in csv.DictReader(f):
            num = row["plate_number"] if row["plate_number"] else "(unreadable)"
            print(f"  {row['plate_id']:<6}  {num:<18}  {row['conf']:>5}  frame {row['frame']}")

    print(f"\n  Total unique plates  : {plate_reg.count}")
    print(f"  Total unique helmets : {helmet_reg.count}")
    print(f"    with helmet        : {stats['with_helmet']}")
    print(f"    NO helmet          : {stats['no_helmet']}")
    print(f"\n  Annotated video  ->  {out_vid}")
    print(f"  Plate crops      ->  {PLATE_CROPS_DIR}")
    print(f"  Plate log        ->  {PLATE_LOG}")

    evaluate_accuracy(plate_reg, stats)


# ═════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    plate_model, helmet_model, ocr = load_models()
    run(plate_model, helmet_model, ocr)