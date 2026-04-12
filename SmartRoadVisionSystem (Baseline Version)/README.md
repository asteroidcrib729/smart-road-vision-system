# smart-road-vision-system
Smart Road Vision System Is My Final Year Project. By Designing This System, My Aim Is To Assist Local On-Foot Traffic Police Officers In Issuing Challans With Vehicles That Are Being Driven With Unreadable License Plates Or Without License Plates And Bikers Who Are Riding Without Wearing A Helmet.

Smart Road Vision System is a final year project focused on assisting traffic police by detecting:
- vehicles with unreadable or missing license plates,
- helmet violations for bikers.

## UVTP module (initial implementation)

This repository now includes a starter implementation of the **Unidentifiable Vehicle Tracking & Profiling (UVTP)** logic:

- `uvtp/config.py`: centralized thresholds for ghost trigger, plate quality checks, and ReID matching.
- `uvtp/logic_gate.py`: deterministic anomaly logic gate for marking a vehicle as unidentifiable.
- `uvtp/reid/feature_extractor.py`: FastReID-based vehicle embedding extractor scaffold (ResNet-style pipeline support).
- `uvtp/session.py`: session ID generator in format `UID-{TIMESTAMP}-{CAMERA_ID}-{INCREMENT}`.
- `uvtp/profiling.py`: vehicle profiling interface and fallback profiler for Step 5 report generation.
- `uvtp/persistence.py`: snapshot storage and report dispatcher interfaces with local implementations.
- `uvtp/tracker_loop.py`: frame-by-frame loop that wires ReID matching + ghost trigger + event creation + stale-session report flushing + 3-snapshot evidence heuristics + profile-enriched final payloads + dispatch hooks.
- `tests/`: unit tests for ghost logic, persistence helpers, tracker loop, and session ID formatting.

## Run tests

```bash
python -m unittest discover -s tests -v
```


## Development workflow

- Start with `docs_uvtp_next_steps.md` for the implementation sequence after this scaffold.