import React, { useState } from 'react';
import { X, Cpu, Sliders, AlertTriangle, CheckCircle } from 'lucide-react';
import { EnhancedSnapshot } from './types';

interface ComparisonSliderModalProps {
  isOpen: boolean;
  onClose: () => void;
  snapshot: EnhancedSnapshot | null;
  onConfirm: (trackId: number, plateNumber: string) => void;
}

export default function ComparisonSliderModal({
  isOpen,
  onClose,
  snapshot,
  onConfirm
}: ComparisonSliderModalProps) {
  const [lensSliderPosition, setLensSliderPosition] = useState<number>(50); // percentage split comparison

  if (!isOpen || !snapshot) return null;

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Background click close */}
      <div className="absolute inset-0" onClick={onClose} />
      
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col animate-fade-in relative z-50">
        
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/10 p-2 rounded border border-emerald-500/20 text-emerald-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-black tracking-wider text-zinc-200">EVIDENTIARY ANALYSIS: ID #{snapshot.trackId}</h3>
              <p className="text-[10px] text-zinc-500">{snapshot.timestamp}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-y-auto">
          
          {/* Double image comparison lens slider */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <span className="text-xs font-black text-zinc-400 uppercase tracking-widest block font-mono">COMPARISON LENS SLIDER</span>
            
            <div className="relative aspect-video rounded-xl overflow-hidden border border-zinc-950 bg-black select-none">
              {/* Base: Enhanced Real-ESRGAN */}
              <img 
                src={snapshot.enhancedImage} 
                alt="Enhanced"
                className="absolute inset-0 w-full h-full object-cover"
              />

              {/* Slide Overlay: Raw crop */}
              <div 
                className="absolute inset-0"
                style={{ clipPath: `polygon(0 0, ${lensSliderPosition}% 0, ${lensSliderPosition}% 100%, 0 100%)` }}
              >
                <img 
                  src={snapshot.rawImage} 
                  alt="Raw blurred"
                  className="absolute inset-0 w-full h-full object-cover filter blur-[2px] brightness-75"
                />
              </div>

              {/* Slider divider line */}
              <div 
                className="absolute top-0 bottom-0 w-1 bg-emerald-500 cursor-ew-resize z-25 shadow-[0_0_12px_rgba(16,185,129,0.8)]"
                style={{ left: `${lensSliderPosition}%` }}
              >
                <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-emerald-500 border-4 border-zinc-900 flex items-center justify-center text-zinc-950 shadow-lg">
                  <Sliders className="w-3.5 h-3.5 rotate-90" />
                </div>
              </div>

              {/* Range slider input overlay */}
              <input 
                type="range"
                min="0"
                max="100"
                value={lensSliderPosition}
                onChange={(e) => setLensSliderPosition(Number(e.target.value))}
                className="absolute inset-0 opacity-0 cursor-ew-resize z-30 w-full h-full"
              />

              <div className="absolute bottom-3 left-3 bg-zinc-950/80 border border-zinc-850 rounded px-2 py-0.5 text-[10px] text-zinc-400 z-10 font-mono">
                Original Frame Crop
              </div>
              <div className="absolute bottom-3 right-3 bg-emerald-950/80 border border-emerald-850 rounded px-2 py-0.5 text-[10px] text-emerald-400 z-10 font-bold font-mono">
                Real-ESRGAN Restored Plate
              </div>

              {/* ==========================================================
                  FLOATING TOP-RIGHT LICENSE PLATE CARD (REQUIREMENT 1)
                  ========================================================== */}
              <div className="absolute top-4 right-4 z-40 bg-zinc-950/95 border-2 border-emerald-500 rounded-xl p-3 shadow-2xl max-w-xs backdrop-blur-sm">
                <span className="block text-[8px] text-zinc-500 font-bold tracking-widest uppercase font-mono">READ LICENSE VALUE</span>
                <span className="block font-mono text-xl font-black text-white tracking-widest my-1 border-b border-zinc-900 pb-1.5">
                  {snapshot.plateNumber}
                </span>
                
                <div className="flex flex-col gap-1 mt-2">
                  <div className="flex items-center justify-between text-[10px] gap-4 font-mono">
                    <span className="text-zinc-500">OCR Engine:</span>
                    <span className="font-bold text-emerald-400 text-right">{snapshot.ocrMethod}</span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-zinc-500">Confidence:</span>
                    <span className="font-bold text-yellow-500">{snapshot.confidence}%</span>
                  </div>
                </div>
              </div>

            </div>

            <p className="text-zinc-500 text-[10px] text-center font-mono">
              ↔️ Drag your cursor or tap across the image to evaluate enhancement difference.
            </p>
          </div>

          {/* Telemetry data side board */}
          <div className="flex flex-col gap-4">
            <span className="text-xs font-black text-zinc-400 uppercase tracking-widest block font-mono">TELEMETRY PROPERTIES</span>
            
            <div className="bg-zinc-950 rounded-xl p-4 border border-zinc-855/60 flex flex-col gap-4">
              <div>
                <span className="block text-[10px] text-zinc-500 font-mono">ASSIGNED VEHICLE CATEGORY</span>
                <span className="text-xs font-bold text-zinc-300 font-mono">{snapshot.className}</span>
              </div>

              <div>
                <span className="block text-[10px] text-zinc-500 font-mono">SPEED DETECTED</span>
                <span className="text-xs font-bold text-yellow-500 font-mono">{snapshot.speed} km/h</span>
              </div>

              <div>
                <span className="block text-[10px] text-zinc-500 font-mono">EVIDENTIARY DATE</span>
                <span className="text-xs font-mono text-zinc-400">{snapshot.timestamp}</span>
              </div>

              <div>
                <span className="block text-[10px] text-zinc-500 font-mono">LOCAL REGISTRATION DB CHECK</span>
                <span className="text-xs font-bold text-emerald-400 font-mono">Validated License Consensus</span>
              </div>

              <div className="border-t border-zinc-900 pt-3">
                <span className="block text-[10px] text-zinc-500 mb-1 font-mono">VIOLATION ALERT RECORD</span>
                {snapshot.violationType ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-950/60 border border-rose-800 text-rose-300 font-bold text-[10px] font-mono">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    {snapshot.violationType}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-400 font-bold text-[10px] font-mono">
                    <CheckCircle className="w-3.5 h-3.5" />
                    No Violations Logged
                  </span>
                )}
              </div>
            </div>

            <div className="mt-auto flex flex-col gap-2">
              <button 
                onClick={() => onConfirm(snapshot.trackId, snapshot.plateNumber)}
                className="w-full bg-emerald-500 hover:bg-emerald-400 text-black py-2.5 rounded-lg text-xs font-bold transition-all shadow-lg hover:shadow-emerald-500/10 active:scale-95 cursor-pointer font-mono"
              >
                CONFIRM PLATE INTEGRITY
              </button>
              <button 
                onClick={onClose}
                className="w-full bg-zinc-800 hover:bg-zinc-700 hover:text-white border border-zinc-700 text-zinc-300 py-2.5 rounded-lg text-xs font-bold transition-all cursor-pointer font-mono"
              >
                CLOSE AUDIT WINDOW
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}
