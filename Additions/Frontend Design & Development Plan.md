# SMART ROAD VISION SYSTEM (SRVS V4) — FRONTEND DESIGN & DEVELOPMENT MASTER PLAN

This master plan details the layout layout design, lifecycle architecture, and data orchestration layers required to build the rest of the frontend dashboard around the `VideoAnalyticsStation.tsx` core component.

---

## 1. Complete Layout Grid Blueprint

The dashboard uses a dark terminal theme built on a **responsive grid layout**. The view is split into three core zones to maintain high informational density on a single screen without relying on nested pages.

### Main Workspace Grid Layout Topology

```
──────────────────────────────────────────────────────────────────────────────────────────
 [SRVS V4]  AI VIDEO MONITORING STATION                                Karachi Hub Desk
──────────────────────────────────────────────────────────────────────────────────────────
 █ SESSION CONTROL PANEL (Full Width Toolbar)
  [ Select Media Feed A ▾ ]  [ Select Media Feed B ▾ ]  [ ▶ RUN ENGINE ]  [ ↻ Reset Workspace ]
  Status: Processing Run #024 | Progress: [██████████████░░░░░░] 70% | Target FPS: 60Hz
──────────────────────────────────────────────────────────────────────────────────────────
 █ ZONE 1: CORE VIDEO STATIONS (65% Width)   │ █ ZONE 2: TELEMETRY ACTIVITY LOG (35% Width)
 ┌──────────────────────────────────────────┐│ ┌─────────────────────────────────────────┐
 │                                          ││ │ [00:00:42.10] Ingesting Frame #2528     │
 │       STREAM A PANEL CONTAINER           ││ │ [00:00:42.15] Track #84 (Bus): 42 km/h  │
 │   (SRVS - Footage of Front Plates)       ││ │ [00:00:42.15] ANPR Consensus: MN-9081   │
 │                                          ││ │ ─────────────────────────────────────── │
 ├──────────────────────────────────────────┤│ │ 🛑 [00:00:43.02] Track #87 (Motorcycle) │
 │                                          ││ │    SPEED VIOLATION: 78 km/h             │
 │       STREAM B PANEL CONTAINER           ││ │ 🛑 [00:00:43.10] Track #87 (Motorcycle) │
 │   (SRVS - Footage of Rear Plates)        ││ │    HELMET VIOLATION: NOT DETECTED       │
 │                                          ││ │                                         │
 └──────────────────────────────────────────┘│ └─────────────────────────────────────────┘
─────────────────────────────────────────────┴────────────────────────────────────────────
 █ ZONE 3: ENFORCEMENT LEDGER (Full Width Lower Deck - Tab Bed)
  [ 🛵 Motorcycles Ledger (5) ]   [ 🛺 Auto-Rickshaws Ledger (2) ]   [ 🚛 Large Vehicles Ledger (14) ]
 ┌───────────────────────────────────────────────────────────────────────────────────────┐
 │ ID    │ TIMESTAMP  │ CLASSIFICATION │ VELOCITY │ ASSIGNED PLATE │ STATUS     │ ACTIONS │
 ├───────┼────────────┼────────────────┼──────────┼────────────────┼────────────┼─────────┤
 │ #87   │ 21:42:04   │ Motorcycle     │ 78 km/h  │ KCD-9081       │ ❌ Alert   │ [Review]│
 │ #84   │ 21:42:01   │ Bus            │ 42 km/h  │ MN-9081        │ ✅ Clear   │ [Review]│
 └───────────────────────────────────────────────────────────────────────────────────────┘

```

### Right-Side Investigation Slide Drawer (`[Review]` Macro Action)

Clicking `[Review]` on any entry in the ledger slides out a focused panel from the right window border to audit the work done by your background AI modules:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🖨️ EVIDENCE ENFORCEMENT AUDIT: TRACK #87                                        [ X ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  █ MULTI-FRAME CROP SELECTIONS (Best Snapshot Extraction)                               │
│   Heuristic Target: Area Max / Laplacian Sharpness Peak Locked                         │
│                                                                                        │
│   Original Low-Resolution Vehicle Crop        Enhanced Real-ESRGAN Plate Snapshot       │
│   ┌─────────────────────────────────┐       ┌─────────────────────────────────┐        │
│   │                                 │       │                                 │        │
│   │       [ Blurry License ]        │       │       [ SHARP TEXT STRING ]     │        │
│   │           [ Plate ]             │       │           [ KCD-9081 ]          │        │
│   │                                 │       │                                 │        │
│   └─────────────────────────────────┘       └─────────────────────────────────┘        │
│                                                                                        │
│  █ TELEMETRY METADATA LOGS                                                             │
│   • Evaluated Real Speed: 78 km/h           • Security Integrity Status: Non-Compliant │
│   • Temporal OCR String: KCD-9081           • Consensus Buffer Depth: 7 Frames         │
│                                                                                        │
│  █ INVESTIGATION AUDIT COMPLIANCE SIGN-OFF                                             │
│   [ 👍 Verify License Integrity ]                      [ 👎 Report False Positive ]   │
└────────────────────────────────────────────────────────────────────────────────────────┘

```

---

## 2. Headless Backend Bridge & Execution Router

Because your backend pipeline must be treated as completely immutable, the frontend operates entirely on its **physical side-effects**: child-process execution handles, SQLite database file modifications, and newly generated disk images.

### System Spawning and Monitoring API Design

The dashboard uses Next.js server actions or API endpoints to manage the lifecycle of your backend scripts without requiring code modifications inside `run_streams.py`:

```typescript
// Location: /src/app/api/analyze/route.ts
import { spawn } from 'child_process';
import { NextResponse } from 'next/server';

let activeProcess: any = null;

export async function POST(request: Request) {
  const { videoA, videoB } = await request.json();
  
  if (activeProcess) {
    return NextResponse.json({ error: "An analysis cycle is currently running." }, { status: 400 });
  }

  // Spawn run_streams.py externally, passing your QHD 60FPS file paths as environment parameters
  activeProcess = spawn('python', ['run_streams.py'], {
    env: { 
      ...process.env,
      STREAM_A_SOURCE: `data/FYP Footage/${videoA}`,
      STREAM_B_SOURCE: `data/FYP Footage/${videoB}`
    }
  });

  // Log process output to your terminal console for real-time debugging
  activeProcess.stdout.on('data', (data: Buffer) => {
    console.log(`SRVS Backend Output: ${data.toString()}`);
  });

  activeProcess.on('close', (code: number) => {
    console.log(`Pipeline process closed with code: ${code}`);
    activeProcess = null;
  });

  return NextResponse.json({ status: "PROCESSING_STARTED" });
}

```

---

## 3. Database Synchronization & Event Ingestion

As your python `DatabaseHandler` module commits evaluated tracks to SQLite, the frontend polls the target database asynchronously. It packages these entries into a frame-indexed hash map structured for $O(1)$ constant-time lookup performance inside your 60 FPS video playback container loops.

### Ingestion Query Service Spec

```typescript
// Location: /src/lib/dbFetcher.ts
import sqlite3 from 'sqlite3';
import { TelemetryMap, TrackData } from '@/types/analytics';

export async function fetchTelemetryPayload(dbPath: string): Promise<TelemetryMap> {
  return new Promise((resolve, reject) => {
    const db = new sqlite3.Database(dbPath);
    const telemetry: TelemetryMap = {};

    // Combine your Motorcycles, Auto_Rickshaws, and Large_Vehicles tables into a unified timeline
    const query = `
      SELECT 'Motorcycle' as class_name, Tracking_ID, Read_Number_Plate, Helmet_Detected, Violation_Detected, Frame_Index, BBox_Coords, Real_Speed FROM Motorcycles
      UNION ALL
      SELECT 'Auto-rickshaw' as class_name, Tracking_ID, Read_Number_Plate, NULL, Violation_Detected, Frame_Index, BBox_Coords, Real_Speed FROM Auto_Rickshaws
      UNION ALL
      SELECT Large_Vehicles.Class_Type as class_name, Tracking_ID, Read_Number_Plate, NULL, Violation_Detected, Frame_Index, BBox_Coords, Real_Speed FROM Large_Vehicles
    `;

    db.all(query, [], (err, rows) => {
      if (err) return reject(err);

      rows.forEach((row: any) => {
        const frameIdx = row.Frame_Index;
        if (!telemetry[frameIdx]) telemetry[frameIdx] = [];

        // Parse coordinates back from database serialization formats safely
        const parsedBBox = JSON.parse(row.BBox_Coords); // [x1, y1, x2, y2]

        telemetry[frameIdx].push({
          track_id: parseInt(row.Tracking_ID),
          bbox: parsedBBox,
          class_name: row.class_name,
          speed: row.Real_Speed,
          violation: Boolean(row.Violation_Detected)
        });
      });

      db.close();
      resolve(telemetry);
    });
  });
}

```

---

## 4. Interactive UI Components Specifications

To make the system highly engaging without adding unnecessary decorative styling, focus your development on three highly tactile, interactive data controls:

### Component A: The Session Controller Toolbar

* **The Dropdown Selectors:** Map your target files (`"SRVS - Footage of Front Number-Plates - New.mp4"`, etc.) directly into user-selectable lists.
* **The Processing Engine Trigger:** A prominent trigger labeled `[ ▶ RUN ENGINE ANALYSIS ]`. Clicking this locks the controls, shows a loading animation, and initializes an interval function that checks the stdout pipeline.
* **The Progress Indicator:** Reads the total frame metrics directly from the video metadata to provide a real-time progress bar, giving users immediate visual feedback as the engine processes the file.

### Component B: The Real-ESRGAN Before/After Comparison Lens Slider

Surfaced inside the right investigation drawer, this component highlights your background enhancement pipeline by providing an interactive image slider:

* **The Mechanics:** Mount two equal-sized image containers stacked directly on top of each other. The base container holds the raw low-resolution vehicle crop (`output/Motorcycles/107.jpg`), while the upper layer maps the restored asset (`output/Restored_Dashboards/Restored_107.jpg`).
* **The Lens Control:** A vertical divider bar widget allows users to slide left or right across the image canvas. Dragging the bar uses CSS width clipping (`clip-path`) to peel away the blurry crop and reveal the clear, enhanced license plate characters underneath.

### Component C: The Database Schema Multi-Table Ledger

Placed directly inside Zone 3, this tab container serves as your master data viewer, mapped directly to your SQLite storage tables:

* **Tab Menus:** Designed with fast client-side tab switching controllers: `[ 🛵 Motorcycles Ledger ]`, `[ 🛺 Auto-Rickshaws Ledger ]`, and `[ 🚛 Large Traffic Ledger ]`.
* **Dynamic Search Modifiers:** An inline input bar allows users to filter results on the fly. Typing text characters instantly updates the rows to find matches against the `Read_Number_Plate` string column using quick regex filtering.
* **Action Routing Hooks:** Each table row features an interactive `[ Review Evidentiary Data ]` action link that maps directly to your side investigation drawer, bridging the data tables and the video overlay together.

---

## 6. Implementation and Development Roadmap

To ensure a structured, step-by-step development process, follow this phased implementation sequence:

```
[Phase 1: Environment Setup] ──► [Phase 2: Bridge Routing] ──► [Phase 3: Synchronized Overlay] ──► [Phase 4: Ledger Integration]

```

### Phase 1: Ingestion Infrastructure Setup

* [ ] Configure your Next.js project directory with TypeScript enabled.
* [ ] Install layout dependencies: TailwindCSS, Lucide-React, and a lightweight SQLite database wrapper (`better-sqlite3` or `sqlite3`).
* [ ] Map the backend pipeline’s `output/` folder directory inside your frontend project setup to serve static asset images safely.

### Phase 2: Background Process Routing

* [ ] Build out the Node.js process runtime engine API paths (`/api/analyze/start`).
* [ ] Implement process protection bounds to throw an alert error block if a duplicate execution request is fired before an active run completes.
* [ ] Verify that clicking the dashboard's processing button successfully spawns `run_streams.py` and logs process metrics to your terminal output window.

### Phase 3: Synchronized Canvas Overlay Deployment

* [ ] Integrate your pre-developed `VideoAnalyticsStation.tsx` file directly into your UI dashboard workflow layout window.
* [ ] Implement the frame mapping math loop component to transform raw database coordinates accurately into native 1440p spatial canvas scaling vectors.
* [ ] Test timeline scrubbing on your 60 FPS test files (`"SRVS - Footage of Front Number-Plates - New.mp4"`) to ensure bounding boxes stick to moving targets when jumping around the timeline.

### Phase 4: Tabbed Ledger and Action Drawer Integration

* [ ] Wire the lower multi-table ledger to fetch rows from the SQLite tables using asynchronous polling routines.
* [ ] Connect the ledger row action links to the right investigation drawer, passing tracking IDs smoothly to load image files.
* [ ] Build out the before/after slider widget to cleanly showcase the image enhancements generated by the `RealESRGANAPI` background tasks.