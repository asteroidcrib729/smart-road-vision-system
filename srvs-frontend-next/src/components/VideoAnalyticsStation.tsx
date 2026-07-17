"use client";

import React, { useRef, useState, useEffect, ChangeEvent } from 'react';
import { Play, Pause, Maximize } from 'lucide-react';
import { TelemetryMap, ToggleState, PlaybackState } from './types';

export interface VideoAnalyticsStationProps {
  telemetryData?: TelemetryMap;
  videoUrl: string;
  streamLabel?: string;
  nativeWidth?: number;  // Matching your 1440p horizontal resolution: 2560
  nativeHeight?: number; // Matching your 1440p vertical resolution: 1440
  fps?: number;          // Processing cadence loop configuration: 60
  isProcessing?: boolean; // Disable controls during core engine runs
}

export default function VideoAnalyticsStation({
  telemetryData = {},
  videoUrl,
  streamLabel = "ZONE 1: STREAM PANEL CONTAINER",
  nativeWidth = 2560,
  nativeHeight = 1440,
  fps = 60,
  isProcessing = false
}: VideoAnalyticsStationProps): React.JSX.Element {
  
  // 1. Hardware & Virtual Canvas DOM Reference Points
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
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

  const [playbackRate, setPlaybackRate] = useState<number>(1);

  // 3. High-Speed 60 Hz Canvas Rendering Loop
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

      const drawColor = track.violation ? '#ef4444' : '#10b981'; // Crimson warning flag (#ef4444) vs emerald green (#10b981)

      // Paint active bounding box envelopes
      if (toggles.showBBoxes) {
        ctx.strokeStyle = drawColor;
        ctx.lineWidth = 2.5;
        ctx.strokeRect(metricsRef.current.x, metricsRef.current.y, metricsRef.current.w, metricsRef.current.h);

        // String calculation configurations
        const labelString = `ID: ${track.track_id} | ${track.class_name}`;
        ctx.font = '10px monospace';
        const stringWidth = ctx.measureText(labelString).width;

        ctx.fillStyle = drawColor;
        ctx.fillRect(metricsRef.current.x, metricsRef.current.y - 18, Math.max(160, stringWidth + 12), 18);

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
  };

  // 4. Stable requestAnimationFrame drawing lifecycle connection
  useEffect(() => {
    let animId: number | null = null;

    const tick = () => {
      renderTrackingOverlay();
      const video = videoRef.current;
      if (video && !video.paused && !video.ended) {
        animId = requestAnimationFrame(tick);
      }
    };

    const video = videoRef.current;
    if (video && !video.paused && !video.ended) {
      animId = requestAnimationFrame(tick);
    } else {
      renderTrackingOverlay(); // Paint a single frame when paused or seeking
    }

    return () => {
      if (animId !== null) {
        cancelAnimationFrame(animId);
      }
    };
  }, [telemetryData, toggles, playbackState.isPlaying]);

  // 5. Asynchronous Lifecycle Listeners & Event Mapping Layers
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = (): void => {
      setPlaybackState((prev) => ({ ...prev, isPlaying: true }));
    };

    const handlePause = (): void => {
      setPlaybackState((prev) => ({ ...prev, isPlaying: false }));
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
    };

    const handleSeeked = (): void => {
      renderTrackingOverlay();
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('seeked', handleSeeked);

    // Apply active speed rate
    video.playbackRate = playbackRate;

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('seeked', handleSeeked);
    };
  }, [fps, playbackRate]);

  // Automatically reset video playback to the beginning and start playback when engine starts processing
  useEffect(() => {
    if (isProcessing && videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch((err) => {
        console.warn("[SYSTEM] Autoplay request on engine start was interrupted:", err);
      });
      renderTrackingOverlay();
    }
  }, [isProcessing]);

  // Speed and Fullscreen actions
  const handleSpeedChange = (rate: number) => {
    setPlaybackRate(rate);
    if (videoRef.current) {
      videoRef.current.playbackRate = rate;
    }
  };

  const handleFullscreenToggle = () => {
    const videoContainer = videoRef.current?.parentElement;
    if (videoContainer) {
      if (!document.fullscreenElement) {
        videoContainer.requestFullscreen().catch((err) => {
          console.error("Failed to enter full-screen:", err);
        });
      } else {
        document.exitFullscreen();
      }
    }
  };

  return (
    <div className="w-full bg-zinc-900/40 p-4 rounded-xl border border-zinc-800 flex flex-col gap-4">
      
      {/* MONITOR STATION NAVIGATION LAYER HEADER */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <h3 className="text-xs font-black tracking-widest text-zinc-300 uppercase">{streamLabel}</h3>
        </div>
        <div className="text-[10px] text-zinc-500 bg-zinc-950 px-2.5 py-1 rounded border border-zinc-850 font-mono">
          Sync Frame Index: <span className="text-yellow-500 font-semibold">{playbackState.computedFrame}</span> / {Math.floor(playbackState.totalDuration * fps) || 600}
        </div>
      </div>

      {/* CORE GRAPHICAL CANVAS CONTAINER VIEWPORT STACK */}
      <div className="relative w-full aspect-video rounded-lg overflow-hidden border border-zinc-950 bg-black shadow-inner">
        <video 
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-cover opacity-85"
          preload="auto"
          loop
          muted
        />

        <canvas 
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none z-10 transform-gpu"
        />

        {Object.keys(telemetryData).length === 0 && (
          <div className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-zinc-400 font-mono">Awaiting Ingestion Pipeline...</p>
          </div>
        )}
      </div>

      {/* MANUAL TIMELINE CONTROLLER LAYER WITH FAST-FORWARD & FULLSCREEN */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-zinc-950 p-3 rounded-lg border border-zinc-850">
        
        {/* Play/Pause Button - Disabled during active engine processing */}
        <button 
          onClick={() => videoRef.current && (playbackState.isPlaying ? videoRef.current.pause() : videoRef.current.play())}
          disabled={isProcessing}
          className="p-2 rounded-full transition-all bg-zinc-900 hover:bg-zinc-800 disabled:bg-zinc-950 disabled:text-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed border border-zinc-800 text-zinc-200 active:scale-95 flex items-center justify-center cursor-pointer"
          title={isProcessing ? 'Locked during engine processing' : (playbackState.isPlaying ? 'Pause' : 'Play')}
        >
          {playbackState.isPlaying ? <Pause className="w-4 h-4 text-yellow-500" /> : <Play className="w-4 h-4 text-emerald-500" />}
        </button>

        {/* Speed Controls: 1x, 2x, 4x - Disabled during processing */}
        <div className={`flex bg-zinc-900 border border-zinc-800 p-0.5 rounded text-[10px] font-bold ${isProcessing ? 'opacity-40' : ''}`}>
          {([1, 2, 4] as const).map((rate) => (
            <button
              key={rate}
              onClick={() => handleSpeedChange(rate)}
              disabled={isProcessing}
              className={`px-2 py-1 rounded transition-colors disabled:cursor-not-allowed ${
                playbackRate === rate && !isProcessing ? 'bg-emerald-500 text-black font-bold' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {rate}x
            </button>
          ))}
        </div>
        
        {/* Clickable and Scrubbable Timeline Slider - Disabled during processing */}
        <div className="flex-grow w-full text-xs text-zinc-400 flex items-center justify-between gap-3">
          <span className="font-mono text-zinc-550 shrink-0">{playbackState.currentTime.toFixed(2)}s</span>
          <input 
            type="range"
            min={0}
            max={playbackState.totalDuration || 10}
            step={0.05}
            value={playbackState.currentTime}
            disabled={isProcessing}
            onChange={(e) => {
              const targetTime = parseFloat(e.target.value);
              if (videoRef.current) {
                videoRef.current.currentTime = targetTime;
              }
              setPlaybackState(prev => ({ ...prev, currentTime: targetTime }));
            }}
            className="w-full h-1 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-emerald-500 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
          />
          <span className="font-mono text-zinc-550 shrink-0">{(playbackState.totalDuration || 10).toFixed(2)}s</span>
        </div>

        {/* Fullscreen Button - Kept interactive so user can inspect fullscreen processing streams */}
        <button
          onClick={handleFullscreenToggle}
          className="p-2 rounded transition-all bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-400 hover:text-zinc-200 active:scale-95 flex items-center justify-center cursor-pointer"
          title="Fullscreen Mode"
        >
          <Maximize className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* THE INTERACTIVE TRACKING TOGGLE DECK PANEL */}
      <div className="bg-zinc-950 rounded-lg p-4 border border-zinc-850 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.showBBoxes}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, showBBoxes: e.target.checked })}
            className="accent-emerald-500 w-4 h-4 rounded bg-zinc-900 border-zinc-800 checked:bg-emerald-500 focus:ring-0 cursor-pointer"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-300 group-hover:text-emerald-400 transition-colors font-mono">Show Dynamic Boxes</span>
            <span className="text-[10px] text-zinc-500 font-mono">YOLO Segment Boundaries</span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.showVelocities}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, showVelocities: e.target.checked })}
            className="accent-yellow-500 w-4 h-4 rounded bg-zinc-900 border-zinc-800 checked:bg-yellow-500 focus:ring-0 cursor-pointer"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-300 group-hover:text-yellow-400 transition-colors font-mono">Show Velocity Trackers</span>
            <span className="text-[10px] text-zinc-500 font-mono">Homography Speed Calculation</span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.filterMotorcycles}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, filterMotorcycles: e.target.checked })}
            className="accent-red-500 w-4 h-4 rounded bg-zinc-900 border-zinc-800 checked:bg-red-500 focus:ring-0 cursor-pointer"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors font-mono">Hide Motorcycles</span>
            <span className="text-[10px] text-zinc-600 font-mono">Filter Two-Wheelers</span>
          </div>
        </label>

        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={toggles.filterLargeVehicles}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, filterLargeVehicles: e.target.checked })}
            className="accent-red-500 w-4 h-4 rounded bg-zinc-900 border-zinc-800 checked:bg-red-500 focus:ring-0 cursor-pointer"
          />
          <div className="flex flex-col">
            <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors font-mono">Hide Large Traffic</span>
            <span className="text-[10px] text-zinc-600 font-mono">Filter Cars/Buses/Trucks</span>
          </div>
        </label>
      </div>

    </div>
  );
}
