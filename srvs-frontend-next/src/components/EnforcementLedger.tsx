import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { EnhancedSnapshot } from './types';

interface EnforcementLedgerProps {
  snapshots: EnhancedSnapshot[];
  onReview: (trackId: number) => void;
}

export default function EnforcementLedger({ snapshots, onReview }: EnforcementLedgerProps) {
  const [ledgerCategory, setLedgerCategory] = useState<'Motorcycle' | 'Auto-rickshaw' | 'Large Vehicles'>('Motorcycle');
  const [ledgerSearchQuery, setLedgerSearchQuery] = useState<string>('');

  const motorcyclesCount = snapshots.filter(s => s.className === 'Motorcycle').length;
  const rickshawsCount = snapshots.filter(s => s.className === 'Auto-rickshaw').length;
  const largeVehiclesCount = snapshots.filter(s => ['Car', 'Bus', 'Truck'].includes(s.className)).length;

  const filteredSnapshots = snapshots
    .filter(snap => {
      if (ledgerCategory === 'Motorcycle') return snap.className === 'Motorcycle';
      if (ledgerCategory === 'Auto-rickshaw') return snap.className === 'Auto-rickshaw';
      return ['Car', 'Bus', 'Truck'].includes(snap.className);
    })
    .filter(snap => snap.plateNumber.toLowerCase().includes(ledgerSearchQuery.toLowerCase()));

  return (
    <div className="bg-zinc-900/40 rounded-xl p-6 border border-zinc-800">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-zinc-800 pb-4 mb-6">
        <div>
          <h3 className="text-xs font-black tracking-widest text-zinc-300 uppercase">ZONE 3: ENFORCEMENT LEDGER</h3>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
          {/* Ledger categories */}
          <div className="flex bg-zinc-950 p-1 rounded-md border border-zinc-850 text-xs">
            <button
              onClick={() => setLedgerCategory('Motorcycle')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all cursor-pointer ${
                ledgerCategory === 'Motorcycle' ? 'bg-emerald-500 text-black' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              🛵 Motorcycles Ledger ({motorcyclesCount})
            </button>
            <button
              onClick={() => setLedgerCategory('Auto-rickshaw')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all cursor-pointer ${
                ledgerCategory === 'Auto-rickshaw' ? 'bg-emerald-500 text-black' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              🛺 Auto-Rickshaws ({rickshawsCount})
            </button>
            <button
              onClick={() => setLedgerCategory('Large Vehicles')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all cursor-pointer ${
                ledgerCategory === 'Large Vehicles' ? 'bg-emerald-500 text-black' : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              🚛 Large Vehicles ({largeVehiclesCount})
            </button>
          </div>

          {/* Search filter - positioned adjacent on the right */}
          <div className="relative flex-grow lg:flex-grow-0">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-zinc-500" />
            <input 
              type="text"
              placeholder="Filter Plates..."
              value={ledgerSearchQuery}
              onChange={(e) => setLedgerSearchQuery(e.target.value)}
              className="bg-zinc-950 border border-zinc-850 text-zinc-300 text-xs rounded pl-9 pr-4 py-2 w-full lg:w-44 outline-none focus:border-emerald-500 font-mono"
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
            {filteredSnapshots.map((snap) => (
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
                    onClick={() => onReview(snap.trackId)}
                    className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 hover:text-white border border-zinc-700 text-zinc-300 rounded text-[10px] font-bold tracking-wide transition-colors cursor-pointer"
                  >
                    [Review]
                  </button>
                </td>
              </tr>
            ))}
            {filteredSnapshots.length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-zinc-500 font-mono">
                  No records match search queries.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
