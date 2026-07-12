import React, { useRef, useState, useEffect } from 'react';

/**
 * Smart Road Vision System (SRVS V4)
 * High-Performance Client-Side Temporal Sync Overlay Engine
 * Optimized for 1440p @ 60 FPS Processing Payload
 */
export default function VideoAnalyticsStation({ 
  telemetryData = {}, // Expected: O(1) Hash Map { frameIndex: [ { track_id, bbox, class_name, speed, violation } ] }
  videoUrl, 
  streamLabel = "STREAM ANALYSIS HUB",
  nativeWidth = 2560, // Exact horizontal pixel boundaries of your FYP Footages
  nativeHeight = 1440, // Exact vertical pixel boundaries of your FYP Footages
  fps = 60 // 60 Frames Per Second tracking thread cadence
}) {
  
  // 1. Immutable Infrastructure & Hardware Refs
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  
  // Reusable tracking structures allocated outside the loop to defeat Garbage Collection thrashing
  const scaleRef = useRef({ x: 1, y: 1 });
  const metricsRef = useRef({ currentFrame: 0, x: 0, y: 0, w: 0, h: 0 });

  // 2. Tactical Interaction Toggle Deck States
  const [toggles, setToggles] = useState({
    showBBoxes: true,
    showVelocities: true,
    filterMotorcycles: false,
    filterLargeVehicles: false,
  });

  const [playbackState, setPlaybackState] = useState({
    isPlaying: false,
    currentTime: 0,
    totalDuration: 0,
    computedFrame: 0
  });

  // 3. High-Speed 60 FPS Canvas Rendering Engine
  const renderTrackingOverlay = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Dynamically match canvas coordinate resolution to physical display container boundaries
    if (canvas.width !== video.clientWidth || canvas.height !== video.clientHeight) {
      canvas.width = video.clientWidth;
      canvas.height = video.clientHeight;
      
      // Compute spatial matrix transformer scales instantly on client resolution shift
      scaleRef.current.x = canvas.width / nativeWidth;
      scaleRef.current.y = canvas.height / nativeHeight;
    }

    // Determine target historical frame index via current playback cursor location
    metricsRef.current.currentFrame = Math.floor(video.currentTime * fps);

    // Clear viewport workspace before painting the next layer matrix
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // O(1) Quick Evaluation Check
    const frameTracks = telemetryData[metricsRef.current.currentFrame] || [];

    // Loop optimized for minimal memory initialization path
    for (let i = 0; i < frameTracks.length; i++) {
      const track = frameTracks[i];

      // Interactive Filters applied directly inside the processing pipeline loop
      if (toggles.filterMotorcycles && track.class_name === 'Motorcycle') continue;
      if (toggles.filterLargeVehicles && ['Car', 'Truck', 'Bus'].includes(track.class_name)) continue;

      const [x1, y1, x2, y2] = track.bbox;
      
      // Calculate layout coordinates using pre-calculated scale metrics
      metricsRef.current.x = x1 * scaleRef.current.x;
      metricsRef.current.y = y1 * scaleRef.current.y;
      metricsRef.current.w = (x2 - x1) * scaleRef.current.x;
      metricsRef.current.h = (y2 - y1) * scaleRef.current.y;

      const drawColor = track.violation ? '#ef4444' : '#22c55e'; // Deep Red for alerts, Green for clear status

      // Draw bounding boxes around target paths
      if (toggles.showBBoxes) {
        ctx.strokeStyle = drawColor;
        ctx.lineWidth = 2;
        ctx.strokeRect(metricsRef.current.x, metricsRef.current.y, metricsRef.current.w, metricsRef.current.h);

        // Render meta string title banner overlay elements
        const labelString = `ID: ${track.track_id} | ${track.class_name}`;
        ctx.font = '11px monospace';
        const stringWidth = ctx.measureText(labelString).width;

        ctx.fillStyle = drawColor;
        ctx.fillRect(metricsRef.current.x, metricsRef.current.y - 18, stringWidth + 12, 18);

        ctx.fillStyle = '#ffffff';
        ctx.fillText(labelString, metricsRef.current.x + 6, metricsRef.current.y - 5);
      }

      // Render mathematical velocity labels onto active bounding box footers
      if (toggles.showVelocities && track.speed > 0) {
        ctx.fillStyle = '#eab308'; // High-contrast terminal yellow text colors
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText(`${track.speed.toFixed(1)} km/h`, metricsRef.current.x + 4, metricsRef.current.y + metricsRef.current.h - 6);
      }
    }

    // Continuously loop execution loop using native monitor frame refresh controls
    if (!video.paused && !video.ended) {
      animationFrameRef.current = requestAnimationFrame(renderTrackingOverlay);
    }
  };

  // 4. Structural Lifecycle and Media State Event Synchronizers
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => {
      setPlaybackState((prev) => ({ ...prev, isPlaying: true }));
      animationFrameRef.current = requestAnimationFrame(renderTrackingOverlay);
    };

    const handlePause = () => {
      setPlaybackState((prev) => ({ ...prev, isPlaying: false }));
      cancelAnimationFrame(animationFrameRef.current);
    };

    const handleTimeUpdate = () => {
      setPlaybackState((prev) => ({
        ...prev,
        currentTime: video.currentTime,
        computedFrame: Math.floor(video.currentTime * fps)
      }));
    };

    const handleLoadedMetadata = () => {
      setPlaybackState((prev) => ({ ...prev, totalDuration: video.duration }));
      renderTrackingOverlay(); // Paint first layout frame frame accurately on file ingestion
    };

    const handleSeeked = () => {
      // Force instantaneous canvas update when scrubbing the video timeline slider manually
      renderTrackingOverlay();
    };

    // Attach native media asset hooks directly to component DOM controls
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
      cancelAnimationFrame(animationFrameRef.current);
    };
  }, [telemetryData, toggles]);

  return (
    <div className="w-full bg-zinc-950 p-6 rounded-xl border border-zinc-800 font-mono shadow-2xl">
      
      {/* HUD CONTROL PANELS BAR */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-4">
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="text-sm font-bold text-zinc-200 tracking-wider uppercase">{streamLabel}</h3>
        </div>
        <div className="text-xs text-zinc-500 bg-zinc-900 px-3 py-1 rounded border border-zinc-800">
          QHD 1440p @ 60Hz Sync Deck | Frame: <span className="text-yellow-500 font-semibold">{playbackState.computedFrame}</span>
        </div>
      </div>

      {/* RENDER BOX OVERLAY STATION STACK */}
      <div className="relative w-full aspect-video rounded-lg overflow-hidden border border-zinc-900 bg-black group shadow-inner">
        {/* Layer 1: HTML5 Base Media Container (Serves your unannotated high-res clip) */}
        <video 
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain"
          preload="auto"
        />

        {/* Layer 2: Transparent Overlap Vector Graphic Canvas Element */}
        <canvas 
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none z-10 transform-gpu"
        />

        {/* CONTROLLER LOADER DRAWER COVERS */}
        {Object.keys(telemetryData).length === 0 && (
          <div className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-zinc-400">Awaiting Simulation Backend Process Ingestion Pipeline...</p>
          </div>
        )}
      </div>

      {/* SIMULATION MONITOR TIMELINE DESK */}
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

      {/* SECTION D: INTERACTIVE TRACKING TOGGLE DECK PANEL */}
      <div className="bg-zinc-900/60 rounded-lg p-4 border border-zinc-900 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.showBBoxes}
            onChange={(e) => setToggles({ ...toggles, showBBoxes: e.target.checked })}
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
            onChange={(e) => setToggles({ ...toggles, showVelocities: e.target.checked })}
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
            onChange={(e) => setToggles({ ...toggles, filterMotorcycles: e.target.checked })}
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
            onChange={(e) => setToggles({ ...toggles, filterLargeVehicles: e.target.checked })}
            className="accent-red-500 w-4 h-4 rounded bg-zinc-800 border-zinc-700 checked:bg-red-500 transition-all focus:ring-0"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors">Hide Large Traffic</span>
            <span className="text-[10px] text-zinc-600">Mask Cars/Trucks/Buses Data</span>
          </div>
        </label>
      </div>

    </div>
  );
}