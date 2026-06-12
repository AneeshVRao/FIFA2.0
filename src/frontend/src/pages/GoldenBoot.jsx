import React, { useState, useMemo } from 'react';
import useSWR from 'swr';
import { TrophyIcon, SoccerBallIcon, WarningIcon } from '../components/Icons';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#050505]/90 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-2xl">
        <p className="text-white font-display font-bold text-lg mb-2">{label}</p>
        <div className="space-y-1">
          <div className="flex justify-between gap-6 text-sm font-mono">
            <span className="text-slate-500 uppercase tracking-widest text-[10px]">Mean (xG)</span>
            <span className="text-fifagold">{payload[0].value.toFixed(2)}</span>
          </div>
          <div className="flex justify-between gap-6 text-sm font-mono">
            <span className="text-slate-500 uppercase tracking-widest text-[10px]">90th %ile</span>
            <span className="text-white/70">{payload[1]?.value?.toFixed(2)}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export default function GoldenBoot() {
  const { data: bootData, error: bootError } = useSWR('/players/golden-boot?limit=40', fetcher);
  const { data: winnerData, error: winnerError } = useSWR('/predictions/winner', fetcher);

  const [filterStage, setFilterStage] = useState('all'); 
  const [searchQuery, setSearchQuery] = useState('');

  const loading = !bootData || !winnerData;
  const error = bootError || winnerError;

  const teamStageProbs = useMemo(() => {
    if (!winnerData) return {};
    const map = {};
    winnerData.teams.forEach((t) => {
      map[t.team_name.toLowerCase()] = {
        qf: t.p_qf,
        sf: t.p_sf,
      };
    });
    return map;
  }, [winnerData]);

  const filteredCandidates = useMemo(() => {
    if (!bootData) return [];
    return bootData.leaderboard.filter((c) => {
      const probs = teamStageProbs[c.team_name.toLowerCase()] || { qf: 0, sf: 0 };
      const matchesSearch = c.player_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            c.team_name.toLowerCase().includes(searchQuery.toLowerCase());
      
      let matchesStage = true;
      if (filterStage === 'qf_25') matchesStage = probs.qf * 100 >= 25;
      else if (filterStage === 'qf_50') matchesStage = probs.qf * 100 >= 50;
      else if (filterStage === 'sf_20') matchesStage = probs.sf * 100 >= 20;
      else if (filterStage === 'sf_40') matchesStage = probs.sf * 100 >= 40;

      return matchesStage && matchesSearch;
    });
  }, [bootData, teamStageProbs, filterStage, searchQuery]);

  const chartData = useMemo(() => {
    return filteredCandidates.slice(0, 6).map((c) => {
      const parts = c.player_name.trim().split(/\s+/);
      const displayName = parts.length > 1 ? `${parts[0][0]}. ${parts.slice(1).join(' ')}` : c.player_name;
      return {
        name: displayName.length > 15 ? displayName.substring(0, 13) + '..' : displayName,
        'Mean Goals': c.mean_goals,
        'P90 Peak': c.p90_goals,
      };
    });
  }, [filteredCandidates]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] gap-8">
        <div className="relative flex items-center justify-center">
          <div className="absolute w-32 h-32 rounded-full border border-fifagold/20 border-t-fifagold animate-spin"></div>
          <SoccerBallIcon className="w-8 h-8 text-fifagold/50 animate-pulse" />
        </div>
        <p className="font-mono text-[10px] text-white/40 uppercase tracking-[0.3em] animate-pulse">
          Simulating Golden Boot Monte Carlo Matrix...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doppelrand-card max-w-2xl mx-auto my-32">
        <div className="doppelrand-inner flex flex-col items-center gap-6 text-center py-24">
          <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <WarningIcon className="w-8 h-8 text-red-500 animate-pulse" />
          </div>
          <h3 className="text-3xl font-display font-semibold text-white tracking-tight">Data Sync Failure</h3>
          <p className="text-sm text-slate-400 font-mono tracking-widest uppercase">
            Golden Boot distributions unavailable
          </p>
        </div>
      </div>
    );
  }

  const leader = filteredCandidates[0];
  const runnerUps = filteredCandidates.slice(1, 3);
  const theRest = filteredCandidates.slice(3, 40);

  return (
    <div className="space-y-32 py-24">
      {/* Cinematic Header */}
      <div className="flex flex-col items-center text-center max-w-3xl mx-auto animate-fade-in-up">
        <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-fifagold/20 bg-fifagold/5 mb-8">
          <TrophyIcon className="w-4 h-4 text-fifagold" /> 
          <span className="text-[10px] text-fifagold uppercase tracking-[0.2em] font-medium">Player Output Predictions</span>
        </div>
        <h1 className="text-5xl lg:text-7xl font-display font-extrabold text-white tracking-tighter leading-[1.1]">
          The Golden <span className="text-transparent bg-clip-text bg-gradient-to-r from-fifagold to-white/50">Boot</span>
        </h1>
        <p className="text-lg text-slate-400 mt-6 font-sans leading-relaxed">
          Stochastic modeling of individual player goal output across 100,000 tournament paths, weighted by team progression probability.
        </p>
      </div>

      {/* Hero Leader: Massive Asymmetrical Bento Box */}
      {leader && (
        <div className="doppelrand-card group relative animate-fade-in-up [animation-delay:200ms]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_rgba(212,175,55,0.05)_0%,_transparent_50%)] pointer-events-none rounded-[2rem]"></div>
          <div className="doppelrand-inner p-12 lg:p-20 flex flex-col lg:flex-row items-center justify-between gap-12 bg-transparent">
            
            <div className="flex-1 space-y-8">
              <div className="w-16 h-16 rounded-full bg-fifagold/10 flex items-center justify-center border border-fifagold/20 mb-8">
                <span className="text-xl font-mono text-fifagold font-bold">#1</span>
              </div>
              <div>
                <h2 className="text-6xl lg:text-8xl font-display font-bold text-white tracking-tighter mb-4">
                  {leader.player_name}
                </h2>
                <div className="text-xl font-mono text-slate-400 uppercase tracking-widest">
                  {leader.team_name}
                </div>
              </div>
            </div>

            <div className="w-full lg:w-96 shrink-0 grid grid-cols-2 gap-8 border-t lg:border-t-0 lg:border-l border-white/10 pt-12 lg:pt-0 lg:pl-12">
              <div>
                <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-2">Golden Boot Prob</div>
                <div className="text-5xl font-mono font-light text-fifagold">
                  {(leader.p_golden_boot * 100).toFixed(1)}<span className="text-2xl text-fifagold/50">%</span>
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-2">Mean Goals (xG)</div>
                <div className="text-5xl font-mono font-light text-white">
                  {leader.mean_goals.toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-2">Median Output</div>
                <div className="text-3xl font-mono text-white/70">
                  {leader.p50_goals.toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-2">90th %ile Ceiling</div>
                <div className="text-3xl font-mono text-white/70">
                  {leader.p90_goals.toFixed(1)}
                </div>
              </div>
            </div>
            
          </div>
        </div>
      )}

      {/* Runner Ups */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-fade-in-up [animation-delay:400ms]">
        {runnerUps.map((player, idx) => (
          <div key={player.reep_player_id} className="doppelrand-card group">
            <div className="doppelrand-inner p-10 flex flex-col justify-between h-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-white/[0.02] to-transparent">
              <div className="flex justify-between items-start mb-12">
                <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                  <span className="text-sm font-mono text-white/50">#{idx + 2}</span>
                </div>
                <div className="text-right">
                  <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest">Boot Prob</div>
                  <div className="text-2xl font-mono font-light text-fifagold">{(player.p_golden_boot * 100).toFixed(1)}%</div>
                </div>
              </div>
              <div>
                <h3 className="text-4xl font-display font-bold text-white tracking-tight mb-2">
                  {player.player_name}
                </h3>
                <div className="text-sm font-mono text-slate-400 uppercase tracking-widest">
                  {player.team_name}
                </div>
                <div className="mt-8 flex gap-8 border-t border-white/5 pt-6">
                  <div>
                    <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-1">Mean Goals</div>
                    <div className="text-xl font-mono text-white">{player.mean_goals.toFixed(1)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-1">P90 Peak</div>
                    <div className="text-xl font-mono text-white/50">{player.p90_goals.toFixed(1)}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filter Tools & Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-fade-in-up [animation-delay:600ms]">
        <div className="lg:col-span-4 space-y-6">
          <div className="doppelrand-card">
            <div className="doppelrand-inner p-8 space-y-8">
              <div>
                <div className="text-[10px] uppercase font-mono text-fifagold tracking-widest mb-2">Query Filter</div>
                <input
                  type="text"
                  placeholder="Search player or team..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#050505] border border-white/10 rounded-xl px-4 py-3 text-white font-mono text-sm placeholder:text-white/20 focus:outline-none focus:border-fifagold transition-colors"
                />
              </div>

              <div>
                <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-4">Team Progression Gates</div>
                <div className="space-y-2">
                  {[
                    { val: 'all', label: 'All Players' },
                    { val: 'qf_25', label: 'Team ≥ 25% to reach QF' },
                    { val: 'qf_50', label: 'Team ≥ 50% to reach QF' },
                    { val: 'sf_20', label: 'Team ≥ 20% to reach SF' },
                  ].map((btn) => (
                    <button
                      key={btn.val}
                      onClick={() => setFilterStage(btn.val)}
                      className={`w-full text-left px-4 py-3 rounded-xl border font-mono text-xs uppercase tracking-widest transition-all duration-300 ${
                        filterStage === btn.val
                          ? 'border-fifagold bg-fifagold/10 text-fifagold'
                          : 'border-white/5 bg-black/40 text-slate-500 hover:border-white/20 hover:text-white'
                      }`}
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-8 doppelrand-card">
          <div className="doppelrand-inner h-full flex flex-col p-10 relative">
            <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-8">
              Top 6 Output Distributions
            </div>
            <div className="flex-1 min-h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                  <XAxis 
                    dataKey="name" 
                    stroke="rgba(255,255,255,0.2)" 
                    tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11, fontFamily: 'Space Grotesk' }}
                    axisLine={false} tickLine={false} dy={10}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.2)" 
                    tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                    axisLine={false} tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                  <Bar dataKey="P90 Peak" fill="rgba(255,255,255,0.05)" radius={[4, 4, 0, 0]} barSize={40} />
                  <Bar dataKey="Mean Goals" fill="hsl(45, 100%, 50%)" radius={[4, 4, 0, 0]} barSize={40} style={{ transform: 'translateX(-40px)' }} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* The Rest of the Pack List */}
      <div className="doppelrand-card animate-fade-in-up [animation-delay:800ms]">
        <div className="doppelrand-inner p-10">
          <div className="text-[10px] uppercase font-mono text-fifagold tracking-widest mb-8">
            Extended Leaderboard (Top 40)
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-4">
            {theRest.map((player, idx) => (
              <div key={player.reep_player_id} className="flex justify-between items-center py-4 border-b border-white/5 hover:border-white/20 transition-colors group">
                <div className="flex items-center gap-4">
                  <span className="text-xs font-mono text-white/30 w-6">{(idx + 4).toString().padStart(2, '0')}</span>
                  <div>
                    <div className="text-sm font-display font-bold text-white group-hover:text-fifagold transition-colors">{player.player_name}</div>
                    <div className="text-[9px] font-mono uppercase text-slate-500 tracking-widest mt-0.5">{player.team_name}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-mono text-white">{player.mean_goals.toFixed(1)} <span className="text-[9px] text-slate-500">xG</span></div>
                  <div className="text-[9px] font-mono text-fifagold mt-0.5">{(player.p_golden_boot * 100).toFixed(1)}% BOOT</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
}
