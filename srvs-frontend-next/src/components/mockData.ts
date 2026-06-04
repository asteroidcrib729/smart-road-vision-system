import { TelemetryMap, TrackData, LogEntry, EnhancedSnapshot, CSVFile } from './types';

export const MOCK_TELEMETRY: TelemetryMap = {};

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

export const INITIAL_LOGS: LogEntry[] = [
  { time: '16:14:02', message: 'SRVS System initialized on video stream source A.', type: 'info' },
  { time: '16:14:03', message: 'Database handler mapped to SQLite backend. 412 entries detected.', type: 'info' },
  { time: '16:14:04', message: 'Target homography warp matrix loaded successfully.', type: 'info' },
  { time: '16:14:05', message: 'Ready for engine execution. Click RUN ENGINE to begin pipeline ingestion.', type: 'warning' }
];

export const SNAPSHOTS_DATABASE: EnhancedSnapshot[] = [
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

export const MOCK_CSV_DATABASE: CSVFile[] = [
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
