import React, { useRef, useState, useEffect, ChangeEvent } from 'react';

// ============================================================================
// STRUCTURAL TYPE DEFINITIONS & CONTRACTS
// ============================================================================

export interface TrackData {
  track_id: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  class_name: string;
  speed: number;
  violation: boolean;
}

export interface TelemetryMap {
  [frameIndex: number]: TrackData[];
}

export interface VideoAnalyticsStationProps {
  telemetryData?: TelemetryMap;
  videoUrl: string;
  streamLabel?: string;
  nativeWidth?: number;  // Matching your 1440p horizontal resolution: 2560
  nativeHeight?: number; // Matching your 1440p vertical resolution: 1440
  fps?: number;          // Processing cadence loop configuration: 60
}

interface ToggleState {
  showBBoxes: boolean;
  showVelocities: boolean;
  filterMotorcycles: boolean;
  filterLargeVehicles: boolean;
}

interface PlaybackState {
  isPlaying: boolean;
  currentTime: number;
  totalDuration: number;
  computedFrame: number;
}

// ============================================================================
// CORE COMPONENT IMPLEMENTATION
// ============================================================================

export default function VideoAnalyticsStation({
  telemetryData = {},
  videoUrl,
  streamLabel = "STREAM ANALYSIS HUB",
  nativeWidth = 2560,
  nativeHeight = 1440,
  fps = 60
}: VideoAnalyticsStationProps): React.JSX.Element {
  
  // 1. Hardware & Virtual Canvas DOM Reference Points
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  
  // Reference pools allocated outside the execution path to defeat Garbage Collection thrashing
  const scaleRef = useRef<{ x: number; y: number }>({ x: 1, y: 1 });
  const metricsRef = useRef<{ currentFrame: number; x: number; y: number; w: number; h: number }>({
    currentFrame: 0, x: 0, y: 0, w: 0, h: 0
  });

  // 2. Interactive Toggle Deck State Engines
  const [toggles, setToggles] = useState<ToggleState>({
    showBBoxes: true,
    showVelocities: true,
    filterMotorcycles: false,
    filterLargeVehicles: false,
  });

  const [playbackState, setPlaybackState] = useState<PlaybackState>({
    isPlaying: false,
    currentTime: 0,
    totalDuration: 0,
    computedFrame: 0
  });

  // 3. High-Speed 60 Hz Canvas Rendering Loop Thread
  const renderTrackingOverlay = (): void => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Secure cross-scaling calculation steps natively against viewport size adjustments
    if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
      canvas.width = video.clientWidth;
      canvas.height = video.clientHeight;
      
      // Calculate transform scale profiles based on true 1440p media clip footprint boundaries
      scaleRef.current.x = canvas.width / nativeWidth;
      scaleRef.current.y = canvas.height / nativeHeight;
    }

    // Determine current frame pointer index using video runtime coordinates
    metricsRef.current.currentFrame = Math.floor(video.currentTime * fps);

    // Wipe down viewport context boundaries before rendering next frame coordinates
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // O(1) Quick hash-lookup for target frame indices
    const frameTracks = telemetryData[metricsRef.current.currentFrame] || [];

    // Microsecond-optimized layout pass loop 
    for (let i = 0; i < frameTracks.length; i++) {
      const track = frameTracks[i];

      // Safe Runtime Toggle Filter Interceptors
      if (toggles.filterMotorcycles && track.class_name === 'Motorcycle') continue;
      if (toggles.filterLargeVehicles && ['Car', 'Truck', 'Bus', 'Auto-rickshaw'].includes(track.class_name)) continue;

      const [x1, y1, x2, y2] = track.bbox;
      
      // Compute pixel layout anchors using pre-calculated scale targets
      metricsRef.current.x = x1 * scaleRef.current.x;
      metricsRef.current.y = y1 * scaleRef.current.y;
      metricsRef.current.w = (x2 - x1) * scaleRef.current.x;
      metricsRef.current.h = (y2 - y1) * scaleRef.current.y;

      const drawColor = track.violation ? '#ef4444' : '#22c55e'; // Crimson warning flag vs dynamic system green

      // Paint active bounding box envelopes
      if (toggles.showBBoxes) {
        ctx.strokeStyle = drawColor;
        ctx.lineWidth = 2;
        ctx.strokeRect(metricsRef.current.x, metricsRef.current.y, metricsRef.current.w, metricsRef.current.h);

        // String calculation configurations
        const labelString = `ID: ${track.track_id} | ${track.class_name}`;
        ctx.font = '11px monospace';
        const stringWidth = ctx.measureText(labelString).width;

        ctx.fillStyle = drawColor;
        ctx.fillRect(metricsRef.current.x, metricsRef.current.y - 18, stringWidth + 12, 18);

        ctx.fillStyle = '#ffffff';
        ctx.fillText(labelString, metricsRef.current.x + 6, metricsRef.current.y - 5);
      }

      // Paint real-time homography perspective speed calculation descriptors
      if (toggles.showVelocities && track.speed > 0) {
        ctx.fillStyle = '#eab308'; // Warning amber text
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText(`${track.speed.toFixed(1)} km/h`, metricsRef.current.x + 4, metricsRef.current.y + metricsRef.current.h - 6);
      }
    }

    // Keep running drawing requests as long as video state indicates playback is active
    if (!video.paused && !video.ended) {
      animationFrameRef.current = requestAnimationFrame(renderTrackingOverlay);
    }
  };

  // 4. Asynchronous Lifecycle Listeners & Event Mapping Layers
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = (): void => {
      setPlaybackState((prev) => ({ ...prev, isPlaying: true }));
      animationFrameRef.current = requestAnimationFrame(renderTrackingOverlay);
    };

    const handlePause = (): void => {
      setPlaybackState((prev) => ({ ...prev, isPlaying: false }));
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };

    const handleTimeUpdate = (): void => {
      setPlaybackState((prev) => ({
        ...prev,
        currentTime: video.currentTime,
        computedFrame: Math.floor(video.currentTime * fps)
      }));
    };

    const handleLoadedMetadata = (): void => {
      setPlaybackState((prev) => ({ ...prev, totalDuration: video.duration }));
      renderTrackingOverlay(); // Paint first structural snapshot immediately on file load
    };

    const handleSeeked = (): void => {
      renderTrackingOverlay(); // Force frame bounding updates during timeline timeline slider scrubbing
    };

    // Standardize event target registration loops
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('seeked', handleSeeked);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('seeked', handleSeeked);
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [telemetryData, toggles]);

  return (
    <div className="w-full bg-zinc-950 p-6 rounded-xl border border-zinc-800 font-mono shadow-2xl">
      
      {/* MONITOR STATION NAVIGATION LAYER HEADER */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-4">
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="text-sm font-bold text-zinc-200 tracking-wider uppercase">{streamLabel}</h3>
        </div>
        <div className="text-xs text-zinc-500 bg-zinc-900 px-3 py-1 rounded border border-zinc-800">
          QHD 1440p @ 60Hz TypeScript Deck | Frame: <span className="text-yellow-500 font-semibold">{playbackState.computedFrame}</span>
        </div>
      </div>

      {/* CORE GRAPHICAL CANVAS CONTAINER VIEWPORT STACK */}
      <div className="relative w-full aspect-video rounded-lg overflow-hidden border border-zinc-900 bg-black shadow-inner">
        <video 
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          preload="auto"
        />

        <canvas 
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none z-10 transform-gpu"
        />

        {Object.keys(telemetryData).length === 0 && (
          <div className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-zinc-400">Awaiting Simulation Backend Process Ingestion Pipeline...</p>
          </div>
        )}
      </div>

      {/* MANUAL TIMELINE CONTROLLER LAYER */}
      <div className="flex items-center gap-4 my-4 bg-zinc-900/40 p-3 rounded-lg border border-zinc-900">
        <button 
          onClick={() => videoRef.current && (playbackState.isPlaying ? videoRef.current.pause() : videoRef.current.play())}
          className="px-4 py-1.5 rounded text-xs font-bold transition-all bg-zinc-800 hover:bg-zinc-700 text-zinc-200 active:scale-95 min-w-[70px]"
        >
          {playbackState.isPlaying ? 'PAUSE' : 'PLAY'}
        </button>
        <div className="flex-1 text-xs text-zinc-400 flex items-center justify-between">
          <span>{playbackState.currentTime.toFixed(2)}s</span>
          <div className="w-full mx-4 h-1 bg-zinc-800 rounded overflow-hidden relative">
            <div 
              className="absolute left-0 top-0 h-full bg-green-500 transition-all duration-75"
              style={{ width: `${(playbackState.currentTime / (playbackState.totalDuration || 1)) * 100}%` }}
            />
          </div>
          <span>{(playbackState.totalDuration || 0).toFixed(2)}s</span>
        </div>
      </div>

      {/* SECTION D: THE INTERACTIVE TRACKING TOGGLE DECK PANEL */}
      <div className="bg-zinc-900/60 rounded-lg p-4 border border-zinc-900 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.showBBoxes}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, showBBoxes: e.target.checked })}
            className="accent-green-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 checked:bg-green-500 transition-all focus:ring-0"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-300 group-hover:text-green-400 transition-colors">Show Dynamic Boxes</span>
            <span className="text-[10px] text-zinc-500">Draw YOLO Target Coordinates</span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.showVelocities}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, showVelocities: e.target.checked })}
            className="accent-yellow-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 checked:bg-yellow-500 transition-all focus:ring-0"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-300 group-hover:text-yellow-400 transition-colors">Show Velocity Trackers</span>
            <span className="text-[10px] text-zinc-500">Render Homography Real Speed</span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.filterMotorcycles}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, filterMotorcycles: e.target.checked })}
            className="accent-red-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 checked:bg-red-500 transition-all focus:ring-0"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors">Hide Motorcycles</span>
            <span className="text-[10px] text-zinc-600">Mask Out Two-Wheeler Overlay</span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.filterLargeVehicles}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, filterLargeVehicles: e.target.checked })}
            className="accent-red-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 checked:bg-red-500 transition-all focus:ring-0"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors">Hide Mapped Traffic</span>
            <span className="text-[10px] text-zinc-600">Mask Cars/Trucks/Buses Data</span>
          </div>
        </label>
      </div>

    </div>
  );
}