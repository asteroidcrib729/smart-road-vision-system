# UVTP Next Steps (Execution Order)

This is the practical sequence to continue after the initial scaffold.

### Status update
- ✅ Step 1 executed in code (`uvtp/reid/feature_extractor.py` + `uvtp/tracker_loop.py` matcher wiring).
- ✅ Step 2 executed in code (`AnomalyLogicGate.update_track(...)` integration).
- ✅ Step 3 baseline executed in code (`flush_closed_sessions` report generation).
- ✅ Step 4 baseline executed in code (entry/best/exit snapshot URL heuristics).
- ✅ Step 5 baseline executed in code (profile-enriched report payload generation).


## Step 1 — Integrate FastReID into tracker loop (critical path)

1. Install runtime dependencies:
   - `torch`, `torchvision`
   - `fastreid`
   - `opencv-python`, `numpy`
2. Add FastReID YAML config and Veri-776 weights paths in runtime settings.
3. For each confirmed vehicle track, crop vehicle ROI and call:
   - `extract_embedding(crop)`
4. Use `is_same_vehicle(prev, current)` with threshold from `UVTPConfig` (`0.20` default).

## Step 2 — Wire plate association and ghost trigger to real detections

1. Feed detector outputs into `Detection` structures.
2. Pass `TrackedVehicleState`, vehicle bbox, and plate detections to `AnomalyLogicGate.update_track(...)`.
3. Trigger ghost session creation when `state.is_ghost` flips to `True`.

## Step 3 — Session lifecycle + persistence

1. On trigger, allocate ID via `SessionIdGenerator.next_id(...)`.
2. Maintain session while object is tracked.
3. On track termination, flush evidence + metadata to DB/JSON payload.

## Step 4 — Snapshot heuristics implementation

Implement exactly 3 images per session:
- Entry (first fully visible frame)
- Best (largest bbox + highest sharpness)
- Exit (last frame before leaving FOV)

Store as JPG at quality 80.

## Step 5 — Profiling and report generation

1. Run attribute classifier from best image.
2. Populate output JSON schema.
3. Send event payload to dashboard endpoint.

## Immediate acceptance checks

- Logic gate unit tests pass.
- Session ID format test pass.
- FastReID extractor can load config/weights without runtime error.
- Tracker loop maintains IDs through short occlusions/turns in a validation clip.


## Step 6 — Production hardening (post-baseline)

1. Replace `NullVehicleProfiler` with real attribute model inference.
2. Plug real JPEG encoder/cropper before `snapshot_storage.save_snapshot_bytes(...)`.
3. Connect `ReportDispatcher` to dashboard HTTP endpoint and DB sink.
4. Run field validation clips and tune thresholds (ghost trigger + ReID).