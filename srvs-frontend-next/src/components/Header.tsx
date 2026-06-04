import React from 'react';
import { Cpu, LayoutDashboard, Image as ImageIcon, FileSpreadsheet } from 'lucide-react';

interface HeaderProps {
  activeTab: 'dashboard' | 'snapshots' | 'csv-explorer';
  setActiveTab: (tab: 'dashboard' | 'snapshots' | 'csv-explorer') => void;
  onTabChange?: () => void;
}

export default function Header({ activeTab, setActiveTab, onTabChange }: HeaderProps) {
  const handleTabClick = (tab: 'dashboard' | 'snapshots' | 'csv-explorer') => {
    setActiveTab(tab);
    if (onTabChange) onTabChange();
  };

  return (
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
            onClick={() => handleTabClick('dashboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'dashboard' 
                ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/10' 
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            MONITOR HUB
          </button>
          <button
            onClick={() => handleTabClick('snapshots')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'snapshots' 
                ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/10' 
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <ImageIcon className="w-3.5 h-3.5" />
            ENHANCED GALLERY
          </button>
          <button
            onClick={() => handleTabClick('csv-explorer')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-bold transition-all cursor-pointer ${
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
  );
}
