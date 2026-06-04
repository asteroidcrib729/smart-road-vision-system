"use client";

import React, { useState, useEffect } from 'react';
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
import { LogEntry, EnhancedSnapshot } from '../components/types';

export default function Home() {
  // Navigation Routing States
  const [activeTab, setActiveTab] = useState<'dashboard' | 'snapshots' | 'csv-explorer'>('dashboard');

  // Stream & Ingestion Engine States
  const [activeMediaFeed, setActiveMediaFeed] = useState<string>('SRVS - Footage of Front Plates - New.mp4');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processProgress, setProcessProgress] = useState<number>(0);
  const [activeLogs, setActiveLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  
  // Review Drawer & Modal States
  const [selectedReviewTrack, setSelectedReviewTrack] = useState<EnhancedSnapshot | null>(null);
  const [isReviewDrawerOpen, setIsReviewDrawerOpen] = useState<boolean>(false);
  const [selectedGallerySnapshot, setSelectedGallerySnapshot] = useState<EnhancedSnapshot | null>(null);

  // Background Stream ingestion routine simulation
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isProcessing) {
      setActiveLogs([
        { time: '16:14:10', message: `Initializing parallel detection execution routing context for ${activeMediaFeed}...`, type: 'info' },
        { time: '16:14:11', message: 'YOLOv8 & PaddleOCR inference weights mounted directly on system GPU device...', type: 'info' }
      ]);
      setProcessProgress(0);

      const updateProgress = () => {
        setProcessProgress((prev) => {
          const next = prev + 1.25;
          if (next >= 100) {
            setIsProcessing(false);
            setActiveLogs(prevLogs => [
              ...prevLogs,
              { time: '16:14:32', message: 'Engine run succeeded. Multi-table ledger databases synchronized with real-time files.', type: 'info' }
            ]);
            return 100;
          }
          if (Math.floor(next) % 15 === 0) {
            const randSpeed = (70 + Math.random() * 20).toFixed(1);
            const randId = Math.floor(100 + Math.random() * 50);
            setActiveLogs(prevLogs => [
              ...prevLogs,
              { time: '16:14:22', message: `⚠️ [ALERT] Speed Violation registered: Track ID #${randId} at ${randSpeed} km/h`, type: 'warning' },
              { time: '16:14:25', message: `🔍 Ingestion routine mapped Frame #${Math.floor(next * 6)} directly to local ledger`, type: 'info' }
            ]);
          }
          return next;
        });
      };
      timer = setInterval(updateProgress, 100);
    }
    return () => clearInterval(timer);
  }, [isProcessing, activeMediaFeed]);

  // Actions
  const handleOpenReview = (trackId: number) => {
    const snapshot = SNAPSHOTS_DATABASE.find(s => s.trackId === trackId);
    if (snapshot) {
      setSelectedReviewTrack(snapshot);
      setIsReviewDrawerOpen(true);
    }
  };

  const handleConfirmReview = (trackId: number, plateNumber: string) => {
    setActiveLogs(prev => [
      ...prev,
      { time: '16:14:45', message: `✅ [VERIFIED] Manual audit verified Plate registration: ${plateNumber} (Track #${trackId})`, type: 'info' }
    ]);
    setIsReviewDrawerOpen(false);
    setSelectedGallerySnapshot(null);
  };

  const handleRejectReview = (trackId: number) => {
    setActiveLogs(prev => [
      ...prev,
      { time: '16:14:55', message: `❌ [REJECTED] Track #${trackId} reported as false positive.`, type: 'warning' }
    ]);
    setIsReviewDrawerOpen(false);
    setSelectedGallerySnapshot(null);
  };

  const handleResetWorkspace = () => {
    setIsProcessing(false);
    setProcessProgress(0);
    setActiveLogs(INITIAL_LOGS);
    setIsReviewDrawerOpen(false);
    setSelectedReviewTrack(null);
    setSelectedGallerySnapshot(null);
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
              isProcessing={isProcessing}
              onStartProcessing={() => setIsProcessing(true)}
              processProgress={processProgress}
              onReset={handleResetWorkspace}
            />

            {/* MAIN TWO-COLUMN SYSTEM GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
              
              {/* ZONE 1: VIDEO OVERLAY WORKSPACE */}
              <div className="lg:col-span-2 flex">
                <VideoAnalyticsStation 
                  telemetryData={MOCK_TELEMETRY}
                  videoUrl="https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
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
              snapshots={SNAPSHOTS_DATABASE} 
              onReview={handleOpenReview}
            />

          </div>
        )}

        {activeTab === 'snapshots' && (
          <SnapshotsGallery 
            snapshots={SNAPSHOTS_DATABASE}
            onSelect={setSelectedGallerySnapshot}
          />
        )}

        {activeTab === 'csv-explorer' && (
          <CsvExplorer csvFiles={MOCK_CSV_DATABASE} />
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
        <p className="text-zinc-700">Secure Terminal Connection Active (TLS 1.3)</p>
      </footer>

    </div>
  );
}
