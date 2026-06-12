import React, { useState, useEffect, Suspense } from 'react';
import useSWR from 'swr';
import { TravelIcon, AltitudeIcon, TrophyIcon, WarningIcon, SoccerBallIcon } from '../components/Icons';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import StadiumMesh from '../components/StadiumMesh';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

const postFetcher = (url, body) =>
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((res) => {
    if (!res.ok) throw new Error('Failed to post');
    return res.json();
  });

export default function MatchPredictor({ selectedMatchId, setSelectedMatchId }) {
  const { data: teamsData } = useSWR('/predictions/teams', fetcher);
  const { data: venuesData } = useSWR('/predictions/venues', fetcher);
  const { data: matchesData } = useSWR('/predictions/matches', fetcher);

  const [customMode, setCustomMode] = useState(false);

  useEffect(() => {
    if (selectedMatchId) {
      setCustomMode(false);
    }
  }, [selectedMatchId]);

  const [teamAId, setTeamAId] = useState('T-83'); 
  const [teamBId, setTeamBId] = useState('T-30'); 
  const [venueId, setVenueId] = useState('v_mexicocity'); 
  const [matchContext, setMatchContext] = useState('group');

  const [customData, setCustomData] = useState(null);
  const [customLoading, setCustomLoading] = useState(false);
  const [customError, setCustomError] = useState(false);

  const { data: matchData, error: matchError } = useSWR(
    !customMode && selectedMatchId ? `/predictions/match/${selectedMatchId}` : null,
    fetcher
  );

  useEffect(() => {
    if (customMode) {
      setCustomLoading(true);
      setCustomError(false);
      postFetcher('/predictions/match/custom', {
        team_a_id: teamAId,
        team_b_id: teamBId,
        venue_id: venueId,
        match_context: matchContext,
      })
        .then((res) => {
          setCustomData(res);
          setCustomLoading(false);
        })
        .catch(() => {
          setCustomError(true);
          setCustomLoading(false);
        });
    }
  }, [customMode, teamAId, teamBId, venueId, matchContext]);

  const loading = !teamsData || !venuesData || !matchesData || (!customMode && !matchData);
  const error = matchError || customError;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] gap-8">
        <div className="relative flex items-center justify-center">
          <div className="absolute w-32 h-32 rounded-full border border-fifagold/20 border-t-fifagold animate-spin"></div>
          <div className="text-fifagold text-2xl font-mono">XG</div>
        </div>
        <p className="font-mono text-[10px] text-white/40 uppercase tracking-[0.3em] animate-pulse">
          Initializing Dixon-Coles Matrix...
        </p>
      </div>
    );
  }

  const activeData = customMode ? customData : matchData;

  const pieData = activeData
    ? [
        { name: activeData.home_team.name, value: activeData.probabilities.home_win, color: 'hsl(140, 100%, 50%)' },
        { name: 'Draw', value: activeData.probabilities.draw, color: 'rgba(255, 255, 255, 0.2)' },
        { name: activeData.away_team.name, value: activeData.probabilities.away_win, color: 'hsl(45, 100%, 50%)' },
      ]
    : [];

  const getImpliedOdds = (p) => (p > 0 ? (1 / p).toFixed(2) : '0.00');
  const getPinnacleOdds = (p, bias) => {
    const odds = 1 / (p * 1.03); 
    return (odds * bias).toFixed(2);
  };

  return (
    <div className="space-y-32 py-24 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-12 border-b border-white/10 pb-16">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-fifagold/20 bg-fifagold/5 mb-8">
            <TrophyIcon className="w-4 h-4 text-fifagold" /> 
            <span className="text-[10px] text-fifagold uppercase tracking-[0.2em] font-medium">Bivariate Poisson Engine</span>
          </div>
          <h1 className="text-5xl lg:text-7xl font-display font-extrabold text-white tracking-tighter leading-[1.1]">
            Match <span className="text-transparent bg-clip-text bg-gradient-to-r from-fifagold to-white/50">Predictor</span>
          </h1>
          <p className="text-lg text-slate-400 mt-6 font-sans leading-relaxed">
            Run official fixtures or custom scenarios through our hyper-calibrated Dixon-Coles expected goals (xG) engine.
          </p>
        </div>

        {/* Toggle Mode */}
        <div className="flex bg-white/5 p-2 rounded-full border border-white/10 select-none shrink-0">
          <button
            onClick={() => setCustomMode(false)}
            className={`px-8 py-3 rounded-full text-xs font-display font-bold tracking-widest uppercase transition-all duration-300 active:scale-[0.98] ${
              !customMode ? 'bg-fifagold text-[#050505] shadow-[0_0_20px_rgba(212,175,55,0.4)]' : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            Official Fixtures
          </button>
          <button
            onClick={() => setCustomMode(true)}
            className={`px-8 py-3 rounded-full text-xs font-display font-bold tracking-widest uppercase transition-all duration-300 active:scale-[0.98] ${
              customMode ? 'bg-fifagold text-[#050505] shadow-[0_0_20px_rgba(212,175,55,0.4)]' : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            Custom Sandbox
          </button>
        </div>
      </div>

      {/* Main Selector Row */}
      {!customMode ? (
        <div className="doppelrand-card max-w-2xl mx-auto">
          <div className="doppelrand-inner space-y-6 p-8">
            <label className="text-[10px] uppercase font-mono text-fifagold tracking-widest block">Select Scheduled Fixture</label>
            <select
              value={selectedMatchId}
              onChange={(e) => setSelectedMatchId(e.target.value)}
              className="bg-[#050505] border border-white/10 rounded-xl px-6 py-4 text-base text-white focus:outline-none focus:border-fifagold transition-colors w-full font-sans cursor-pointer hover:border-white/20"
            >
              {matchesData.matches.map((m) => (
                <option key={m.match_id} value={m.match_id} className="bg-[#0b0d17] text-white">
                  Match {m.match_id.replace('match_', '')}: {m.team_a_name} vs {m.team_b_name} ({m.stage.toUpperCase()})
                </option>
              ))}
            </select>
          </div>
        </div>
      ) : (
        <div className="doppelrand-card">
          <div className="doppelrand-inner p-10 grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="space-y-4">
              <label className="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Team A (Home)</label>
              <select
                value={teamAId}
                onChange={(e) => setTeamAId(e.target.value)}
                className="bg-[#050505] border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-fifagold transition-colors w-full cursor-pointer hover:border-white/20"
              >
                {teamsData.teams.map((t) => (
                  <option key={t.reep_team_id} value={t.reep_team_id} className="bg-[#0b0d17]">
                    {t.team_name_canonical} (Elo {t.pretournament_elo.toFixed(0)})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-4">
              <label className="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Team B (Away)</label>
              <select
                value={teamBId}
                onChange={(e) => setTeamBId(e.target.value)}
                className="bg-[#050505] border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-fifagold transition-colors w-full cursor-pointer hover:border-white/20"
              >
                {teamsData.teams.map((t) => (
                  <option key={t.reep_team_id} value={t.reep_team_id} className="bg-[#0b0d17]">
                    {t.team_name_canonical} (Elo {t.pretournament_elo.toFixed(0)})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-4">
              <label className="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Host Venue</label>
              <select
                value={venueId}
                onChange={(e) => setVenueId(e.target.value)}
                className="bg-[#050505] border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-fifagold transition-colors w-full cursor-pointer hover:border-white/20"
              >
                {venuesData.venues.map((v) => (
                  <option key={v.venue_id} value={v.venue_id} className="bg-[#0b0d17]">
                    {v.stadium_name} ({v.city})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-4">
              <label className="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Match Context</label>
              <select
                value={matchContext}
                onChange={(e) => setMatchContext(e.target.value)}
                className="bg-[#050505] border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-fifagold transition-colors w-full cursor-pointer hover:border-white/20"
              >
                <option value="group" className="bg-[#0b0d17]">Group Stage</option>
                <option value="r32" className="bg-[#0b0d17]">Round of 32</option>
                <option value="r16" className="bg-[#0b0d17]">Round of 16</option>
                <option value="quarterfinal" className="bg-[#0b0d17]">Quarterfinal</option>
                <option value="semifinal" className="bg-[#0b0d17]">Semifinal</option>
                <option value="final" className="bg-[#0b0d17]">Final</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Prediction Output Section */}
      {customMode && customLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-8">
          <div className="w-16 h-16 rounded-full border-t-4 border-fifagold animate-spin"></div>
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest animate-pulse">
            Calculating...
          </p>
        </div>
      ) : activeData ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Column 1: Matchup Details & Donut Chart */}
          <div className="doppelrand-card lg:col-span-8">
            <div className="doppelrand-inner h-full flex flex-col p-12 relative overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-white/[0.03] to-transparent">
              <div className="flex justify-between items-center mb-16">
                <span className="text-[10px] font-mono uppercase text-fifagold tracking-[0.2em]">
                  Dixon-Coles Matrix
                </span>
                <span className="text-[10px] uppercase font-mono text-white px-3 py-1.5 rounded-full border border-white/10 bg-white/5 font-bold tracking-widest">
                  {activeData.stage} Phase
                </span>
              </div>

              {/* Large Score Projection Grid */}
              <div className="flex justify-between items-center gap-8 mb-16 relative">
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] font-mono text-white/20 uppercase tracking-[0.5em] select-none">
                  VERSUS
                </div>

                <div className="text-center space-y-6 flex-1">
                  <h3 className="text-4xl lg:text-6xl font-display font-extrabold text-white tracking-tighter">
                    {activeData.home_team.name}
                  </h3>
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 font-mono tracking-widest mb-2">Projected xG</div>
                    <div className="text-6xl lg:text-8xl font-mono font-light text-fifagreen tracking-tighter">
                      {activeData.expected_goals.home_xg.toFixed(2)}
                    </div>
                  </div>
                </div>

                <div className="text-center space-y-6 flex-1">
                  <h3 className="text-4xl lg:text-6xl font-display font-extrabold text-white tracking-tighter">
                    {activeData.away_team.name}
                  </h3>
                  <div>
                    <div className="text-[10px] uppercase text-slate-500 font-mono tracking-widest mb-2">Projected xG</div>
                    <div className="text-6xl lg:text-8xl font-mono font-light text-fifagold tracking-tighter">
                      {activeData.expected_goals.away_xg.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>

              {/* Probabilities Distribution donut and legend */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center border-t border-white/5 pt-12 mt-auto">
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={80}
                        outerRadius={110}
                        paddingAngle={4}
                        dataKey="value"
                        stroke="none"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: '#050505', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', padding: '16px' }}
                        itemStyle={{ color: '#ffffff', fontFamily: 'Geist Mono', fontSize: '18px' }}
                        formatter={(value) => [`${(value * 100).toFixed(1)}%`]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-4">
                  {pieData.map((d) => (
                    <div key={d.name} className="flex justify-between items-center p-4 bg-white/[0.02] border border-white/5 rounded-2xl">
                      <div className="flex items-center gap-4">
                        <span className="w-3 h-3 rounded-full shadow-[0_0_10px_currentColor]" style={{ backgroundColor: d.color, color: d.color }}></span>
                        <span className="text-lg font-display font-bold text-white">{d.name}</span>
                      </div>
                      <span className="text-2xl font-mono text-white/80">
                        {(d.value * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Column 2: Influences, Odds, Scorelines */}
          <div className="space-y-8 lg:col-span-4">
            
            {/* 3D Stadium Telemetry Card */}
            {(() => {
              const activeVenueId = activeData?.venue?.id;
              const activeVenueObj = venuesData?.venues?.find(v => v.venue_id === activeVenueId);
              const activeVenueCapacity = activeVenueObj ? activeVenueObj.capacity : 60000;
              const activeVenueHost = activeVenueObj ? activeVenueObj.host_nation : 'USA';
              
              return (
                <div className="doppelrand-card h-[400px]">
                  <div className="doppelrand-inner h-full flex flex-col p-6">
                    <div className="flex justify-between items-center border-b border-white/5 pb-4 mb-4">
                      <h3 className="text-sm font-display font-semibold text-white">Stadium Telemetry</h3>
                    </div>
                    
                    <div className="flex-1 bg-[#050505] rounded-2xl relative overflow-hidden border border-white/10 flex items-center justify-center group/canvas">
                      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#050505]/80 z-10 pointer-events-none"></div>
                      <Canvas 
                        camera={{ position: [0, 8, 14], fov: 45 }}
                        dpr={typeof window !== 'undefined' && /iPhone|iPad|Android/i.test(navigator.userAgent) ? 1 : 2}
                      >
                        <color attach="background" args={["#050505"]} />
                        <ambientLight intensity={0.5} />
                        <directionalLight position={[10, 10, 5]} intensity={1} />
                        <Suspense fallback={null}>
                          <StadiumMesh 
                            capacity={activeVenueCapacity} 
                            altitude={activeData.venue.altitude_m} 
                            hostNation={activeVenueHost} 
                          />
                          <OrbitControls 
                            enableZoom={false} 
                            enablePan={false}
                            maxPolarAngle={Math.PI / 2 - 0.2}
                            minPolarAngle={0.4}
                            autoRotate
                            autoRotateSpeed={1.0}
                          />
                        </Suspense>
                      </Canvas>
                      
                      <div className="absolute bottom-4 left-4 z-20 space-y-1">
                        <div className="text-[10px] font-mono text-white/50 uppercase tracking-[0.2em]">{activeData.venue.name}</div>
                        <div className="text-2xl font-display font-bold text-white">{activeVenueCapacity.toLocaleString()} <span className="text-sm text-slate-500 font-sans font-normal">seats</span></div>
                      </div>
                      
                      <div className="absolute top-4 right-4 z-20">
                        <div className="px-3 py-1 rounded-full bg-white/10 border border-white/20 text-[10px] font-mono text-white uppercase tracking-widest backdrop-blur-md">
                          {activeData.venue.altitude_m.toFixed(0)}m ASL
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Top Scorelines (Doppelrand Card) */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner p-8 space-y-6">
                <div className="flex items-center gap-4">
                  <div className="w-8 h-8 rounded-full bg-fifagold/10 flex items-center justify-center border border-fifagold/20">
                    <SoccerBallIcon className="w-4 h-4 text-fifagold" />
                  </div>
                  <h3 className="text-xl font-display font-bold text-white tracking-tight">Predicted Scorelines</h3>
                </div>
                
                <div className="space-y-3">
                  {activeData.top_scorelines.map((s, idx) => (
                    <div key={s.scoreline} className="flex justify-between items-center p-4 bg-[#050505] border border-white/5 rounded-2xl hover:border-white/20 transition-colors">
                      <div className="flex items-center gap-4">
                        <span className="text-[10px] font-mono text-slate-600">0{idx + 1}</span>
                        <span className="text-2xl font-mono font-bold text-white">{s.scoreline}</span>
                      </div>
                      <span className="text-lg font-mono text-fifagold">
                        {(s.probability * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      ) : null}
    </div>
  );
}
