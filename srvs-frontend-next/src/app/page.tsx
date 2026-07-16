"use client";

import React, { useState, useEffect, useRef } from 'react';
import Header from '../components/Header';
import SessionControlPanel from '../components/SessionControlPanel';
import VideoAnalyticsStation from '../components/VideoAnalyticsStation';
import LiveTelemetryLog from '../components/LiveTelemetryLog';
import EnforcementLedger from '../components/EnforcementLedger';
import ReviewDrawer from '../components/ReviewDrawer';
import SnapshotsGallery from '../components/SnapshotsGallery';
import ComparisonSliderModal from '../components/ComparisonSliderModal';
import CsvExplorer from '../components/CsvExplorer';
import { 
  MOCK_TELEMETRY, 
  INITIAL_LOGS, 
  SNAPSHOTS_DATABASE, 
  MOCK_CSV_DATABASE 
} from '../components/mockData';
import { LogEntry, EnhancedSnapshot, TelemetryMap, CSVFile } from '../components/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  // Navigation Routing States
  const [activeTab, setActiveTab] = useState<'dashboard' | 'snapshots' | 'csv-explorer'>('dashboard');

  // Stream & Ingestion Engine States
  const [activeMediaFeed, setActiveMediaFeed] = useState<string>('SRVS - Footage of Front Plates - New.mp4');
  const [mediaFeeds, setMediaFeeds] = useState<string[]>([
    'SRVS - Footage of Front Plates - New.mp4',
    'SRVS - Footage of Rear Plates - Alt.mp5'
  ]);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processProgress, setProcessProgress] = useState<number>(0);
  const [activeLogs, setActiveLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [telemetry, setTelemetry] = useState<TelemetryMap>(MOCK_TELEMETRY);
  const [snapshots, setSnapshots] = useState<EnhancedSnapshot[]>(SNAPSHOTS_DATABASE);
  const [csvFiles, setCsvFiles] = useState<CSVFile[]>(MOCK_CSV_DATABASE);

  // Ingestion File Download States
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  
  // Review Drawer & Modal States
  const [selectedReviewTrack, setSelectedReviewTrack] = useState<EnhancedSnapshot | null>(null);
  const [isReviewDrawerOpen, setIsReviewDrawerOpen] = useState<boolean>(false);
  const [selectedGallerySnapshot, setSelectedGallerySnapshot] = useState<EnhancedSnapshot | null>(null);

  // Backend connection status flag
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Check connection status to FastAPI on load
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const res = await fetch(`${API_URL}/api/ledger?category=Motorcycle`);
        if (res.ok) {
          setIsBackendConnected(true);
          console.log("[SYSTEM] Connected to FastAPI backend successfully.");
        }
      } catch (err) {
        setIsBackendConnected(false);
        console.warn("[SYSTEM] FastAPI backend is offline. Running in high-fidelity simulation mode.");
      }
    };
    checkConnection();
  }, [activeTab]);

  // Load database tables and CSV files from backend if connected
  const refreshBackendData = async () => {
    if (!isBackendConnected) return;

    try {
      // 1. Fetch ledgers for Motorcycles, Rickshaws, Large Vehicles
      const [motoRes, rickRes, largeRes] = await Promise.all([
        fetch(`${API_URL}/api/ledger?category=Motorcycle`),
        fetch(`${API_URL}/api/ledger?category=Auto-rickshaw`),
        fetch(`${API_URL}/api/ledger?category=Large%20Vehicles`)
      ]);

      if (motoRes.ok && rickRes.ok && largeRes.ok) {
        const moto = await motoRes.json();
        const rick = await rickRes.json();
        const large = await largeRes.json();

        // Combine into unified snapshots list, parsing paths correctly
        const combined = [...moto, ...rick, ...large].map(item => ({
          ...item,
          rawImage: item.rawImage.startsWith("http") ? item.rawImage : `${API_URL}${item.rawImage}`,
          enhancedImage: item.enhancedImage.startsWith("http") ? item.enhancedImage : `${API_URL}${item.enhancedImage}`
        }));
        
        // Only set snapshots if backend has items, otherwise use initial mocks
        if (combined.length > 0) {
          setSnapshots(combined);
        }
      }

      // 2. Fetch CSV files metadata and rows
      const csvRes = await fetch(`${API_URL}/api/csv-explorer`);
      if (csvRes.ok) {
        const csvs = await csvRes.json();
        if (csvs.length > 0) {
          setCsvFiles(csvs);
        }
      }
    } catch (err) {
      console.error("[ERROR] Failed to load data from backend:", err);
    }
  };

  // Poll for databases on tab switch or periodically
  useEffect(() => {
    refreshBackendData();
  }, [activeTab, isBackendConnected]);

  // SSE stream events subscription when processing starts
  useEffect(() => {
    if (isProcessing && isBackendConnected) {
      console.log("[SYSTEM] Connecting to SSE stream at /api/stream/events...");
      const eventSource = new EventSource(`${API_URL}/api/stream/events`);
      eventSourceRef.current = eventSource;

      // Reset local stream telemetry coordinates on start
      setTelemetry({});
      setActiveLogs([]);

      eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'log') {
            setActiveLogs(prev => [...prev, payload.data]);
            // Close progress and finalize state when pipeline signals completion log
            if (payload.data.message.includes("Engine run succeeded")) {
              setProcessProgress(100);
              setIsProcessing(false);
              refreshBackendData();
            }
          } else if (payload.type === 'telemetry') {
            setTelemetry(prev => ({
              ...prev,
              [payload.data.frame]: payload.data.tracks
            }));
            
            // Sync progress bar: estimate based on frame counts (max 30 frames in dummy)
            const progress = (payload.data.frame / 30) * 100;
            setProcessProgress(Math.min(progress, 100));
          }
        } catch (err) {
          console.error("Failed to parse SSE payload:", err);
        }
      };

      eventSource.onerror = (err) => {
        console.warn("SSE connection closed or lost. Finalizing logs...");
        eventSource.close();
        setIsProcessing(false);
        setProcessProgress(100);
        refreshBackendData();
      };

      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
      };
    } else if (isProcessing && !isBackendConnected) {
      // Offline high-fidelity simulation loop (10 seconds @ 60 FPS)
      setActiveLogs([
        { time: '16:14:10', message: `[SIMULATION] Initializing parallel detection execution routing context for ${activeMediaFeed}...`, type: 'info' },
        { time: '16:14:11', message: '[SIMULATION] YOLOv8 & PaddleOCR inference weights mounted directly on system GPU device...', type: 'info' }
      ]);
      setProcessProgress(0);
      setTelemetry(MOCK_TELEMETRY);

      const updateProgress = () => {
        setProcessProgress((prev) => {
          const next = prev + 1.25;
          if (next >= 100) {
            setIsProcessing(false);
            setActiveLogs(prevLogs => [
              ...prevLogs,
              { time: '16:14:32', message: '[SIMULATION] Engine run succeeded. Multi-table ledger databases synchronized.', type: 'info' }
            ]);
            return 100;
          }
          if (Math.floor(next) % 15 === 0) {
            const randSpeed = (70 + Math.random() * 20).toFixed(1);
            const randId = Math.floor(100 + Math.random() * 50);
            setActiveLogs(prevLogs => [
              ...prevLogs,
              { time: '16:14:22', message: `⚠️ [SIMULATION ALERT] Speed Violation registered: Track ID #${randId} at ${randSpeed} km/h`, type: 'warning' },
              { time: '16:14:25', message: `🔍 Ingestion routine mapped Frame #${Math.floor(next * 6)} directly to local ledger`, type: 'info' }
            ]);
          }
          return next;
        });
      };
      const timer = setInterval(updateProgress, 100);
      return () => clearInterval(timer);
    }
  }, [isProcessing, isBackendConnected, activeMediaFeed]);

  // Actions
  const handleStartProcessing = async () => {
    if (isBackendConnected) {
      try {
        const res = await fetch(`${API_URL}/api/stream/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stream_feed: activeMediaFeed })
        });
        if (res.ok) {
          setIsProcessing(true);
          setProcessProgress(0);
        }
      } catch (err) {
        console.error("Failed to start backend stream:", err);
      }
    } else {
      setIsProcessing(true);
    }
  };

  const handleDownloadDriveVideo = async (fileId: string) => {
    setIsDownloading(true);
    setDownloadError(null);
    try {
      if (isBackendConnected) {
        const res = await fetch(`${API_URL}/api/video/download`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_id: fileId })
        });
        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || "Download failed on backend");
        }
        
        // Append newly downloaded file to selectors
        const newFeed = `${fileId}.mp4`;
        setMediaFeeds(prev => [...prev, newFeed]);
        setActiveMediaFeed(newFeed);
        
        setActiveLogs(prev => [
          ...prev,
          { time: '16:14:15', message: `📥 [DOWNLOAD SUCCESS] File ${fileId}.mp4 downloaded locally and added to media feeds.`, type: 'info' }
        ]);
      } else {
        // Simulated offline success
        await new Promise(resolve => setTimeout(resolve, 2000));
        const newFeed = `${fileId}.mp4`;
        setMediaFeeds(prev => [...prev, newFeed]);
        setActiveMediaFeed(newFeed);
        
        setActiveLogs(prev => [
          ...prev,
          { time: '16:14:15', message: `📥 [SIMULATED INGESTION] File ${fileId}.mp4 ingested successfully.`, type: 'info' }
        ]);
      }
    } catch (err: any) {
      setDownloadError(err.message || "Failed to download remote file");
      setActiveLogs(prev => [
        ...prev,
        { time: '16:14:16', message: `❌ [INGESTION ERROR] Ingestion failed: ${err.message || "Unknown error"}`, type: 'warning' }
      ]);
      throw err;
    } finally {
      setIsDownloading(false);
    }
  };

  const handleOpenReview = (trackId: number) => {
    const snapshot = snapshots.find(s => s.trackId === trackId);
    if (snapshot) {
      setSelectedReviewTrack(snapshot);
      setIsReviewDrawerOpen(true);
    }
  };

  const handleConfirmReview = async (trackId: number, plateNumber: string) => {
    setActiveLogs(prev => [
      ...prev,
      { time: '16:14:45', message: `✅ [VERIFIED] Manual audit verified Plate registration: ${plateNumber} (Track #${trackId})`, type: 'info' }
    ]);
    setIsReviewDrawerOpen(false);
    setSelectedGallerySnapshot(null);
  };

  const handleRejectReview = async (trackId: number) => {
    setActiveLogs(prev => [
      ...prev,
      { time: '16:14:55', message: `❌ [REJECTED] Track #${trackId} reported as false positive.`, type: 'warning' }
    ]);
    setIsReviewDrawerOpen(false);
    setSelectedGallerySnapshot(null);
  };

  const handleResetWorkspace = async () => {
    if (isBackendConnected && isProcessing) {
      try {
        await fetch(`${API_URL}/api/stream/stop`, { method: 'POST' });
      } catch (err) {
        console.warn("Failed to send stop signal to backend:", err);
      }
    }
    
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setIsProcessing(false);
    setProcessProgress(0);
    setActiveLogs(INITIAL_LOGS);
    setTelemetry(MOCK_TELEMETRY);
    setSnapshots(SNAPSHOTS_DATABASE);
    setCsvFiles(MOCK_CSV_DATABASE);
    setIsReviewDrawerOpen(false);
    setSelectedReviewTrack(null);
    setSelectedGallerySnapshot(null);
    setDownloadError(null);
  };

  const getVideoUrl = (feed: string) => {
    if (feed === 'SRVS - Footage of Front Plates - New.mp4' || feed === 'SRVS - Footage of Rear Plates - Alt.mp5') {
      return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4";
    }
    if (feed.endsWith('.mp4')) {
      return `${API_URL}/videos/${feed}`;
    }
    return "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4";
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-mono select-none antialiased selection:bg-emerald-500 selection:text-black">
      
      {/* HEADER SECTION */}
      <Header 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        onTabChange={() => setIsReviewDrawerOpen(false)}
      />

      {/* RENDER ACTIVE ROUTE CONTAINER */}
      <main className="flex-grow max-w-[1800px] w-full mx-auto p-6 flex flex-col gap-6 relative">
        
        {activeTab === 'dashboard' && (
          <div className="flex flex-col gap-6">
            
            {/* SESSION CONTROL PANEL */}
            <SessionControlPanel 
              activeMediaFeed={activeMediaFeed}
              setActiveMediaFeed={setActiveMediaFeed}
              mediaFeeds={mediaFeeds}
              isProcessing={isProcessing}
              onStartProcessing={handleStartProcessing}
              processProgress={processProgress}
              onReset={handleResetWorkspace}
              onDownloadDriveVideo={handleDownloadDriveVideo}
              isDownloading={isDownloading}
              downloadError={downloadError}
            />

            {/* MAIN TWO-COLUMN SYSTEM GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
              
              {/* ZONE 1: VIDEO OVERLAY WORKSPACE */}
              <div className="lg:col-span-2 flex">
                <VideoAnalyticsStation 
                  telemetryData={telemetry}
                  videoUrl={getVideoUrl(activeMediaFeed)}
                  streamLabel="ZONE 1: STREAM PANEL CONTAINER"
                  nativeWidth={2560}
                  nativeHeight={1440}
                  fps={60}
                />
              </div>

              {/* ZONE 2: LIVE TELEMETRY LOG */}
              <div className="flex">
                <LiveTelemetryLog logs={activeLogs} />
              </div>

            </div>

            {/* ZONE 3: ENFORCEMENT LEDGER */}
            <EnforcementLedger 
              snapshots={snapshots} 
              onReview={handleOpenReview}
            />

          </div>
        )}

        {activeTab === 'snapshots' && (
          <SnapshotsGallery 
            snapshots={snapshots}
            onSelect={setSelectedGallerySnapshot}
          />
        )}

        {activeTab === 'csv-explorer' && (
          <CsvExplorer csvFiles={csvFiles} />
        )}

        {/* PORTALS & OVERLAY COMPONENTS */}
        
        {/* Right slide drawer (Zone 3 ledger reviews) */}
        <ReviewDrawer 
          isOpen={isReviewDrawerOpen}
          onClose={() => setIsReviewDrawerOpen(false)}
          track={selectedReviewTrack}
          onConfirm={handleConfirmReview}
          onReject={handleRejectReview}
        />

        {/* Full-screen comparison zoom modal (Gallery audit) */}
        <ComparisonSliderModal 
          isOpen={selectedGallerySnapshot !== null}
          onClose={() => setSelectedGallerySnapshot(null)}
          snapshot={selectedGallerySnapshot}
          onConfirm={handleConfirmReview}
        />

      </main>

      {/* FOOTER METRIC DECK */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-4 px-6 text-center text-zinc-600 text-[10px] tracking-wider flex flex-col sm:flex-row justify-between items-center gap-2">
        <p>© 2026 Smart Road Vision System (SRVS V4) | Karachi Operations Control Hub</p>
        <div className="flex items-center gap-4 text-zinc-700">
          <span className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${isBackendConnected ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            {isBackendConnected ? "Connected to Azure API" : "Simulated Local Session"}
          </span>
          <span>Secure Terminal Connection Active (TLS 1.3)</span>
        </div>
      </footer>

    </div>
  );
}
