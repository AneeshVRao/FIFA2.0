import React, { useState } from 'react';
import FreezeBanner from './components/FreezeBanner';
import SplashScreen from './components/SplashScreen';
import Dashboard from './pages/Dashboard';
import MatchPredictor from './pages/MatchPredictor';
import XGSandbox from './pages/XGSandbox';
import PenaltySandbox from './pages/PenaltySandbox';
import BracketExplorer from './pages/BracketExplorer';
import GoldenBoot from './pages/GoldenBoot';
import logoUrl from './assets/logo.svg';
import { TrophyIcon, SoccerBallIcon, StadiumIcon, TravelIcon, AltitudeIcon } from './components/Icons';

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedMatchId, setSelectedMatchId] = useState('match_1');

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <Dashboard 
            onSelectMatch={(matchId) => {
              setSelectedMatchId(matchId);
              setActiveTab('predictor');
            }} 
          />
        );
      case 'predictor':
        return (
          <MatchPredictor 
            selectedMatchId={selectedMatchId} 
            setSelectedMatchId={setSelectedMatchId} 
          />
        );
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
    <>
      {showSplash && <SplashScreen onComplete={() => setShowSplash(false)} />}
      <div className="bg-darkbg text-slate-200 min-h-[100dvh] font-sans flex flex-col relative overflow-hidden selection:bg-fifagold/30 selection:text-white">
      {/* Ambient Radial Glow Orbs */}
      <div className="glow-orb-gold top-[-100px] left-[-100px]"></div>
      <div className="glow-orb-green bottom-[-100px] right-[-100px]"></div>

      {/* Freeze Disclaimer Banner */}
      <FreezeBanner />

      {/* Fluid Glass Navigation Pill */}
      <header className="sticky top-20 z-40 mx-auto mt-6 px-4 md:px-6 w-full max-w-6xl pointer-events-none">
        <nav className="pointer-events-auto bg-[#090b13]/85 backdrop-blur-xl border border-white/10 rounded-full py-3 px-4 md:px-7 flex items-center justify-between shadow-[0_20px_40px_-10px_rgba(0,0,0,0.7)]">
          {/* Logo Brand Brand Accent */}
          <div className="flex items-center gap-3 pl-1 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <img 
              src={logoUrl} 
              className="w-6 h-8 object-contain select-none pointer-events-none filter drop-shadow-[0_0_6px_rgba(225,181,11,0.3)]" 
              alt="FIFA 26 Logo" 
            />
            <span className="font-display font-black text-sm md:text-base text-white tracking-widest uppercase">
              Goal<span className="text-fifagold">IQ</span>
            </span>
          </div>

          {/* Navigation Links list */}
          <div className="flex items-center gap-1.5 md:gap-3 overflow-x-auto scrollbar-none py-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = activeTab === link.id;
              return (
                <button
                  key={link.id}
                  onClick={() => setActiveTab(link.id)}
                  className={`px-4 py-2.5 rounded-full text-xs md:text-xs font-display font-bold tracking-wider uppercase transition-all duration-350 ease-[cubic-bezier(0.32,0.72,0,1)] flex items-center gap-2 cursor-pointer whitespace-nowrap ${
                    isActive 
                      ? 'bg-gradient-to-r from-fifagold via-amber-400 to-fifagold text-[#050505] shadow-[0_8px_20px_-4px_rgba(212,175,55,0.45)] border border-fifagold/30 scale-[1.03]' 
                      : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="hidden md:inline">{link.label}</span>
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
          <div className="text-[#00ff88]/70">
            LIVE TOURNAMENT RE-SIMULATION ENGINE · INGESTING REAL-TIME FBRef EVENTS AND APIFY FATIGUE SCORES
          </div>
        </div>
      </footer>
    </div>
    </>
  );
}
