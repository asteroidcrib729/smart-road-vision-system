import React from 'react';
import { Cpu, RefreshCw } from 'lucide-react';

interface SessionControlPanelProps {
  activeMediaFeed: string;
  setActiveMediaFeed: (feed: string) => void;
  isProcessing: boolean;
  onStartProcessing: () => void;
  processProgress: number;
  onReset: () => void;
}

export default function SessionControlPanel({
  activeMediaFeed,
  setActiveMediaFeed,
  isProcessing,
  onStartProcessing,
  processProgress,
  onReset
}: SessionControlPanelProps) {
  return (
    <div className="bg-zinc-900/60 rounded-xl p-4 border border-zinc-800/85 flex flex-col xl:flex-row items-center justify-between gap-4">
      <div className="flex flex-wrap items-center gap-4 w-full xl:w-auto">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] text-zinc-500 font-bold tracking-wider">SELECT ACTIVE VIDEO STREAM</span>
          <select 
            value={activeMediaFeed}
            onChange={(e) => setActiveMediaFeed(e.target.value)}
            disabled={isProcessing}
            className="bg-zinc-950 border border-zinc-800 text-zinc-300 text-xs rounded px-3 py-2 outline-none focus:border-emerald-500 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed font-mono"
          >
            <option value="SRVS - Footage of Front Plates - New.mp4">Stream A: (FYP Front Plate Footage - 1440p @ 60 FPS)</option>
            <option value="SRVS - Footage of Rear Plates - Alt.mp4">Stream B: (FYP Rear Plate Footage - 1440p @ 60 FPS)</option>
          </select>
        </div>

        <div className="flex items-center gap-3 self-end">
          <button 
            onClick={onStartProcessing}
            disabled={isProcessing}
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
            className="p-2 bg-zinc-950 border border-zinc-800 hover:border-zinc-700 hover:text-zinc-200 text-zinc-400 rounded transition-all cursor-pointer"
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
  );
}
