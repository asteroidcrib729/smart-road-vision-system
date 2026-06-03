"use client";

import React, { useMemo } from 'react';
import VideoAnalyticsStation, { TelemetryMap } from '../components/VideoAnalyticsStation';

export default function Home() {
  // Generate high-fidelity mock telemetry data corresponding to active bounding boxes
  const mockTelemetry: TelemetryMap = useMemo(() => {
    const telemetry: TelemetryMap = {};
    // Generate data for 1000 frames (approx 16 seconds at 60fps)
    for (let frame = 0; frame < 1000; frame++) {
      telemetry[frame] = [
        {
          track_id: 87,
          // Bounding box: [x1, y1, x2, y2]
          // Slowly moves from left to right on a 2560x1440 resolution canvas
          bbox: [
            150 + frame * 1.8, 
            400 + Math.sin(frame / 20) * 30, 
            400 + frame * 1.8, 
            800 + Math.sin(frame / 20) * 30
          ],
          class_name: 'Motorcycle',
          speed: 78.4,
          violation: true
        },
        {
          track_id: 84,
          // Moves from right to left
          bbox: [
            2000 - frame * 1.2, 
            550, 
            2450 - frame * 1.2, 
            950
          ],
          class_name: 'Bus',
          speed: 42.1,
          violation: false
        }
      ];
    }
    return telemetry;
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-mono flex flex-col selection:bg-green-500 selection:text-black">
      {/* HEADER SECTION */}
      <header className="border-b border-zinc-800 bg-zinc-900/50 backdrop-blur-md px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 z-40">
        <div className="flex items-center gap-4">
          <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-3 py-1.5 rounded-md text-xs font-bold tracking-wider animate-pulse flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-400" />
            LIVE STATION
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tight text-white flex items-center gap-2">
              <span>SRVS V4</span>
              <span className="text-zinc-600">|</span>
              <span className="text-zinc-400 text-sm font-normal">AI VIDEO MONITORING PLATFORM</span>
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="text-zinc-500">
            Node: <span className="text-zinc-300">Karachi Hub Desk</span>
          </div>
          <div className="h-4 w-px bg-zinc-800" />
          <div className="text-zinc-500">
            Target Cadence: <span className="text-yellow-500 font-bold">60Hz</span>
          </div>
        </div>
      </header>

      {/* SESSION TOOLBAR */}
      <section className="bg-zinc-900/30 border-b border-zinc-800/80 px-6 py-3 flex flex-wrap items-center gap-4 justify-between">
        <div className="flex items-center gap-3">
          <label className="text-xs text-zinc-500 font-bold uppercase">Active Media Feed:</label>
          <select className="bg-zinc-900 border border-zinc-800 rounded px-3 py-1.5 text-xs text-zinc-200 focus:outline-none focus:border-green-500 font-mono transition-colors">
            <option>SRVS - Front License Plate Ingest (60fps Demo)</option>
            <option>SRVS - Rear License Plate Ingest (Alternate Source)</option>
          </select>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-400">
            Status: <span className="text-green-500 font-bold">Processing Run #024</span>
          </span>
          <span className="text-zinc-600">|</span>
          <button className="bg-green-600 hover:bg-green-500 text-white font-bold text-xs px-4 py-1.5 rounded transition-all active:scale-95">
            ▶ RUN ENGINE
          </button>
          <button className="bg-zinc-850 hover:bg-zinc-800 text-zinc-400 font-bold text-xs px-4 py-1.5 rounded border border-zinc-800 transition-all active:scale-95">
            ↻ Reset Workspace
          </button>
        </div>
      </section>

      {/* MAIN CONTAINER */}
      <main className="flex-1 p-6 grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* ZONE 1: VIDEO STREAM (Left & Center, occupies 2 cols on xl) */}
        <section className="xl:col-span-2 flex flex-col gap-6">
          <div className="bg-zinc-900/20 rounded-xl overflow-hidden border border-zinc-800/60 p-1">
            <VideoAnalyticsStation 
              telemetryData={mockTelemetry}
              videoUrl="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
              streamLabel="SRVS Karachi Hub Desk - Stream Ingestion"
              nativeWidth={2560}
              nativeHeight={1440}
              fps={60}
            />
          </div>

          {/* ZONE 3: LOWER DECK - ENFORCEMENT LEDGER */}
          <div className="bg-zinc-900/40 rounded-xl border border-zinc-800/80 p-5 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-zinc-850 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-zinc-300">█ ENFORCEMENT LEDGER</span>
                <span className="text-xs text-zinc-600 font-bold">(SYSTEM LOGGED DETECTIONS)</span>
              </div>
              <div className="flex gap-2">
                <button className="bg-zinc-855 text-green-400 border border-green-500/20 text-xs px-3 py-1 rounded font-bold">
                  🛵 Motorcycles (1)
                </button>
                <button className="bg-zinc-900 text-zinc-500 hover:text-zinc-300 text-xs px-3 py-1 rounded">
                  🛺 Auto-Rickshaws (0)
                </button>
                <button className="bg-zinc-900 text-zinc-500 hover:text-zinc-300 text-xs px-3 py-1 rounded">
                  🚛 Large Vehicles (1)
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500 uppercase tracking-wider">
                    <th className="py-2.5 font-bold">Track ID</th>
                    <th className="py-2.5 font-bold">Timestamp</th>
                    <th className="py-2.5 font-bold">Classification</th>
                    <th className="py-2.5 font-bold">Velocity</th>
                    <th className="py-2.5 font-bold">BBox Coords</th>
                    <th className="py-2.5 font-bold">Compliance Status</th>
                    <th className="py-2.5 font-bold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900/50">
                  <tr className="hover:bg-zinc-900/35 transition-colors">
                    <td className="py-3 text-red-400 font-bold">#87</td>
                    <td className="py-3 text-zinc-400">21:42:04</td>
                    <td className="py-3">Motorcycle</td>
                    <td className="py-3 text-yellow-500 font-semibold">78.4 km/h</td>
                    <td className="py-3 text-zinc-500 font-mono">[Dynamic Track]</td>
                    <td className="py-3">
                      <span className="bg-red-950 border border-red-500/20 text-red-400 px-2.5 py-0.5 rounded text-[10px] font-bold">
                        ❌ SPEED VIOLATION
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <button className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-bold px-3 py-1 rounded transition-colors text-[10px]">
                        Review
                      </button>
                    </td>
                  </tr>
                  <tr className="hover:bg-zinc-900/35 transition-colors">
                    <td className="py-3 text-green-400 font-bold">#84</td>
                    <td className="py-3 text-zinc-400">21:42:01</td>
                    <td className="py-3">Bus</td>
                    <td className="py-3 text-zinc-300">42.1 km/h</td>
                    <td className="py-3 text-zinc-500 font-mono">[Dynamic Track]</td>
                    <td className="py-3">
                      <span className="bg-green-950 border border-green-500/20 text-green-400 px-2.5 py-0.5 rounded text-[10px] font-bold">
                        ✅ COMPLIANT
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <button className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-bold px-3 py-1 rounded transition-colors text-[10px]">
                        Review
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ZONE 2: TELEMETRY ACTIVITY LOG (Right Column, occupies 1 col on xl) */}
        <section className="bg-zinc-900/30 rounded-xl border border-zinc-800/80 p-5 flex flex-col gap-4">
          <div className="border-b border-zinc-850 pb-3">
            <h2 className="text-sm font-bold text-zinc-300 flex items-center gap-2">
              <span>█ SYSTEM TELEMETRY LOG</span>
            </h2>
          </div>
          
          <div className="flex-1 font-mono text-[11px] text-zinc-400 space-y-2 overflow-y-auto max-h-[500px] xl:max-h-[700px] scrollbar-thin scrollbar-thumb-zinc-800">
            <p className="text-zinc-650">[00:00:01.00] Initializing SRVS Pipeline Node Engine...</p>
            <p className="text-zinc-650">[00:00:01.20] Loading CUDA execution providers...</p>
            <p className="text-zinc-550">[00:00:02.10] Loading YOLO weight tables [COCO/Custom V4]...</p>
            <p className="text-zinc-300">[00:00:03.45] Model compiled. Processing thread initialized at 60Hz.</p>
            <p className="text-green-500 font-bold">[00:00:04.10] INGESTION SUCCESS: Stream Source کراچی_HUB_A loaded.</p>
            <div className="h-px bg-zinc-800/60 my-2" />
            <p className="text-zinc-500">[00:00:05.15] Ingesting Frame #0001 - Cadence stable</p>
            <p className="text-zinc-500">[00:00:05.80] Ingesting Frame #0040 - Speed: 59.8 FPS</p>
            <p className="text-zinc-300">[00:00:06.12] Track #84 (Bus): Entered detection area. Velocity: 42.1 km/h.</p>
            <p className="text-zinc-500">[00:00:07.45] Ingesting Frame #0120 - Speed: 60.1 FPS</p>
            <p className="text-zinc-300">[00:00:07.62] Track #87 (Motorcycle): Entered detection area.</p>
            <p className="text-red-400 font-bold">🛑 [00:00:07.95] SPEED VIOLATION DETECTED: Track #87 Velocity: 78.4 km/h</p>
            <p className="text-red-450">⚠️ [00:00:08.02] HELMET VIOLATION ALERT: Track #87 Operator non-compliant</p>
            <p className="text-zinc-500">[00:00:09.10] Ingesting Frame #0240 - Speed: 60.0 FPS</p>
            <p className="text-zinc-300">[00:00:09.40] OCR consensus engine locked on Track #87 plate crop.</p>
            <p className="text-yellow-500 font-bold">✨ [00:00:09.95] OCR STABLE READ: Track #87 Plate Consensus: "KCD-9081"</p>
            <p className="text-zinc-500">[00:00:10.50] Ingesting Frame #0360 - Speed: 59.9 FPS</p>
            <p className="text-zinc-500">[00:00:12.10] Ingesting Frame #0480 - Speed: 60.1 FPS</p>
          </div>
          
          <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-900 text-[10px] space-y-1">
            <div className="flex justify-between text-zinc-500">
              <span>CPU Load:</span>
              <span className="text-zinc-300 font-bold">24%</span>
            </div>
            <div className="flex justify-between text-zinc-500">
              <span>GPU Memory:</span>
              <span className="text-zinc-300 font-bold">3.2GB / 8.0GB</span>
            </div>
            <div className="flex justify-between text-zinc-500">
              <span>Consensus Confidence:</span>
              <span className="text-green-500 font-bold">96.8%</span>
            </div>
          </div>
        </section>
        
      </main>

      {/* FOOTER */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-4 px-6 text-center text-[10px] text-zinc-600 flex justify-between items-center">
        <span>© 2026 Smart Road Vision System (SRVS). Karachi Hub Command.</span>
        <span>Secure Terminal Connection Active (TLS 1.3)</span>
      </footer>
    </div>
  );
}
