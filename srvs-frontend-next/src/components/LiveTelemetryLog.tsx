import React, { useEffect, useRef } from 'react';
import { LogEntry } from './types';

interface LiveTelemetryLogProps {
  logs: LogEntry[];
}

export default function LiveTelemetryLog({ logs }: LiveTelemetryLogProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Automatically scroll logs to bottom on update
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-zinc-900/40 p-4 rounded-xl border border-zinc-800 flex-grow flex flex-col justify-between max-h-[515px] h-full">
      <div>
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-3">
          <span className="text-xs font-black tracking-widest text-zinc-300 uppercase">ZONE 2: TELEMETRY ACTIVITY LOG</span>
          <span className="text-[9px] bg-red-950 text-red-400 border border-red-900/60 rounded px-2 py-0.5">Stream Output</span>
        </div>

        {/* Scrollable event listings */}
        <div 
          ref={containerRef}
          className="flex flex-col gap-2.5 h-[380px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-zinc-800"
        >
          {logs.map((log, index) => (
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
                  <span className={`w-1.5 h-1.5 rounded-full ${log.type === 'warning' ? 'bg-red-400 animate-ping' : 'bg-zinc-650'}`} />
                  TELEMETRY LOG TICK
                </span>
                <span>{log.time}</span>
              </div>
              <p className="font-mono">{log.message}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="pt-2 text-right border-t border-zinc-900">
        <span className="text-[10px] text-zinc-500">Live Cadence Polling...</span>
      </div>
    </div>
  );
}
