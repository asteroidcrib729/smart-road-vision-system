import React, { useState } from 'react';
import { Cpu, RefreshCw, Download, AlertCircle } from 'lucide-react';

interface SessionControlPanelProps {
  activeMediaFeed: string;
  setActiveMediaFeed: (feed: string) => void;
  mediaFeeds: string[];
  isProcessing: boolean;
  onStartProcessing: () => void;
  processProgress: number;
  onReset: () => void;
  onDownloadDriveVideo: (fileId: string) => Promise<void>;
  isDownloading: boolean;
  downloadError: string | null;
}

export default function SessionControlPanel({
  activeMediaFeed,
  setActiveMediaFeed,
  mediaFeeds,
  isProcessing,
  onStartProcessing,
  processProgress,
  onReset,
  onDownloadDriveVideo,
  isDownloading,
  downloadError
}: SessionControlPanelProps) {
  const [driveUrl, setDriveUrl] = useState<string>('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const extractFileId = (url: string): string | null => {
    // Matches standard drive file links like: https://drive.google.com/file/d/FILE_ID/view...
    const regExp = /\/file\/d\/([a-zA-Z0-9-_]{33,40})/;
    const match = url.match(regExp);
    return match ? match[1] : null;
  };

  const handleDownloadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!driveUrl) {
      setValidationError("Please paste a Google Drive link.");
      return;
    }

    const fileId = extractFileId(driveUrl);
    if (!fileId) {
      setValidationError("Invalid Google Drive URL. Ensure it contains '/file/d/FILE_ID'.");
      return;
    }

    try {
      await onDownloadDriveVideo(fileId);
      setDriveUrl(''); // Clear input on success
    } catch (err: any) {
      // handled by parent
    }
  };

  return (
    <div className="bg-zinc-900/60 rounded-xl p-5 border border-zinc-800/85 flex flex-col gap-4">
      <div className="flex flex-col xl:flex-row items-stretch xl:items-center justify-between gap-4">
        
        {/* Dropdown Selector */}
        <div className="flex flex-wrap items-center gap-4 w-full xl:w-auto">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] text-zinc-500 font-bold tracking-wider">SELECT ACTIVE VIDEO STREAM</span>
            <select 
              value={activeMediaFeed}
              onChange={(e) => setActiveMediaFeed(e.target.value)}
              disabled={isProcessing}
              className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded px-3 py-2 outline-none focus:border-emerald-500 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed font-mono w-full sm:w-[480px]"
            >
              {mediaFeeds.map(feed => (
                <option key={feed} value={feed}>
                  {feed.startsWith("1") ? `Drive: ${feed.substring(0, 8)}... (${feed})` : `Stream: ${feed}`}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-3 self-end">
            <button 
              onClick={onStartProcessing}
              disabled={isProcessing || isDownloading}
              className={`flex items-center gap-2 px-5 py-2 rounded text-xs font-bold transition-all cursor-pointer ${
                isProcessing 
                  ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed' 
                  : 'bg-emerald-500 hover:bg-emerald-400 text-black hover:scale-[1.02] active:scale-95'
              }`}
            >
              <Cpu className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
              {isProcessing ? 'RUNNING PROCESSING CORE...' : '▶ RUN ENGINE'}
            </button>
            
            <button 
              onClick={onReset}
              className="flex items-center gap-2 px-3 py-2 bg-red-950/60 hover:bg-red-800 text-red-200 hover:text-white border border-red-900 hover:border-red-700 rounded text-xs font-bold transition-all cursor-pointer hover:scale-[1.02] active:scale-95 shadow-[0_0_8px_rgba(220,38,38,0.15)]"
              title="Interrupt Engine & Reset Workspace"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>INTERRUPT ENGINE</span>
            </button>
          </div>
        </div>

        {/* Google Drive Link Download Form */}
        <form onSubmit={handleDownloadSubmit} className="flex-grow xl:max-w-md flex flex-col gap-1">
          <span className="text-[10px] text-zinc-500 font-bold tracking-wider">INGEST REMOTE VIDEO (GOOGLE DRIVE)</span>
          <div className="flex gap-2">
            <input 
              type="text"
              placeholder="Paste Google Drive shareable link..."
              value={driveUrl}
              onChange={(e) => setDriveUrl(e.target.value)}
              disabled={isDownloading || isProcessing}
              className="bg-zinc-950 border border-zinc-850 text-zinc-300 text-xs rounded px-3 py-2 outline-none focus:border-emerald-500 w-full font-mono disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isDownloading || isProcessing}
              className="px-4 py-2 bg-zinc-800 hover:bg-zinc-750 border border-zinc-700 text-zinc-200 rounded text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
            >
              {isDownloading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                  INGESTING...
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5" />
                  INGEST
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Ingestion Engine state indicators */}
      <div className="border-t border-zinc-900 pt-3 mt-1 flex flex-col gap-2">
        {(validationError || downloadError) && (
          <div className="flex items-center gap-2 text-rose-400 text-[10px] font-bold">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{validationError || downloadError}</span>
          </div>
        )}
        <div className="w-full flex items-center gap-4 bg-zinc-950 p-2.5 rounded border border-zinc-800/60">
          <div className="flex-grow">
            <div className="flex justify-between items-center mb-1 text-[10px] font-bold text-zinc-400">
              <span>INGESTION STATUS</span>
              <span className="text-emerald-400">{isProcessing ? `${Math.floor(processProgress)}%` : 'READY'}</span>
            </div>
            <div className="w-full h-1 bg-zinc-900 rounded-full overflow-hidden">
              <div 
                className="h-full bg-emerald-500 transition-all duration-300 shadow-[0_0_8px_rgba(16,185,129,0.5)]"
                style={{ width: `${isProcessing ? processProgress : 100}%` }}
              />
            </div>
          </div>
          <div className="text-right shrink-0">
            <span className="block text-[8px] text-zinc-500">INGESTION Cadence</span>
            <span className="text-[10px] text-yellow-500 font-bold">60Hz QHD</span>
          </div>
        </div>
      </div>
    </div>
  );
}
