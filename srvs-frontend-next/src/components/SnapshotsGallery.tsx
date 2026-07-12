import React, { useState } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { EnhancedSnapshot } from './types';

interface SnapshotsGalleryProps {
  snapshots: EnhancedSnapshot[];
  onSelect: (snap: EnhancedSnapshot) => void;
}

export default function SnapshotsGallery({ snapshots, onSelect }: SnapshotsGalleryProps) {
  const [galleryFilterClass, setGalleryFilterClass] = useState<string>('All');
  const [gallerySearch, setGallerySearch] = useState<string>('');

  const filteredSnapshots = snapshots
    .filter(snap => galleryFilterClass === 'All' || snap.className === galleryFilterClass)
    .filter(snap => snap.plateNumber.toLowerCase().includes(gallerySearch.toLowerCase()));

  return (
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
                className={`px-3 py-1 rounded transition-all cursor-pointer ${
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
              className="bg-zinc-950 border border-zinc-850 text-zinc-300 text-xs rounded pl-9 pr-4 py-2 w-full md:w-56 outline-none focus:border-emerald-500 font-mono"
            />
          </div>
        </div>
      </div>

      {/* SNAPSHOTS COMPACT GRID CONTAINER */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredSnapshots.map((snap) => (
          <div 
            key={snap.id}
            onClick={() => onSelect(snap)}
            className="group bg-zinc-900/30 border border-zinc-850 hover:border-emerald-500/50 rounded-xl overflow-hidden cursor-pointer transition-all duration-355 hover:shadow-lg hover:shadow-emerald-500/5 hover:-translate-y-1 flex flex-col justify-between"
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
                <span className="block text-[10px] text-zinc-500 font-mono">PLATE NUMBER</span>
                <span className="font-mono text-sm font-black text-zinc-200 tracking-wider bg-zinc-900 px-2 py-0.5 border border-zinc-800 rounded">
                  {snap.plateNumber}
                </span>
              </div>

              <div className="text-right">
                <span className="block text-[10px] text-zinc-500 font-mono">REAL SPEED</span>
                <span className="text-xs font-bold text-yellow-500 font-mono">{snap.speed} km/h</span>
              </div>
            </div>

            <div className="px-4 py-2 bg-zinc-950/80 border-t border-zinc-900 text-[10px] text-zinc-500 flex items-center justify-between font-mono">
              <span>Launch Interactive Comparison Lens Slider</span>
              <ArrowRight className="w-3 h-3 text-emerald-500 group-hover:translate-x-1 transition-transform" />
            </div>

          </div>
        ))}
        {filteredSnapshots.length === 0 && (
          <div className="col-span-full bg-zinc-900/10 border border-zinc-850 p-12 text-center text-zinc-500 rounded-xl font-mono">
            No evidentiary snapshots match filters.
          </div>
        )}
      </div>
    </div>
  );
}
