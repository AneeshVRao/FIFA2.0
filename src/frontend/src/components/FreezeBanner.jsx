import React from 'react';
import { WarningIcon } from './Icons';

export default function FreezeBanner() {
  return (
    <div className="bg-[#0f0e0a] border-b border-[#00ff88]/20 py-3.5 px-6 liquid-glass sticky top-0 z-50">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-3">
        <WarningIcon className="w-5 h-5 text-[#00ff88] flex-shrink-0 animate-pulse" strokeWidth={2} />
        <span className="font-display text-xs md:text-sm text-slate-300 font-medium tracking-wide uppercase">
          Live Tournament Engine: Probabilities dynamically re-simulated based on live match results and real-time fatigue (Matches Completed: 2/104)
        </span>
      </div>
    </div>
  );
}
