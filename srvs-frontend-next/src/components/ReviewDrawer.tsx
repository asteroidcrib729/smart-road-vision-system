import React from 'react';
import { X } from 'lucide-react';
import { EnhancedSnapshot } from './types';

interface ReviewDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  track: EnhancedSnapshot | null;
  onConfirm: (trackId: number, plateNumber: string) => void;
  onReject: (trackId: number) => void;
}

export default function ReviewDrawer({
  isOpen,
  onClose,
  track,
  onConfirm,
  onReject
}: ReviewDrawerProps) {
  if (!isOpen || !track) return null;

  const getBadgeColor = (method: string) => {
    return method.includes('Gemini') 
      ? 'bg-purple-950/80 text-purple-300 border-purple-800' 
      : 'bg-indigo-950/80 text-indigo-300 border-indigo-800';
  };

  return (
    <div className="fixed inset-0 bg-black/65 backdrop-blur-sm z-40 flex justify-end">
      {/* Background click close */}
      <div className="absolute inset-0" onClick={onClose} />
      
      <div className="w-full max-w-lg bg-zinc-900 border-l border-zinc-800 p-6 flex flex-col justify-between shadow-2xl h-full overflow-y-auto animate-slide-in relative z-50">
        
        <div>
          <div className="flex items-center justify-between border-b border-zinc-800 pb-4 mb-6">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
              <h3 className="text-xs font-black tracking-widest text-zinc-300 uppercase">
                EVIDENTIARY AUDIT: TRACK #{track.trackId}
              </h3>
            </div>
            <button 
              onClick={onClose}
              className="p-1 hover:bg-zinc-800 rounded transition-colors text-zinc-400 hover:text-zinc-200 cursor-pointer"
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
                  src={track.rawImage} 
                  alt="Raw vehicle crop" 
                  className="w-full h-32 object-cover rounded border border-zinc-900 filter blur-[1px] brightness-75"
                />
              </div>
              <div className="bg-zinc-950 p-2 rounded-lg border border-emerald-500 text-center">
                <span className="block text-[8px] text-emerald-400 font-bold mb-1">REAL-ESRGAN ENHANCED</span>
                <img 
                  src={track.enhancedImage} 
                  alt="Real-ESRGAN output" 
                  className="w-full h-32 object-cover rounded border border-zinc-900"
                />
              </div>
            </div>

            <div className="bg-zinc-950 rounded-xl p-4 border border-zinc-850 flex flex-col gap-3.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-zinc-500 font-mono">Evaluated Real Speed:</span>
                <span className="font-bold text-yellow-500 font-mono">{track.speed} km/h</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-zinc-500 font-mono">Temporal Plate Readout:</span>
                <span className="font-mono font-black text-zinc-200 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-850">
                  {track.plateNumber}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-zinc-500 font-mono">Consensus Core Confidence:</span>
                <span className="font-bold text-emerald-400 font-mono">{track.confidence}%</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-zinc-500 font-mono">Inference Engine Route:</span>
                <span className={`px-2 py-0.5 rounded border text-[10px] font-mono ${getBadgeColor(track.ocrMethod)}`}>
                  {track.ocrMethod}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-zinc-850 flex flex-col gap-2 mt-6">
          <button
            onClick={() => onConfirm(track.trackId, track.plateNumber)}
            className="w-full bg-emerald-500 hover:bg-emerald-400 text-black py-2.5 rounded text-xs font-black tracking-wide transition-all active:scale-95 shadow-lg shadow-emerald-500/10 cursor-pointer"
          >
            VERIFY LICENSE INTEGRITY
          </button>
          <button
            onClick={() => onReject(track.trackId)}
            className="w-full bg-zinc-800 hover:bg-zinc-700 hover:text-white border border-zinc-700 text-zinc-300 py-2.5 rounded text-xs font-black tracking-wide transition-all cursor-pointer"
          >
            REPORT FALSE POSITIVE
          </button>
        </div>

      </div>
    </div>
  );
}
