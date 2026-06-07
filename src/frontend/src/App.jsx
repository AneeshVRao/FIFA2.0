import React, { useState } from 'react';
import FreezeBanner from './components/FreezeBanner';
import Dashboard from './pages/Dashboard';
import MatchPredictor from './pages/MatchPredictor';
import XGSandbox from './pages/XGSandbox';
import PenaltySandbox from './pages/PenaltySandbox';
import BracketExplorer from './pages/BracketExplorer';
import GoldenBoot from './pages/GoldenBoot';
import { TrophyIcon, SoccerBallIcon, StadiumIcon, TravelIcon, AltitudeIcon } from './components/Icons';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'predictor':
        return <MatchPredictor />;
      case 'xg':
        return <XGSandbox />;
      case 'penalty':
        return <PenaltySandbox />;
      case 'bracket':
        return <BracketExplorer />;
      case 'goldenboot':
        return <GoldenBoot />;
      default:
        return <Dashboard />;
    }
  };

  const navLinks = [
    { id: 'dashboard', label: 'Globe Map', icon: StadiumIcon },
    { id: 'predictor', label: 'Predictor', icon: TravelIcon },
    { id: 'xg', label: 'xG Sandbox', icon: SoccerBallIcon },
    { id: 'penalty', label: 'Penalty Sandbox', icon: AltitudeIcon },
    { id: 'bracket', label: 'Bracket', icon: TrophyIcon },
    { id: 'goldenboot', label: 'Golden Boot', icon: TrophyIcon },
  ];

  return (
    <div className="bg-darkbg text-slate-200 min-h-[100dvh] font-sans flex flex-col relative overflow-hidden selection:bg-fifagold/30 selection:text-white">
      {/* Ambient Radial Glow Orbs */}
      <div className="glow-orb-gold top-[-100px] left-[-100px]"></div>
      <div className="glow-orb-green bottom-[-100px] right-[-100px]"></div>

      {/* Freeze Disclaimer Banner */}
      <FreezeBanner />

      {/* Fluid Glass Navigation Pill */}
      <header className="sticky top-20 z-40 mx-auto mt-6 px-4 md:px-0 w-full max-w-4xl pointer-events-none">
        <nav className="pointer-events-auto bg-[#090b13]/85 backdrop-blur-xl border border-white/10 rounded-full py-2 px-3 md:px-4 flex items-center justify-between shadow-[0_15px_30px_-5px_rgba(0,0,0,0.6)]">
          {/* Logo Brand Brand Accent */}
          <div className="flex items-center gap-2 pl-2 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <TrophyIcon className="w-5 h-5 text-fifagold animate-pulse" />
            <span className="font-display font-extrabold text-sm text-white tracking-wider uppercase">
              Goal<span className="text-fifagold">IQ</span>
            </span>
          </div>

          {/* Navigation Links list */}
          <div className="flex gap-1 md:gap-1.5 overflow-x-auto max-w-[70%] scrollbar-none py-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = activeTab === link.id;
              return (
                <button
                  key={link.id}
                  onClick={() => setActiveTab(link.id)}
                  className={`px-3.5 py-2 rounded-full text-[10px] md:text-xs font-display font-semibold tracking-wide uppercase transition-all duration-300 ease-[cubic-bezier(0.32,0.72,0,1)] flex items-center gap-1.5 cursor-pointer whitespace-nowrap ${
                    isActive 
                      ? 'bg-fifagold text-[#050505] shadow-[0_4px_12px_rgba(212,175,55,0.3)] scale-[1.03] font-bold' 
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="hidden sm:inline">{link.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      {/* Main Pages Container */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 md:px-8 py-10 relative z-10">
        {renderActivePage()}
      </main>

      {/* Broadcast Experience Footer */}
      <footer className="border-t border-white/5 py-8 text-center text-[10px] font-mono text-slate-500 relative z-10">
        <div className="max-w-7xl mx-auto px-4 space-y-2">
          <div>GOALIQ · OFFICIAL FIFA WORLD CUP 2026 ANALYTICAL ENGINE</div>
          <div className="text-slate-600">
            COMPUTED VIA MONTE CARLO TOURNAMENT FORECAST GRIDS · VERIFIED UNDER FROZEN METADATA INDEX
          </div>
        </div>
      </footer>
    </div>
  );
}
