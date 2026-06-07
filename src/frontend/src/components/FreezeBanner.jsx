import React from 'react';
import { WarningIcon } from './Icons';

export default function FreezeBanner() {
  return (
    <div className="bg-[#0f0e0a] border-b border-[#ffd700]/10 py-3.5 px-6 liquid-glass sticky top-0 z-50">
      <div className="max-w-7xl mx-auto flex items-center justify-center gap-3">
        <WarningIcon className="w-5 h-5 text-fifagold flex-shrink-0 animate-pulse" strokeWidth={2} />
        <span className="font-display text-xs md:text-sm text-slate-300 font-medium tracking-wide uppercase">
          Pre-Tournament Predictive Forecast: All Models Frozen as of June 6, 2026. fixtures and valuations are locked.
        </span>
      </div>
    </div>
  );
}
