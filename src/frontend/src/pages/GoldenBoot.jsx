import React, { useState, useMemo } from 'react';
import useSWR from 'swr';
import { TrophyIcon, SoccerBallIcon, WarningIcon } from '../components/Icons';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

export default function GoldenBoot() {
  const { data: bootData, error: bootError } = useSWR('/players/golden-boot?limit=40', fetcher);
  const { data: winnerData, error: winnerError } = useSWR('/predictions/winner', fetcher);

  const [filterStage, setFilterStage] = useState('all'); // all, qf_25, qf_50, sf_20, sf_40
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPlayer, setSelectedPlayer] = useState(null); // Active modal player

  const loading = !bootData || !winnerData;
  const error = bootError || winnerError;

  // Map team names to QF and SF probabilities for dynamic filtering (PRD Section 13.6)
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

  // Filter candidates based on name and team stage probability gates
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

  // Chart data representing top 8 filtered candidates' goal distributions (PRD Section 13.6)
  const chartData = useMemo(() => {
    return filteredCandidates.slice(0, 8).map((c) => ({
      name: c.player_name.split(' ').pop(), // last name
      'P50 (Median)': c.p50_goals,
      'P90 (High Target)': c.p90_goals,
      Mean: c.mean_goals,
    }));
  }, [filteredCandidates]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 rounded-full border-t-2 border-fifagold animate-spin"></div>
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest animate-pulse">
          Compiling player metrics and roster matrices...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doppelrand-card max-w-xl mx-auto my-12">
        <div className="doppelrand-inner flex flex-col items-center gap-4 text-center">
          <WarningIcon className="w-8 h-8 text-red-500" />
          <h3 className="text-lg font-display font-semibold text-white">Roster Sync Failure</h3>
          <p className="text-xs text-slate-400">Failed to retrieve Golden Boot distribution curves.</p>
        </div>
      </div>
    );
  }

  const podium = filteredCandidates.slice(0, 3);

  return (
    <div className="space-y-12 animate-fade-in py-6 relative">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Golden Boot Projections
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl font-sans">
            Simulated probabilities for the top tournament goalscorer candidates. Uses Monte Carlo matches progression to model expected minutes.
          </p>
        </div>

        {/* Filters Panel (PRD Section 13.6: team stage filters) */}
        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          {/* Search */}
          <input
            type="text"
            placeholder="Search candidates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-full px-4 py-2 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full sm:w-48 font-sans"
          />

          {/* Team Stage Filter */}
          <select
            value={filterStage}
            onChange={(e) => setFilterStage(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-full px-4 py-2 text-xs text-white focus:outline-none focus:border-fifagold/40 cursor-pointer font-sans"
          >
            <option value="all" className="bg-[#0b0d17]">All Teams</option>
            <option value="qf_25" className="bg-[#0b0d17]">P(QF) &ge; 25%</option>
            <option value="qf_50" className="bg-[#0b0d17]">P(QF) &ge; 50%</option>
            <option value="sf_20" className="bg-[#0b0d17]">P(SF) &ge; 20%</option>
            <option value="sf_40" className="bg-[#0b0d17]">P(SF) &ge; 40%</option>
          </select>
        </div>
      </div>

      {/* Goal Distribution Chart (PRD Section 13.6) */}
      {chartData.length > 0 && (
        <div className="doppelrand-card">
          <div className="doppelrand-inner space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-base font-display font-semibold text-white">Goal Distribution Ranges</h3>
              <span className="text-[10px] font-mono text-slate-500 uppercase">Top 8 Filtered Contenders</span>
            </div>
            
            <div className="h-[260px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="name" stroke="rgba(255,255,255,0.3)" fontSize={10} />
                  <YAxis stroke="rgba(255,255,255,0.3)" fontSize={10} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#090b13', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    labelStyle={{ color: '#ffffff', fontWeight: 'bold' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 10, paddingTop: 10 }} />
                  <Bar dataKey="P50 (Median)" fill="hsl(140, 100%, 50%)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="P90 (High Target)" fill="hsl(45, 100%, 50%)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Mean" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Top 3 Podium Cards */}
      {podium.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-end">
          {podium[1] && (
            <PodiumCard candidate={podium[1]} rank={2} qfProb={teamStageProbs[podium[1].team_name.toLowerCase()]?.qf || 0} onSelect={setSelectedPlayer} />
          )}
          {podium[0] && (
            <PodiumCard candidate={podium[0]} rank={1} qfProb={teamStageProbs[podium[0].team_name.toLowerCase()]?.qf || 0} onSelect={setSelectedPlayer} featured />
          )}
          {podium[2] && (
            <PodiumCard candidate={podium[2]} rank={3} qfProb={teamStageProbs[podium[2].team_name.toLowerCase()]?.qf || 0} onSelect={setSelectedPlayer} />
          )}
        </div>
      )}

      {/* Leaderboard Table List */}
      <div className="doppelrand-card">
        <div className="doppelrand-inner space-y-4">
          <h3 className="text-xl font-display font-semibold text-white">Full Leaderboard</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse cursor-pointer">
              <thead>
                <tr className="border-b border-white/5 text-[10px] uppercase font-mono text-slate-400 tracking-wider">
                  <th className="py-3 px-4 w-12 text-center">Rank</th>
                  <th className="py-3 px-4">Player</th>
                  <th className="py-3 px-4">Squad</th>
                  <th className="py-3 px-4 text-center">Exp Minutes</th>
                  <th className="py-3 px-4 text-center">QF Reach</th>
                  <th className="py-3 px-4">Goal Density (P50 - Mean - P90)</th>
                  <th className="py-3 px-4 text-right">Golden Boot Prob</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-sm">
                {filteredCandidates.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-xs text-slate-500">
                      No candidates match the selected filters.
                    </td>
                  </tr>
                ) : (
                  filteredCandidates.map((c, idx) => {
                    const qf = teamStageProbs[c.team_name.toLowerCase()]?.qf || 0.0;
                    return (
                      <tr 
                        key={c.reep_player_id} 
                        onClick={() => setSelectedPlayer(c)}
                        className="hover:bg-white/[0.02] transition-all duration-200"
                      >
                        <td className="py-4 px-4 text-center font-mono font-bold text-slate-400">
                          {idx + 1}
                        </td>
                        <td className="py-4 px-4 font-display font-semibold text-white">
                          {c.player_name}
                        </td>
                        <td className="py-4 px-4 text-slate-400">
                          {c.team_name}
                        </td>
                        <td className="py-4 px-4 text-center font-mono font-semibold text-slate-300">
                          {c.expected_minutes.toFixed(0)} min
                        </td>
                        <td className="py-4 px-4 text-center font-mono text-slate-300">
                          {(qf * 100).toFixed(1)}%
                        </td>
                        <td className="py-4 px-4 w-60">
                          <div className="space-y-1">
                            <div className="flex justify-between items-center text-[9px] font-mono text-slate-500">
                              <span>P50: {c.p50_goals.toFixed(0)}</span>
                              <span>Mean: {c.mean_goals.toFixed(1)}</span>
                              <span>P90: {c.p90_goals.toFixed(0)}</span>
                            </div>
                            <div className="h-1.5 w-full bg-white/5 rounded-full relative overflow-hidden">
                              <div 
                                style={{
                                  left: `${(c.p50_goals / 10) * 100}%`,
                                  width: `${((c.p90_goals - c.p50_goals) / 10) * 100}%`,
                                }}
                                className="absolute h-full bg-fifagold/20 rounded-full"
                              ></div>
                              <div 
                                style={{
                                  left: `${(c.mean_goals / 10) * 100}%`,
                                }}
                                className="absolute w-2.5 h-2.5 -mt-0.5 rounded-full bg-fifagold border border-[#050505]"
                              ></div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-4 text-right font-mono font-bold text-fifagold">
                          {(c.p_golden_boot * 100).toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* PRD Section 13.6: Player Card Modal Overlay */}
      {selectedPlayer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-fade-in p-4">
          <div className="doppelrand-card max-w-md w-full relative pointer-events-auto">
            <div className="doppelrand-inner p-6 space-y-6">
              {/* Modal Header */}
              <div className="flex justify-between items-start border-b border-white/5 pb-4">
                <div>
                  <span className="text-[10px] font-mono text-fifagold uppercase tracking-widest">Player Profile Modal</span>
                  <h2 className="text-2xl font-display font-extrabold text-white mt-1">
                    {selectedPlayer.player_name}
                  </h2>
                  <p className="text-xs text-slate-400">{selectedPlayer.team_name} · {selectedPlayer.position}</p>
                </div>
                <button 
                  onClick={() => setSelectedPlayer(null)}
                  className="text-slate-400 hover:text-white font-mono text-xs uppercase cursor-pointer"
                >
                  [CLOSE]
                </button>
              </div>

              {/* Modal Stats Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                  <div className="text-[10px] uppercase font-mono text-slate-500">Caps</div>
                  <div className="text-lg font-mono font-bold text-white mt-1">
                    {selectedPlayer.caps} caps
                  </div>
                </div>
                <div className="bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                  <div className="text-[10px] uppercase font-mono text-slate-500">Bayesian Conversion</div>
                  <div className="text-lg font-mono font-bold text-fifagold mt-1">
                    {(selectedPlayer.bayesian_penalty_conversion * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                  <div className="text-[10px] uppercase font-mono text-slate-500">Expected Minutes</div>
                  <div className="text-lg font-mono font-bold text-white mt-1">
                    {selectedPlayer.expected_minutes.toFixed(0)} min
                  </div>
                </div>
                <div className="bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                  <div className="text-[10px] uppercase font-mono text-slate-500">Golden Boot Prob</div>
                  <div className="text-lg font-mono font-bold text-fifagold mt-1">
                    {(selectedPlayer.p_golden_boot * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Simulation Path Summary */}
              <div className="p-4 bg-white/5 border border-white/10 rounded-xl space-y-2">
                <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Simulation Path Summary</span>
                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  The model projects a mean output of <strong className="text-white">{selectedPlayer.mean_goals.toFixed(2)} goals</strong> for this player. Expected minutes are adjusted dynamically based on team progression likelihood to the Quarterfinal ({(teamStageProbs[selectedPlayer.team_name.toLowerCase()]?.qf * 100).toFixed(1)}% reach rate).
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component: Podium Cards for top 3 candidates
function PodiumCard({ candidate, rank, qfProb, featured, onSelect }) {
  return (
    <div 
      onClick={() => onSelect(candidate)}
      className={`doppelrand-card cursor-pointer transition-all duration-300 hover:border-fifagold/60 ${
        featured ? 'md:scale-105 border-fifagold/30 shadow-[0_25px_50px_rgba(212,175,55,0.1)]' : ''
      }`}
    >
      <div className="doppelrand-inner flex flex-col justify-between space-y-4">
        <div className="flex justify-between items-center">
          <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
            rank === 1 ? 'bg-fifagold/20 border border-fifagold/30 text-fifagold' : 'bg-white/5 border border-white/10 text-slate-400'
          }`}>
            Rank {rank}
          </span>
          <SoccerBallIcon className={`w-5 h-5 ${featured ? 'text-fifagold animate-spin-slow' : 'text-slate-500'}`} />
        </div>

        <div className="space-y-1">
          <h3 className="text-xl font-display font-extrabold text-white leading-tight truncate">
            {candidate.player_name}
          </h3>
          <p className="text-xs text-slate-400">
            {candidate.team_name}
          </p>
        </div>

        <div className="space-y-2.5 border-t border-white/5 pt-4 text-xs font-mono">
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Golden Boot Prob</span>
            <span className="text-fifagold font-bold">{(candidate.p_golden_boot * 100).toFixed(1)}%</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Mean Goals</span>
            <span className="text-white font-semibold">{candidate.mean_goals.toFixed(1)} goals</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">QF Survival</span>
            <span className="text-slate-300">{(qfProb * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
