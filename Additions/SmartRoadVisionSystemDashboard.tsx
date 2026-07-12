import React, { useRef, useState, useEffect, ChangeEvent } from 'react';
import { 
  LayoutDashboard, 
  Image as ImageIcon, 
  FileSpreadsheet, 
  Play, 
  Pause, 
  RefreshCw, 
  Search, 
  Sliders, 
  Cpu, 
  AlertTriangle, 
  CheckCircle, 
  ChevronRight, 
  X, 
  FileText,
  ArrowRight
} from 'lucide-react';

// ============================================================================
// STRUCTURAL TYPE DEFINITIONS & CONTRACTS (STRICT TSX)
// ============================================================================

export interface TrackData {
  track_id: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  class_name: string;
  speed: number;
  violation: boolean;
  plate?: string;
  ocr_method?: 'Local OCR (PaddleOCR v4)' | 'Cloud API Fallback (Gemini)';
  confidence?: number;
}

export interface TelemetryMap {
  [frameIndex: number]: TrackData[];
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

interface EnhancedSnapshot {
  id: string;
  trackId: number;
  className: string;
  timestamp: string;
  rawImage: string;
  enhancedImage: string;
  plateNumber: string;
  ocrMethod: 'Local OCR (PaddleOCR v4)' | 'Cloud API Fallback (Gemini)';
  confidence: number;
  speed: number;
  violationType: string | null;
}

interface CSVFile {
  name: string;
  size: string;
  recordsCount: number;
  lastUpdated: string;
  headers: string[];
  rows: Record<string, string | number | boolean>[];
}

// ============================================================================
// HIGH-FIDELITY SIMULATED SEED DATA
// ============================================================================

const MOCK_TELEMETRY: TelemetryMap = {};
// Generate 600 frames of realistic Karachi highway traffic data (10 seconds @ 60 FPS)
for (let frame = 0; frame <= 600; frame++) {
  const tracks: TrackData[] = [];
  
  // Bike 1: Fast moving motorcycle weaving across frames (Frames 10 to 320)
  if (frame >= 10 && frame <= 320) {
    const progress = (frame - 10) / 310;
    const x = 300 + progress * 1600;
    const y = 800 - progress * 200;
    const w = 110 - (progress * 50);
    const h = 170 - (progress * 70);
    tracks.push({
      track_id: 87,
      bbox: [x, y, x + w, y + h],
      class_name: 'Motorcycle',
      speed: 78.4,
      violation: true, // Speed limit violation
      plate: 'KCD-9081',
      ocr_method: 'Cloud API Fallback (Gemini)',
      confidence: 98.2
    });
  }

  // Bus 1: Heavy vehicle cruising (Frames 80 to 450)
  if (frame >= 80 && frame <= 450) {
    const progress = (frame - 80) / 370;
    const x = 100 + progress * 1300;
    const y = 500 + progress * 300;
    const w = 340 - (progress * 80);
    const h = 280 - (progress * 50);
    tracks.push({
      track_id: 84,
      bbox: [x, y, x + w, y + h],
      class_name: 'Bus',
      speed: 42.1,
      violation: false,
      plate: 'MN-9081',
      ocr_method: 'Local OCR (PaddleOCR v4)',
      confidence: 94.5
    });
  }

  // Auto-Rickshaw 1: Mid lane weaving (Frames 180 to 580)
  if (frame >= 180 && frame <= 580) {
    const progress = (frame - 180) / 400;
    const x = 1800 - progress * 1500;
    const y = 650 + progress * 250;
    const w = 150 + (progress * 40);
    const h = 180 + (progress * 45);
    tracks.push({
      track_id: 112,
      bbox: [x, y, x + w, y + h],
      class_name: 'Auto-rickshaw',
      speed: 49.8,
      violation: false,
      plate: 'DGH-7731',
      ocr_method: 'Local OCR (PaddleOCR v4)',
      confidence: 91.2
    });
  }

  // Offending Car: High-speed overtake (Frames 300 to 590)
  if (frame >= 300 && frame <= 590) {
    const progress = (frame - 300) / 290;
    const x = 900 + progress * 1200;
    const y = 600 + progress * 100;
    const w = 240 - (progress * 40);
    const h = 160 - (progress * 20);
    tracks.push({
      track_id: 142,
      bbox: [x, y, x + w, y + h],
      class_name: 'Car',
      speed: 89.5,
      violation: true,
      plate: 'BJZ-4492',
      ocr_method: 'Local OCR (PaddleOCR v4)',
      confidence: 96.8
    });
  }

  MOCK_TELEMETRY[frame] = tracks;
}

const INITIAL_LOGS = [
  { time: '16:14:02', message: 'SRVS System initialized on video stream source A.', type: 'info' },
  { time: '16:14:03', message: 'Database handler mapped to SQLite backend. 412 entries detected.', type: 'info' },
  { time: '16:14:04', message: 'Target homography warp matrix loaded successfully.', type: 'info' },
  { time: '16:14:05', message: 'Ready for engine execution. Click RUN ENGINE to begin pipeline ingestion.', type: 'warning' }
];

const SNAPSHOTS_DATABASE: EnhancedSnapshot[] = [
  {
    id: 'snap-001',
    trackId: 87,
    className: 'Motorcycle',
    timestamp: '2026-06-02 16:10:15',
    rawImage: 'https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&q=40&w=400',
    enhancedImage: 'https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&q=80&w=800',
    plateNumber: 'KCD-9081',
    ocrMethod: 'Cloud API Fallback (Gemini)',
    confidence: 98.2,
    speed: 78.4,
    violationType: 'Speed Limit & Helmet Detection Alert'
  },
  {
    id: 'snap-002',
    trackId: 112,
    className: 'Auto-rickshaw',
    timestamp: '2026-06-02 16:11:04',
    rawImage: 'https://images.unsplash.com/photo-1566908829747-975b9f7833f2?auto=format&fit=crop&q=40&w=400',
    enhancedImage: 'https://images.unsplash.com/photo-1566908829747-975b9f7833f2?auto=format&fit=crop&q=80&w=800',
    plateNumber: 'DGH-7731',
    ocrMethod: 'Local OCR (PaddleOCR v4)',
    confidence: 91.2,
    speed: 49.8,
    violationType: null
  },
  {
    id: 'snap-003',
    trackId: 142,
    className: 'Car',
    timestamp: '2026-06-02 16:11:42',
    rawImage: 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&q=40&w=400',
    enhancedImage: 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&q=80&w=800',
    plateNumber: 'BJZ-4492',
    ocrMethod: 'Local OCR (PaddleOCR v4)',
    confidence: 96.8,
    speed: 89.5,
    violationType: 'Speed Limit Infraction'
  },
  {
    id: 'snap-004',
    trackId: 99,
    className: 'Motorcycle',
    timestamp: '2026-06-02 16:12:11',
    rawImage: 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&q=40&w=400',
    enhancedImage: 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?auto=format&fit=crop&q=80&w=800',
    plateNumber: 'KHI-2210',
    ocrMethod: 'Cloud API Fallback (Gemini)',
    confidence: 97.5,
    speed: 84.1,
    violationType: 'Speed Limit Alert'
  },
  {
    id: 'snap-005',
    trackId: 84,
    className: 'Bus',
    timestamp: '2026-06-02 16:12:59',
    rawImage: 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&q=40&w=400',
    enhancedImage: 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&q=80&w=800',
    plateNumber: 'MN-9081',
    ocrMethod: 'Local OCR (PaddleOCR v4)',
    confidence: 94.5,
    speed: 42.1,
    violationType: null
  },
  {
    id: 'snap-006',
    trackId: 210,
    className: 'Car',
    timestamp: '2026-06-02 16:13:20',
    rawImage: 'https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&q=40&w=400',
    enhancedImage: 'https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&q=80&w=800',
    plateNumber: 'ABC-1234',
    ocrMethod: 'Local OCR (PaddleOCR v4)',
    confidence: 95.1,
    speed: 55.0,
    violationType: null
  }
];

const MOCK_CSV_DATABASE: CSVFile[] = [
  {
    name: 'motorcycle_violations.csv',
    size: '12.4 KB',
    recordsCount: 5,
    lastUpdated: '2026-06-02 16:10:00',
    headers: ['Tracking_ID', 'Timestamp', 'Class', 'Read_Number_Plate', 'Helmet_Detected', 'Velocity_KMPH', 'Violation_Status'],
    rows: [
      { Tracking_ID: 87, Timestamp: '16:10:15', Class: 'Motorcycle', Read_Number_Plate: 'KCD-9081', Helmet_Detected: 'NO', Velocity_KMPH: 78.4, Violation_Status: 'CRITICAL' },
      { Tracking_ID: 99, Timestamp: '16:12:11', Class: 'Motorcycle', Read_Number_Plate: 'KHI-2210', Helmet_Detected: 'YES', Velocity_KMPH: 84.1, Violation_Status: 'CRITICAL' },
      { Tracking_ID: 105, Timestamp: '16:13:02', Class: 'Motorcycle', Read_Number_Plate: 'LHR-8890', Helmet_Detected: 'NO', Velocity_KMPH: 52.3, Violation_Status: 'WARNING' },
      { Tracking_ID: 154, Timestamp: '16:13:45', Class: 'Motorcycle', Read_Number_Plate: 'IK-5062', Helmet_Detected: 'YES', Velocity_KMPH: 71.8, Violation_Status: 'CRITICAL' },
      { Tracking_ID: 201, Timestamp: '16:14:01', Class: 'Motorcycle', Read_Number_Plate: 'QTA-1123', Helmet_Detected: 'NO', Velocity_KMPH: 35.0, Violation_Status: 'WARNING' }
    ]
  },
  {
    name: 'auto_rickshaws_log.csv',
    size: '8.1 KB',
    recordsCount: 4,
    lastUpdated: '2026-06-02 16:08:15',
    headers: ['Tracking_ID', 'Timestamp', 'Read_Number_Plate', 'Velocity_KMPH', 'Emissions_Status', 'Permit_Valid'],
    rows: [
      { Tracking_ID: 112, Timestamp: '16:11:04', Read_Number_Plate: 'DGH-7731', Velocity_KMPH: 49.8, Emissions_Status: 'PASS', Permit_Valid: 'YES' },
      { Tracking_ID: 124, Timestamp: '16:11:58', Read_Number_Plate: 'KAR-9981', Velocity_KMPH: 55.4, Emissions_Status: 'FAIL', Permit_Valid: 'YES' },
      { Tracking_ID: 145, Timestamp: '16:12:33', Read_Number_Plate: 'RWP-1044', Velocity_KMPH: 31.2, Emissions_Status: 'PASS', Permit_Valid: 'NO' },
      { Tracking_ID: 189, Timestamp: '16:13:12', Read_Number_Plate: 'MUL-4050', Velocity_KMPH: 42.0, Emissions_Status: 'PASS', Permit_Valid: 'YES' }
    ]
  },
  {
    name: 'heavy_vehicles_telemetry.csv',
    size: '18.9 KB',
    recordsCount: 6,
    lastUpdated: '2026-06-02 16:11:12',
    headers: ['Tracking_ID', 'Timestamp', 'Vehicle_Type', 'Read_Number_Plate', 'Velocity_KMPH', 'Lane_Index', 'Violation_Status'],
    rows: [
      { Tracking_ID: 84, Timestamp: '16:12:59', Vehicle_Type: 'Bus', Read_Number_Plate: 'MN-9081', Velocity_KMPH: 42.1, Lane_Index: 1, Violation_Status: 'NONE' },
      { Tracking_ID: 91, Timestamp: '16:13:05', Vehicle_Type: 'Truck', Read_Number_Plate: 'HINO-900', Velocity_KMPH: 68.2, Lane_Index: 0, Violation_Status: 'WARNING' },
      { Tracking_ID: 102, Timestamp: '16:13:18', Vehicle_Type: 'Bus', Read_Number_Plate: 'QA-4451', Velocity_KMPH: 50.0, Lane_Index: 1, Violation_Status: 'NONE' },
      { Tracking_ID: 130, Timestamp: '16:13:40', Vehicle_Type: 'Container-Truck', Read_Number_Plate: 'T-889-K', Velocity_KMPH: 74.5, Lane_Index: 2, Violation_Status: 'CRITICAL' },
      { Tracking_ID: 172, Timestamp: '16:13:58', Vehicle_Type: 'Truck', Read_Number_Plate: 'PES-6632', Velocity_KMPH: 48.9, Lane_Index: 0, Violation_Status: 'NONE' },
      { Tracking_ID: 220, Timestamp: '16:14:05', Vehicle_Type: 'Bus', Read_Number_Plate: 'KHI-0044', Velocity_KMPH: 54.2, Lane_Index: 1, Violation_Status: 'NONE' }
    ]
  },
  {
    name: 'api_fallback_telemetry.csv',
    size: '6.4 KB',
    recordsCount: 3,
    lastUpdated: '2026-06-02 16:13:45',
    headers: ['Tracking_ID', 'Timestamp', 'Local_OCR_Confidence', 'API_Fallback_Triggered', 'Plate_Consensus_String', 'API_Response_Time_MS'],
    rows: [
      { Tracking_ID: 87, Timestamp: '16:10:15', Local_OCR_Confidence: '41.2%', API_Fallback_Triggered: 'TRUE', Plate_Consensus_String: 'KCD-9081', API_Response_Time_MS: 480 },
      { Tracking_ID: 99, Timestamp: '16:12:11', Local_OCR_Confidence: '38.9%', API_Fallback_Triggered: 'TRUE', Plate_Consensus_String: 'KHI-2210', API_Response_Time_MS: 520 },
      { Tracking_ID: 105, Timestamp: '16:13:02', Local_OCR_Confidence: '44.5%', API_Fallback_Triggered: 'TRUE', Plate_Consensus_String: 'LHR-8890', API_Response_Time_MS: 490 }
    ]
  }
];

// ============================================================================
// MAIN INTEGRATED WORKSPACE APPLICATION COMPONENT (TSX)
// ============================================================================

export default function App(): React.JSX.Element {
  // Navigation Routing States
  const [activeTab, setActiveTab] = useState<'dashboard' | 'snapshots' | 'csv-explorer'>('dashboard');

  // Video Analytics Station Settings & States
  const [activeMediaFeed, setActiveMediaFeed] = useState<string>('SRVS - Footage of Front Plates - New.mp4');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processProgress, setProcessProgress] = useState<number>(0);
  const [telemetry, setTelemetry] = useState<TelemetryMap>(MOCK_TELEMETRY);
  const [activeLogs, setActiveLogs] = useState(INITIAL_LOGS);
  
  // Ledger active categorization state
  const [ledgerCategory, setLedgerCategory] = useState<'Motorcycle' | 'Auto-rickshaw' | 'Large Vehicles'>('Motorcycle');
  const [ledgerSearchQuery, setLedgerSearchQuery] = useState<string>('');

  // Right-Side Slide investigation Drawer States
  const [selectedReviewTrack, setSelectedReviewTrack] = useState<EnhancedSnapshot | null>(null);
  const [lensSliderPosition, setLensSliderPosition] = useState<number>(50); // percentage split comparison
  const [isReviewDrawerOpen, setIsReviewDrawerOpen] = useState<boolean>(false);

  // Requirement 1: Gallery inspection state
  const [selectedGallerySnapshot, setSelectedGallerySnapshot] = useState<EnhancedSnapshot | null>(null);
  const [gallerySearch, setGallerySearch] = useState<string>('');
  const [galleryFilterClass, setGalleryFilterClass] = useState<string>('All');

  // Requirement 2: CSV Explorer state
  const [selectedCSVFile, setSelectedCSVFile] = useState<CSVFile>(MOCK_CSV_DATABASE[0]);
  const [csvSearchQuery, setCsvSearchQuery] = useState<string>('');

  // 1440p @ 60 FPS Tracking Matrix References (Prevents micro-allocation garbage collection delays)
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const scaleRef = useRef<{ x: number; y: number }>({ x: 1, y: 1 });
  const metricsRef = useRef<{ currentFrame: number; x: number; y: number; w: number; h: number }>({
    currentFrame: 0, x: 0, y: 0, w: 0, h: 0
  });

  const [toggles, setToggles] = useState<ToggleState>({
    showBBoxes: true,
    showVelocities: true,
    filterMotorcycles: false,
    filterLargeVehicles: false,
  });

  const [playbackState, setPlaybackState] = useState<PlaybackState>({
    isPlaying: false,
    currentTime: 0,
    totalDuration: 10, // Simulated total 10s video clip
    computedFrame: 0
  });

  // Background Stream ingestion routine simulation (Next.js Spawn simulation backend router)
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
            setActiveLogs(prevLogs => [
              ...prevLogs,
              { time: '16:14:22', message: `⚠️ [ALERT] Speed Violation registered: Track ID #${Math.floor(100 + Math.random() * 50)} at ${randSpeed} km/h`, type: 'warning' },
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

  // Synchronized High-Performance Canvas Overlay Drawing Engine (Native 1440p Matrix Math)
  const renderTrackingOverlay = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Dynamically scale canvas to match display client boundaries
    const container = canvas.parentElement;
    if (container) {
      if (canvas.width !== container.clientWidth || canvas.height !== container.clientHeight) {
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        
        // Calculate spatial scaling targets based on exact 1440p (2560x1440) coordinate files
        scaleRef.current.x = canvas.width / 2560;
        scaleRef.current.y = canvas.height / 1440;
      }
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const currentFrame = playbackState.computedFrame;
    const frameTracks = telemetry[currentFrame] || [];

    for (let i = 0; i < frameTracks.length; i++) {
      const track = frameTracks[i];

      // Interactive Toggle Filter Interceptors
      if (toggles.filterMotorcycles && track.class_name === 'Motorcycle') continue;
      if (toggles.filterLargeVehicles && ['Car', 'Bus'].includes(track.class_name)) continue;

      const [x1, y1, x2, y2] = track.bbox;
      
      // Paint layout coordinates from native high-res coordinates (x1, y1, x2, y2)
      metricsRef.current.x = x1 * scaleRef.current.x;
      metricsRef.current.y = y1 * scaleRef.current.y;
      metricsRef.current.w = (x2 - x1) * scaleRef.current.x;
      metricsRef.current.h = (y2 - y1) * scaleRef.current.y;

      const drawColor = track.violation ? '#ef4444' : '#22c55e'; // Deep Red alert vs Dynamic green

      // Render Bounding Box paths
      if (toggles.showBBoxes) {
        ctx.strokeStyle = drawColor;
        ctx.lineWidth = 2.5;
        ctx.strokeRect(metricsRef.current.x, metricsRef.current.y, metricsRef.current.w, metricsRef.current.h);

        // Header identity box
        ctx.fillStyle = drawColor;
        ctx.fillRect(metricsRef.current.x, metricsRef.current.y - 20, 160, 20);

        ctx.fillStyle = '#ffffff';
        ctx.font = '10px monospace';
        ctx.fillText(`ID: ${track.track_id} | ${track.class_name}`, metricsRef.current.x + 6, metricsRef.current.y - 6);
      }

      // Render velocity tags
      if (toggles.showVelocities && track.speed > 0) {
        ctx.fillStyle = '#eab308'; // Warning high-contrast amber
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText(`${track.speed.toFixed(1)} km/h`, metricsRef.current.x + 4, metricsRef.current.y + metricsRef.current.h - 6);
      }
    }
  };

  // Video Time Update Tick
  useEffect(() => {
    let tick: NodeJS.Timeout;
    if (playbackState.isPlaying) {
      tick = setInterval(() => {
        setPlaybackState(prev => {
          let nextTime = prev.currentTime + 0.05;
          if (nextTime >= prev.totalDuration) {
            nextTime = 0; // Simulated looping
          }
          return {
            ...prev,
            currentTime: nextTime,
            computedFrame: Math.floor(nextTime * 60) // High-cadence 60 FPS processing
          };
        });
      }, 50);
    }
    return () => clearInterval(tick);
  }, [playbackState.isPlaying]);

  // Sync rendering pipeline triggers
  useEffect(() => {
    renderTrackingOverlay();
  }, [playbackState.currentTime, toggles]);

  // Slide drawer activation
  const handleOpenReview = (trackId: number) => {
    const snapshot = SNAPSHOTS_DATABASE.find(s => s.trackId === trackId);
    if (snapshot) {
      setSelectedReviewTrack(snapshot);
      setIsReviewDrawerOpen(true);
    }
  };

  const getBadgeColor = (method: string) => {
    return method.includes('Gemini') 
      ? 'bg-purple-950/80 text-purple-300 border-purple-800' 
      : 'bg-indigo-950/80 text-indigo-300 border-indigo-800';
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-mono select-none antialiased">
      
      {/* HEADER SECTION */}
      <header className="border-b border-zinc-900 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-[1800px] mx-auto px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Cpu className="w-6 h-6 animate-pulse" />
              <div className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-black tracking-wider text-zinc-100">SMART ROAD VISION SYSTEM</h1>
                <span className="text-[10px] tracking-widest text-emerald-400 font-bold bg-emerald-950/50 px-2 py-0.5 rounded border border-emerald-900">V4</span>
              </div>
              <p className="text-xs text-zinc-500">Autonomous Karachi Traffic Safety & License Recognition Deck</p>
            </div>
          </div>

          {/* DYNAMIC NAVIGATION MENU */}
          <nav className="flex items-center bg-zinc-900 p-1 rounded-lg border border-zinc-800">
            <button
              onClick={() => { setActiveTab('dashboard'); setIsReviewDrawerOpen(false); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-bold transition-all ${
                activeTab === 'dashboard' 
                  ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/10' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              MONITOR HUB
            </button>
            <button
              onClick={() => { setActiveTab('snapshots'); setIsReviewDrawerOpen(false); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-bold transition-all ${
                activeTab === 'snapshots' 
                  ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/10' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              ENHANCED GALLERY
            </button>
            <button
              onClick={() => { setActiveTab('csv-explorer'); setIsReviewDrawerOpen(false); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-bold transition-all ${
                activeTab === 'csv-explorer' 
                  ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/10' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              CSV LEDGER EXPLORER
            </button>
          </nav>
        </div>
      </header>

      {/* RENDER ACTIVE ROUTE CONTAINER */}
      <main className="flex-grow max-w-[1800px] w-full mx-auto p-6 flex flex-col gap-6 relative">
        
        {/* ============================================================================
            ROUTE 1: MONITOR HUB (DASHBOARD WORKSPACE VIEW)
            ============================================================================ */}
        {activeTab === 'dashboard' && (
          <div className="flex flex-col gap-6">
            
            {/* SESSION CONTROL PANEL */}
            <div className="bg-zinc-900/60 rounded-xl p-4 border border-zinc-800/85 flex flex-col xl:flex-row items-center justify-between gap-4">
              <div className="flex flex-wrap items-center gap-4 w-full xl:w-auto">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] text-zinc-500 font-bold tracking-wider">SELECT ACTIVE VIDEO STREAM</span>
                  <select 
                    value={activeMediaFeed}
                    onChange={(e) => {
                      setActiveMediaFeed(e.target.value);
                      setIsProcessing(false);
                      setProcessProgress(0);
                    }}
                    className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded px-3 py-2 outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="SRVS - Footage of Front Plates - New.mp4">Stream A: (FYP Front Plate Footage - 1440p @ 60 FPS)</option>
                    <option value="SRVS - Footage of Rear Plates - Alt.mp4">Stream B: (FYP Rear Plate Footage - 1440p @ 60 FPS)</option>
                  </select>
                </div>

                <div className="flex items-center gap-3 self-end">
                  <button 
                    onClick={() => setIsProcessing(true)}
                    disabled={isProcessing}
                    className={`flex items-center gap-2 px-5 py-2 rounded text-xs font-bold transition-all ${
                      isProcessing 
                        ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed' 
                        : 'bg-emerald-500 hover:bg-emerald-400 text-black hover:scale-[1.02] active:scale-95'
                    }`}
                  >
                    <Cpu className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
                    {isProcessing ? 'RUNNING PROCESSING CORE...' : '▶ RUN ENGINE'}
                  </button>
                  
                  <button 
                    onClick={() => {
                      setPlaybackState({ isPlaying: false, currentTime: 0, totalDuration: 10, computedFrame: 0 });
                      setIsProcessing(false);
                      setProcessProgress(0);
                      setActiveLogs(INITIAL_LOGS);
                    }}
                    className="p-2 bg-zinc-950 border border-zinc-800 hover:border-zinc-700 hover:text-zinc-200 text-zinc-400 rounded transition-all"
                    title="Reset Workspace"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Ingestion Engine state indicators */}
              <div className="w-full xl:w-1/3 flex items-center gap-4 bg-zinc-950 p-3 rounded border border-zinc-800/60">
                <div className="flex-grow">
                  <div className="flex justify-between items-center mb-1 text-[10px] font-bold text-zinc-400">
                    <span>PROCESSING METRICS RUN #024</span>
                    <span className="text-emerald-400">{isProcessing ? `${Math.floor(processProgress)}%` : 'COMPLETED'}</span>
                  </div>
                  <div className="w-full h-1.5 bg-zinc-900 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-emerald-500 transition-all duration-300 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                      style={{ width: `${isProcessing ? processProgress : 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <span className="block text-[9px] text-zinc-500">TARGET DECK RATE</span>
                  <span className="text-xs text-yellow-500 font-bold">60Hz QHD</span>
                </div>
              </div>
            </div>

            {/* MAIN TWO-COLUMN SYSTEM GRID */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* ZONE 1: VIDEO OVERLAY WORKSPACE */}
              <div className="lg:col-span-2 flex flex-col gap-4">
                <div className="w-full bg-zinc-900/40 p-4 rounded-xl border border-zinc-800 flex flex-col gap-4">
                  
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                    <div className="flex items-center gap-3">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                      <h3 className="text-xs font-black tracking-widest text-zinc-300 uppercase">ZONE 1: STREAM PANEL CONTAINER</h3>
                    </div>
                    <div className="text-[10px] text-zinc-500 bg-zinc-950 px-2.5 py-1 rounded border border-zinc-800">
                      Sync Frame Index: <span className="text-yellow-500 font-semibold">{playbackState.computedFrame}</span> / 600
                    </div>
                  </div>

                  {/* High-bitrate video stream simulated canvas stack */}
                  <div className="relative w-full aspect-video rounded-lg overflow-hidden border border-zinc-950 bg-black shadow-inner">
                    <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
                      <img 
                        src="https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&q=70&w=1600" 
                        alt="FYP Stream"
                        className="w-full h-full object-cover opacity-35 filter brightness-50"
                      />
                      <div className="absolute inset-0 bg-[linear-gradient(rgba(18,18,18,0.15)_1px,transparent_1px),linear-gradient(90deg,rgba(18,18,18,0.15)_1px,transparent_1px)] bg-[size:20px_20px]" />
                    </div>

                    <canvas 
                      ref={canvasRef}
                      className="absolute inset-0 w-full h-full pointer-events-none z-10"
                    />

                    {Object.keys(telemetry).length === 0 && (
                      <div className="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-3">
                        <div className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                        <p className="text-xs text-zinc-400">Loading system pipelines to target GPU layout memory...</p>
                      </div>
                    )}
                  </div>

                  {/* Track timeline controls */}
                  <div className="flex items-center gap-4 bg-zinc-950 p-3 rounded-lg border border-zinc-850">
                    <button 
                      onClick={() => setPlaybackState(prev => ({ ...prev, isPlaying: !prev.isPlaying }))}
                      className="px-4 py-1.5 rounded text-xs font-bold transition-all bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-200 active:scale-95 min-w-[70px] flex items-center gap-2"
                    >
                      {playbackState.isPlaying ? <Pause className="w-3.5 h-3.5 text-yellow-500" /> : <Play className="w-3.5 h-3.5 text-emerald-500" />}
                      {playbackState.isPlaying ? 'PAUSE' : 'PLAY'}
                    </button>
                    
                    <div className="flex-grow text-xs text-zinc-400 flex items-center justify-between">
                      <span className="font-mono text-zinc-500">{playbackState.currentTime.toFixed(2)}s</span>
                      <div className="w-full mx-4 h-1 bg-zinc-900 rounded-full overflow-hidden relative">
                        <div 
                          className="absolute left-0 top-0 h-full bg-emerald-500 transition-all duration-75"
                          style={{ width: `${(playbackState.currentTime / (playbackState.totalDuration || 1)) * 100}%` }}
                        />
                      </div>
                      <span className="font-mono text-zinc-500">{(playbackState.totalDuration || 10).toFixed(2)}s</span>
                    </div>
                  </div>

                  {/* Render tracking switches */}
                  <div className="bg-zinc-950 rounded-lg p-4 border border-zinc-850 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <label className="flex items-center gap-3 cursor-pointer select-none group">
                      <input 
                        type="checkbox"
                        checked={toggles.showBBoxes}
                        onChange={(e: ChangeEvent<HTMLInputElement>) => setToggles({ ...toggles, showBBoxes: e.target.checked })}
                        className="accent-emerald-500 w-4 h-4 rounded bg-zinc-900 border-zinc-800 checked:bg-emerald-500 focus:ring-0 cursor-pointer"
                      />
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-zinc-300 group-hover:text-emerald-400 transition-colors">Show Dynamic Boxes</span>
                        <span className="text-[10px] text-zinc-500">YOLO Segment Boundaries</span>
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
                        <span className="text-xs font-bold text-zinc-300 group-hover:text-yellow-400 transition-colors">Show Velocity Trackers</span>
                        <span className="text-[10px] text-zinc-500">Homography Speed Calculation</span>
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
                        <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors">Hide Motorcycles</span>
                        <span className="text-[10px] text-zinc-600">Filter Two-Wheelers</span>
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
                        <span className="text-xs font-bold text-zinc-400 group-hover:text-red-400 transition-colors">Hide Large Traffic</span>
                        <span className="text-[10px] text-zinc-600">Filter Cars/Buses/Trucks</span>
                      </div>
                    </label>
                  </div>

                </div>
              </div>

              {/* ZONE 2: LIVE TELEMETRY LOG */}
              <div className="flex flex-col gap-4">
                <div className="bg-zinc-900/40 p-4 rounded-xl border border-zinc-800 flex-grow flex flex-col justify-between max-h-[515px]">
                  <div>
                    <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-3">
                      <span className="text-xs font-black tracking-widest text-zinc-300 uppercase">ZONE 2: TELEMETRY ACTIVITY LOG</span>
                      <span className="text-[9px] bg-red-950 text-red-400 border border-red-900/60 rounded px-2 py-0.5">Stream Output</span>
                    </div>

                    {/* Scrollable event listings */}
                    <div className="flex flex-col gap-2.5 h-[380px] overflow-y-auto pr-1">
                      {activeLogs.map((log, index) => (
                        <div 
                          key={index} 
                          className={`p-3 rounded border text-xs leading-relaxed transition-all ${
                            log.type === 'warning' 
                              ? 'bg-rose-950/20 border-rose-900/40 text-rose-300 animate-pulse' 
                              : 'bg-zinc-950/60 border-zinc-850 text-zinc-300'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1 text-[10px] text-zinc-500 font-semibold">
                            <span className="flex items-center gap-1.5">
                              <span className={`w-1.5 h-1.5 rounded-full ${log.type === 'warning' ? 'bg-red-400 animate-ping' : 'bg-zinc-600'}`} />
                              TELEMETRY LOG TICK
                            </span>
                            <span>{log.time}</span>
                          </div>
                          <p className="font-mono">{log.message}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 text-right">
                    <span className="text-[10px] text-zinc-500">Live Cadence Polling...</span>
                  </div>
                </div>
              </div>

            </div>

            {/* ============================================================================
                ZONE 3: ENFORCEMENT LEDGER (TAB BED DATA LEDGER)
                ============================================================================ */}
            <div className="bg-zinc-900/40 rounded-xl p-6 border border-zinc-800">
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-zinc-800 pb-4 mb-6">
                <div>
                  <h3 className="text-xs font-black tracking-widest text-zinc-300 uppercase">ZONE 3: ENFORCEMENT LEDGER</h3>
                  <p className="text-xs text-zinc-500">Active SQLITE interface synchronized dynamically with deep-learning extraction modules</p>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
                  {/* Ledger categories matching original text specs */}
                  <div className="flex bg-zinc-950 p-1 rounded-md border border-zinc-850 text-xs">
                    <button
                      onClick={() => setLedgerCategory('Motorcycle')}
                      className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                        ledgerCategory === 'Motorcycle' ? 'bg-emerald-500 text-black' : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      🛵 Motorcycles Ledger ({SNAPSHOTS_DATABASE.filter(s => s.className === 'Motorcycle').length})
                    </button>
                    <button
                      onClick={() => setLedgerCategory('Auto-rickshaw')}
                      className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                        ledgerCategory === 'Auto-rickshaw' ? 'bg-emerald-500 text-black' : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      🛺 Auto-Rickshaws ({SNAPSHOTS_DATABASE.filter(s => s.className === 'Auto-rickshaw').length})
                    </button>
                    <button
                      onClick={() => setLedgerCategory('Large Vehicles')}
                      className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                        ledgerCategory === 'Large Vehicles' ? 'bg-emerald-500 text-black' : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      🚛 Large Vehicles ({SNAPSHOTS_DATABASE.filter(s => ['Car', 'Bus'].includes(s.className)).length})
                    </button>
                  </div>

                  {/* Search filter */}
                  <div className="relative flex-grow lg:flex-grow-0">
                    <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-zinc-500" />
                    <input 
                      type="text"
                      placeholder="Filter Plates..."
                      value={ledgerSearchQuery}
                      onChange={(e) => setLedgerSearchQuery(e.target.value)}
                      className="bg-zinc-950 border border-zinc-850 text-zinc-300 text-xs rounded pl-9 pr-4 py-2 w-full lg:w-44 outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto border border-zinc-850 rounded-lg">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-zinc-950 border-b border-zinc-850 text-[10px] text-zinc-400 tracking-wider">
                      <th className="p-3">ID</th>
                      <th className="p-3">TIMESTAMP</th>
                      <th className="p-3">CLASSIFICATION</th>
                      <th className="p-3">VELOCITY</th>
                      <th className="p-3">ASSIGNED PLATE</th>
                      <th className="p-3">STATUS</th>
                      <th className="p-3 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-850 text-xs text-zinc-300">
                    {SNAPSHOTS_DATABASE
                      .filter(snap => {
                        if (ledgerCategory === 'Motorcycle') return snap.className === 'Motorcycle';
                        if (ledgerCategory === 'Auto-rickshaw') return snap.className === 'Auto-rickshaw';
                        return ['Car', 'Bus'].includes(snap.className);
                      })
                      .filter(snap => snap.plateNumber.toLowerCase().includes(ledgerSearchQuery.toLowerCase()))
                      .map((snap) => (
                        <tr key={snap.id} className="hover:bg-zinc-900/30 transition-colors">
                          <td className="p-3 font-semibold text-emerald-500">#{snap.trackId}</td>
                          <td className="p-3 text-zinc-400 font-mono">{snap.timestamp.split(' ')[1]}</td>
                          <td className="p-3">{snap.className}</td>
                          <td className="p-3 font-semibold text-yellow-500">{snap.speed} km/h</td>
                          <td className="p-3 font-mono bg-zinc-950/40 border border-zinc-900 px-2 py-0.5 rounded w-fit">{snap.plateNumber}</td>
                          <td className="p-3">
                            {snap.violationType ? (
                              <span className="text-red-400 flex items-center gap-1.5 font-bold">
                                ❌ Alert
                              </span>
                            ) : (
                              <span className="text-emerald-400 flex items-center gap-1.5 font-bold">
                                ✅ Clear
                              </span>
                            )}
                          </td>
                          <td className="p-3 text-right">
                            <button
                              onClick={() => handleOpenReview(snap.trackId)}
                              className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 hover:text-white border border-zinc-700 text-zinc-300 rounded text-[10px] font-bold tracking-wide transition-colors"
                            >
                              [Review]
                            </button>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        )}

        {/* ============================================================================
            ROUTE 2: ENHANCED SNAPSHOTS GALLERY (REQUIREMENT 1)
            ============================================================================ */}
        {activeTab === 'snapshots' && (
          <div className="flex flex-col gap-6 animate-fade-in">
            
            {/* Gallery Control Panel */}
            <div className="bg-zinc-900/60 rounded-xl p-4 border border-zinc-800 flex flex-col md:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-black tracking-widest text-zinc-300 uppercase">EVIDENTIARY RECOVERY & OCR AUDIT</h3>
                <p className="text-xs text-zinc-500">Real-ESRGAN enhanced 4x super-resolution snapshots and license plate read diagnostics</p>
              </div>

              <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                <div className="flex bg-zinc-950 p-1 rounded-md border border-zinc-850 text-xs">
                  {['All', 'Motorcycle', 'Auto-rickshaw', 'Car', 'Bus'].map(cls => (
                    <button
                      key={cls}
                      onClick={() => setGalleryFilterClass(cls)}
                      className={`px-3 py-1 rounded transition-all ${
                        galleryFilterClass === cls 
                          ? 'bg-emerald-500 text-black font-bold' 
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      {cls}
                    </button>
                  ))}
                </div>

                <div className="relative flex-grow md:flex-grow-0">
                  <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-zinc-500" />
                  <input 
                    type="text"
                    placeholder="Search plate..."
                    value={gallerySearch}
                    onChange={(e) => setGallerySearch(e.target.value)}
                    className="bg-zinc-950 border border-zinc-850 text-zinc-300 text-xs rounded pl-9 pr-4 py-2 w-full md:w-56 outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
            </div>

            {/* SNAPSHOTS COMPACT GRID CONTAINER */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {SNAPSHOTS_DATABASE
                .filter(snap => galleryFilterClass === 'All' || snap.className === galleryFilterClass)
                .filter(snap => snap.plateNumber.toLowerCase().includes(gallerySearch.toLowerCase()))
                .map((snap) => (
                  <div 
                    key={snap.id}
                    onClick={() => setSelectedGallerySnapshot(snap)}
                    className="group bg-zinc-900/30 border border-zinc-850 hover:border-emerald-500/50 rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:shadow-lg hover:shadow-emerald-500/5 hover:-translate-y-1 flex flex-col justify-between"
                  >
                    <div className="relative h-48 bg-black overflow-hidden">
                      <img 
                        src={snap.rawImage} 
                        alt="Raw crop" 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-80"
                      />
                      
                      <div className="absolute top-3 left-3 flex flex-col gap-1.5 z-10">
                        <span className="text-[9px] bg-zinc-950/80 text-zinc-300 border border-zinc-800 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                          {snap.className}
                        </span>
                        {snap.violationType && (
                          <span className="text-[9px] bg-red-950/90 text-red-300 border border-red-900 px-2 py-0.5 rounded font-bold uppercase">
                            Violation Triggered
                          </span>
                        )}
                      </div>

                      <div className="absolute bottom-3 right-3 bg-emerald-950/90 text-emerald-300 border border-emerald-800 rounded px-2.5 py-1 text-[9px] font-bold flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                        Real-ESRGAN Optimized
                      </div>
                    </div>

                    <div className="p-4 border-t border-zinc-850/80 flex items-center justify-between bg-zinc-950/20">
                      <div>
                        <span className="block text-[10px] text-zinc-500">PLATE NUMBER</span>
                        <span className="font-mono text-sm font-black text-zinc-200 tracking-wider bg-zinc-900 px-2 py-0.5 border border-zinc-800 rounded">
                          {snap.plateNumber}
                        </span>
                      </div>

                      <div className="text-right">
                        <span className="block text-[10px] text-zinc-500">REAL SPEED</span>
                        <span className="text-xs font-bold text-yellow-500">{snap.speed} km/h</span>
                      </div>
                    </div>

                    <div className="px-4 py-2 bg-zinc-950/80 border-t border-zinc-900 text-[10px] text-zinc-500 flex items-center justify-between">
                      <span>Launch Interactive Comparison Lens Slider</span>
                      <ArrowRight className="w-3 h-3 text-emerald-500 group-hover:translate-x-1 transition-transform" />
                    </div>

                  </div>
                ))}
            </div>

            {/* INTERACTIVE ZOOM MODAL (WITH ACCURATE PLATE BOX DISPLAY - REQUIREMENT 1) */}
            {selectedGallerySnapshot && (
              <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col animate-fade-in">
                  
                  <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="bg-emerald-500/10 p-2 rounded border border-emerald-500/20 text-emerald-400">
                        <Cpu className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-black tracking-wider text-zinc-200">EVIDENTIARY ANALYSIS: ID #{selectedGallerySnapshot.trackId}</h3>
                        <p className="text-[10px] text-zinc-500">{selectedGallerySnapshot.timestamp}</p>
                      </div>
                    </div>
                    <button 
                      onClick={() => setSelectedGallerySnapshot(null)}
                      className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-100 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-y-auto">
                    
                    {/* Double image comparison lens slider */}
                    <div className="lg:col-span-2 flex flex-col gap-4">
                      <span className="text-xs font-black text-zinc-400 uppercase tracking-widest block">COMPARISON LENS SLIDER</span>
                      
                      <div className="relative aspect-video rounded-xl overflow-hidden border border-zinc-950 bg-black select-none">
                        {/* Base: Enhanced Real-ESRGAN */}
                        <img 
                          src={selectedGallerySnapshot.enhancedImage} 
                          alt="Enhanced"
                          className="absolute inset-0 w-full h-full object-cover"
                        />

                        {/* Slide Overlay: Raw crop */}
                        <div 
                          className="absolute inset-0"
                          style={{ clipPath: `polygon(0 0, ${lensSliderPosition}% 0, ${lensSliderPosition}% 100%, 0 100%)` }}
                        >
                          <img 
                            src={selectedGallerySnapshot.rawImage} 
                            alt="Raw blurred"
                            className="absolute inset-0 w-full h-full object-cover filter blur-[2px] brightness-75"
                          />
                        </div>

                        {/* Slider divider line */}
                        <div 
                          className="absolute top-0 bottom-0 w-1 bg-emerald-500 cursor-ew-resize z-20 shadow-[0_0_12px_rgba(16,185,129,0.8)]"
                          style={{ left: `${lensSliderPosition}%` }}
                        >
                          <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-emerald-500 border-4 border-zinc-900 flex items-center justify-center text-zinc-950 shadow-lg">
                            <Sliders className="w-3.5 h-3.5 rotate-90" />
                          </div>
                        </div>

                        {/* Range slider context */}
                        <input 
                          type="range"
                          min="0"
                          max="100"
                          value={lensSliderPosition}
                          onChange={(e) => setLensSliderPosition(Number(e.target.value))}
                          className="absolute inset-0 opacity-0 cursor-ew-resize z-30"
                        />

                        <div className="absolute bottom-3 left-3 bg-zinc-950/80 border border-zinc-850 rounded px-2 py-0.5 text-[10px] text-zinc-400 z-10">
                          Original Frame Crop
                        </div>
                        <div className="absolute bottom-3 right-3 bg-emerald-950/80 border border-emerald-850 rounded px-2 py-0.5 text-[10px] text-emerald-400 z-10 font-bold">
                          Real-ESRGAN Restored Plate
                        </div>

                        {/* ==========================================================
                            FLOATING TOP-RIGHT LICENSE PLATE CARD (REQUIREMENT 1)
                            ========================================================== */}
                        <div className="absolute top-4 right-4 z-40 bg-zinc-950/95 border-2 border-emerald-500 rounded-xl p-3 shadow-2xl max-w-xs backdrop-blur-sm">
                          <span className="block text-[8px] text-zinc-500 font-bold tracking-widest uppercase">READ LICENSE VALUE</span>
                          <span className="block font-mono text-xl font-black text-white tracking-widest my-1 border-b border-zinc-900 pb-1.5">
                            {selectedGallerySnapshot.plateNumber}
                          </span>
                          
                          <div className="flex flex-col gap-1 mt-2">
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-zinc-500">OCR Engine:</span>
                              <span className="font-bold text-emerald-400">{selectedGallerySnapshot.ocrMethod}</span>
                            </div>
                            <div className="flex items-center justify-between text-[10px]">
                              <span className="text-zinc-500">Confidence:</span>
                              <span className="font-bold text-yellow-500">{selectedGallerySnapshot.confidence}%</span>
                            </div>
                          </div>
                        </div>

                      </div>

                      <p className="text-zinc-500 text-[10px] text-center">
                        ↔️ Drag your cursor or tap across the image to evaluate enhancement difference.
                      </p>
                    </div>

                    {/* Telemetry data side board */}
                    <div className="flex flex-col gap-4">
                      <span className="text-xs font-black text-zinc-400 uppercase tracking-widest block">TELEMETRY PROPERTIES</span>
                      
                      <div className="bg-zinc-950 rounded-xl p-4 border border-zinc-850/60 flex flex-col gap-4">
                        <div>
                          <span className="block text-[10px] text-zinc-500">ASSIGNED VEHICLE CATEGORY</span>
                          <span className="text-xs font-bold text-zinc-300">{selectedGallerySnapshot.className}</span>
                        </div>

                        <div>
                          <span className="block text-[10px] text-zinc-500">SPEED DETECTED</span>
                          <span className="text-xs font-bold text-yellow-500">{selectedGallerySnapshot.speed} km/h</span>
                        </div>

                        <div>
                          <span className="block text-[10px] text-zinc-500">EVIDENTIARY DATE</span>
                          <span className="text-xs font-mono text-zinc-400">{selectedGallerySnapshot.timestamp}</span>
                        </div>

                        <div>
                          <span className="block text-[10px] text-zinc-500">LOCAL REGISTRATION DB CHECK</span>
                          <span className="text-xs font-bold text-emerald-400">Validated License Consensus</span>
                        </div>

                        <div className="border-t border-zinc-900 pt-3">
                          <span className="block text-[10px] text-zinc-500 mb-1">VIOLATION ALERT RECORD</span>
                          {selectedGallerySnapshot.violationType ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-950/60 border border-rose-800 text-rose-300 font-bold text-[10px]">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              {selectedGallerySnapshot.violationType}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-400 font-bold text-[10px]">
                              <CheckCircle className="w-3.5 h-3.5" />
                              No Violations Logged
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mt-auto flex flex-col gap-2">
                        <button 
                          onClick={() => {
                            setActiveLogs(prev => [
                              ...prev,
                              { time: '16:14:45', message: `✅ [VERIFIED] Manual audit verified Plate registration: ${selectedGallerySnapshot.plateNumber}`, type: 'info' }
                            ]);
                            setSelectedGallerySnapshot(null);
                          }}
                          className="w-full bg-emerald-500 hover:bg-emerald-400 text-black py-2.5 rounded-lg text-xs font-bold transition-all shadow-lg hover:shadow-emerald-500/10 active:scale-95"
                        >
                          CONFIRM PLATE INTEGRITY
                        </button>
                        <button 
                          onClick={() => setSelectedGallerySnapshot(null)}
                          className="w-full bg-zinc-800 hover:bg-zinc-700 hover:text-white border border-zinc-700 text-zinc-300 py-2.5 rounded-lg text-xs font-bold transition-all"
                        >
                          CLOSE AUDIT WINDOW
                        </button>
                      </div>

                    </div>

                  </div>

                </div>
              </div>
            )}

          </div>
        )}

        {/* ============================================================================
            ROUTE 3: CSV LEDGER EXPLORER (REQUIREMENT 2)
            ============================================================================ */}
        {activeTab === 'csv-explorer' && (
          <div className="flex flex-col gap-6 animate-fade-in">
            
            <div className="bg-zinc-900/60 rounded-xl p-5 border border-zinc-800">
              <h3 className="text-sm font-black tracking-widest text-zinc-300 uppercase">FLAT-FILE CSV REPORT DATABASE</h3>
              <p className="text-xs text-zinc-500">Inspect raw tabular reports generated by the background tracking routines in a standard SQL layout grid.</p>
            </div>

            {/* DUAL PANE CONTROL ENVIRONMENT */}
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 items-start">
              
              {/* LEFT HAND CONTROL PANE: AVAILABLE CSV FILE DIRECTORY */}
              <div className="xl:col-span-1 bg-zinc-900/40 p-4 rounded-xl border border-zinc-800 flex flex-col gap-4">
                <span className="text-[10px] text-zinc-500 font-bold tracking-wider uppercase block border-b border-zinc-800 pb-2">
                  System CSV Directory
                </span>

                <div className="flex flex-col gap-2">
                  {MOCK_CSV_DATABASE.map((file) => {
                    const isActive = selectedCSVFile.name === file.name;
                    return (
                      <div
                        key={file.name}
                        onClick={() => {
                          setSelectedCSVFile(file);
                          setCsvSearchQuery('');
                        }}
                        className={`p-3 rounded-lg border cursor-pointer select-none transition-all ${
                          isActive 
                            ? 'bg-emerald-500/10 border-emerald-500 shadow-md shadow-emerald-500/5' 
                            : 'bg-zinc-950/40 border-zinc-850 hover:bg-zinc-900 hover:border-zinc-700'
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <FileText className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
                          <span className={`text-xs font-semibold ${isActive ? 'text-emerald-400' : 'text-zinc-300'}`}>
                            {file.name}
                          </span>
                        </div>
                        
                        <div className="mt-2.5 flex items-center justify-between text-[9px] text-zinc-500">
                          <span>{file.recordsCount} Records</span>
                          <span>{file.size}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="mt-4 p-3 bg-zinc-950/60 rounded border border-zinc-850/60 text-[10px] text-zinc-500 leading-relaxed">
                  💡 Clicking a ledger loads the parsed array directly into the database explorer table.
                </div>
              </div>

              {/* RIGHT HAND COLUMN: STRUCTURED SQL-LIKE GRID */}
              <div className="xl:col-span-3 bg-zinc-900/40 p-5 rounded-xl border border-zinc-800 flex flex-col gap-4">
                
                {/* Search & Statistics Filter Row */}
                <div className="flex flex-col md:flex-row items-center justify-between gap-4 border-b border-zinc-850 pb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-xs bg-emerald-950/80 text-emerald-300 border border-emerald-800 px-2.5 py-1 rounded font-bold font-mono">
                      SQL_VIEW
                    </span>
                    <div>
                      <h4 className="text-xs font-bold text-zinc-300">{selectedCSVFile.name}</h4>
                      <p className="text-[10px] text-zinc-500">Last Synced: {selectedCSVFile.lastUpdated}</p>
                    </div>
                  </div>

                  <div className="relative w-full md:w-64">
                    <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-zinc-500" />
                    <input 
                      type="text"
                      placeholder="SQL Like Filter..."
                      value={csvSearchQuery}
                      onChange={(e) => setCsvSearchQuery(e.target.value)}
                      className="bg-zinc-950 border border-zinc-850 text-zinc-300 text-xs rounded pl-9 pr-4 py-2 w-full outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                {/* Database Table Layout */}
                <div className="overflow-x-auto border border-zinc-850 rounded-lg">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-zinc-950 border-b border-zinc-850 text-[10px] text-zinc-400 tracking-wider">
                        {selectedCSVFile.headers.map((header) => (
                          <th key={header} className="p-3">{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-850 text-xs text-zinc-300 font-mono">
                      {selectedCSVFile.rows
                        .filter(row => {
                          if (!csvSearchQuery) return true;
                          return Object.values(row).some(val => 
                            String(val).toLowerCase().includes(csvSearchQuery.toLowerCase())
                          );
                        })
                        .map((row, index) => (
                          <tr key={index} className="hover:bg-zinc-900/30 transition-all">
                            {selectedCSVFile.headers.map((header) => {
                              const cellValue = row[header];
                              let cellClass = "";
                              
                              if (header === 'Tracking_ID') cellClass = "text-emerald-400 font-bold";
                              if (header === 'Read_Number_Plate' || header === 'Plate_Consensus_String') cellClass = "font-black bg-zinc-950/40 border border-zinc-900 px-1.5 py-0.5 rounded";
                              if (header === 'Velocity_KMPH') cellClass = "text-yellow-500 font-semibold";
                              if (cellValue === 'CRITICAL' || cellValue === 'FAIL' || cellValue === 'NO') cellClass = "text-red-400 font-extrabold";
                              if (cellValue === 'PASS' || cellValue === 'YES') cellClass = "text-emerald-400 font-bold";
                              
                              return (
                                <td key={header} className={`p-3 border-r border-zinc-850/40 last:border-0 ${cellClass}`}>
                                  {String(cellValue)}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      {selectedCSVFile.rows.length === 0 && (
                        <tr>
                          <td colSpan={selectedCSVFile.headers.length} className="p-8 text-center text-zinc-500">
                            No records detected matching database specifications.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="flex items-center justify-between text-[10px] text-zinc-500 pt-2">
                  <span>Showing {selectedCSVFile.rows.length} rows inside compiled flat storage matrix</span>
                  <span>Database Protocol: ANSI Format</span>
                </div>

              </div>

            </div>

          </div>
        )}

        {/* ============================================================================
            RIGHT WORKSPACE SIDE SLIDE-OUT PANEL (GENERAL REVIEW DRAWER)
            ============================================================================ */}
        {isReviewDrawerOpen && selectedReviewTrack && (
          <div className="fixed inset-0 bg-black/65 backdrop-blur-sm z-40 flex justify-end">
            <div className="w-full max-w-lg bg-zinc-900 border-l border-zinc-800 p-6 flex flex-col justify-between shadow-2xl h-full overflow-y-auto animate-slide-in">
              
              <div>
                <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                    <h3 className="text-xs font-black tracking-widest text-zinc-300 uppercase">
                      EVIDENTIARY AUDIT: TRACK #{selectedReviewTrack.trackId}
                    </h3>
                  </div>
                  <button 
                    onClick={() => setIsReviewDrawerOpen(false)}
                    className="p-1 hover:bg-zinc-800 rounded transition-colors text-zinc-400 hover:text-zinc-200"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex flex-col gap-4">
                  <span className="text-[10px] text-zinc-500 font-bold tracking-widest uppercase">Multi-Frame Crop Selections</span>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-zinc-950 p-2 rounded-lg border border-zinc-850 text-center">
                      <span className="block text-[8px] text-zinc-500 mb-1">ORIGINAL BLURRY CROP</span>
                      <img 
                        src={selectedReviewTrack.rawImage} 
                        alt="Raw vehicle crop" 
                        className="w-full h-32 object-cover rounded border border-zinc-900 filter blur-[1px] brightness-75"
                      />
                    </div>
                    <div className="bg-zinc-950 p-2 rounded-lg border border-emerald-500 text-center">
                      <span className="block text-[8px] text-emerald-400 font-bold mb-1">REAL-ESRGAN ENHANCED</span>
                      <img 
                        src={selectedReviewTrack.enhancedImage} 
                        alt="Real-ESRGAN output" 
                        className="w-full h-32 object-cover rounded border border-zinc-900"
                      />
                    </div>
                  </div>

                  <div className="bg-zinc-950 rounded-xl p-4 border border-zinc-850 flex flex-col gap-3.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500">Evaluated Real Speed:</span>
                      <span className="font-bold text-yellow-500">{selectedReviewTrack.speed} km/h</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500">Temporal Plate Readout:</span>
                      <span className="font-mono font-black text-zinc-200 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-850">
                        {selectedReviewTrack.plateNumber}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500">Consensus Core Confidence:</span>
                      <span className="font-bold text-emerald-400">{selectedReviewTrack.confidence}%</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-zinc-500">Inference Engine Route:</span>
                      <span className={`px-2 py-0.5 rounded border text-[10px] ${getBadgeColor(selectedReviewTrack.ocrMethod)}`}>
                        {selectedReviewTrack.ocrMethod}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-6 border-t border-zinc-850 flex flex-col gap-2 mt-6">
                <button
                  onClick={() => {
                    setActiveLogs(prev => [
                      ...prev,
                      { time: '16:14:50', message: `👍 [CONFIRMED] Track #${selectedReviewTrack.trackId} verified manually. License registered: ${selectedReviewTrack.plateNumber}`, type: 'info' }
                    ]);
                    setIsReviewDrawerOpen(false);
                  }}
                  className="w-full bg-emerald-500 hover:bg-emerald-400 text-black py-2.5 rounded text-xs font-black tracking-wide transition-all active:scale-95 shadow-lg shadow-emerald-500/10"
                >
                  VERIFY LICENSE INTEGRITY
                </button>
                <button
                  onClick={() => {
                    setActiveLogs(prev => [
                      ...prev,
                      { time: '16:14:55', message: `❌ [REJECTED] Track #${selectedReviewTrack.trackId} reported as false positive.`, type: 'warning' }
                    ]);
                    setIsReviewDrawerOpen(false);
                  }}
                  className="w-full bg-zinc-800 hover:bg-zinc-700 hover:text-white border border-zinc-700 text-zinc-300 py-2.5 rounded text-xs font-black tracking-wide transition-all"
                >
                  REPORT FALSE POSITIVE
                </button>
              </div>

            </div>
          </div>
        )}

      </main>

      {/* FOOTER METRIC DECK */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-4 px-6 text-center text-zinc-600 text-[10px] tracking-wider">
        <p>© 2026 Smart Road Vision System (SRVS V4) | Karachi Operations Control Hub | Designed with TypeScript React Framework</p>
      </footer>

    </div>
  );
}