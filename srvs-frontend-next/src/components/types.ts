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

export interface ToggleState {
  showBBoxes: boolean;
  showVelocities: boolean;
  filterMotorcycles: boolean;
  filterLargeVehicles: boolean;
}

export interface PlaybackState {
  isPlaying: boolean;
  currentTime: number;
  totalDuration: number;
  computedFrame: number;
}

export interface EnhancedSnapshot {
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

export interface CSVFile {
  name: string;
  size: string;
  recordsCount: number;
  lastUpdated: string;
  headers: string[];
  rows: Record<string, string | number | boolean>[];
}

export interface LogEntry {
  time: string;
  message: string;
  type: 'info' | 'warning';
}
