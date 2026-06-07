import React, { useState, useMemo } from 'react';
import useSWR from 'swr';
import { TrophyIcon, SoccerBallIcon, WarningIcon } from '../components/Icons';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

export default function GoldenBoot() {
  const { data: bootData, error: bootError } = useSWR('/players/golden-boot?limit=40', fetcher);
  const { data: winnerData, error: winnerError } = useSWR('/predictions/winner', fetcher);

  const [minQfProb, setMinQfProb] = useState(0); // Quarterfinal survival threshold (0%, 15%, 30%, 50%)
  const [searchQuery, setSearchQuery] = useState('');

  const loading = !bootData || !winnerData;
  const error = bootError || winnerError;

  // Map team names to QF probabilities for joining datasets
  const teamQfMap = useMemo(() => {
    if (!winnerData) return {};
    const map = {};
    winnerData.teams.forEach((t) => {
      map[t.team_name.toLowerCase()] = t.p_qf;
    });
    return map;
  }, [winnerData]);

  // Filter candidates based on name search and QF survival threshold
  const filteredCandidates = useMemo(() => {
    if (!bootData) return [];
    return bootData.leaderboard.filter((c) => {
      const qfProb = teamQfMap[c.team_name.toLowerCase()] || 0.0;
      const matchesQf = qfProb * 100 >= minQfProb;
      const matchesSearch = c.player_name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            c.team_name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesQf && matchesSearch;
    });
  }, [bootData, teamQfMap, minQfProb, searchQuery]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 rounded-full border-t-2 border-fifagold animate-spin"></div>
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest">
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
  const remainder = filteredCandidates.slice(3);

  return (
    <div className="space-y-12 animate-fade-in py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Golden Boot Projections
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl">
            Simulated probabilities for the top tournament goalscorer candidates. Uses Monte Carlo matches progression to model expected minutes.
          </p>
        </div>

        {/* Filters Panel */}
        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          {/* Search */}
          <input
            type="text"
            placeholder="Search candidates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-full px-4 py-2 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full sm:w-48 font-sans"
          />

          {/* QF Filter */}
          <select
            value={minQfProb}
            onChange={(e) => setMinQfProb(Number(e.target.value))}
            className="bg-white/5 border border-white/10 rounded-full px-4 py-2 text-xs text-white focus:outline-none focus:border-fifagold/40 cursor-pointer font-sans"
          >
            <option value={0} className="bg-[#0b0d17]">All Teams</option>
            <option value={15} className="bg-[#0b0d17]">QF Survival &gt; 15%</option>
            <option value={30} className="bg-[#0b0d17]">QF Survival &gt; 30%</option>
            <option value={50} className="bg-[#0b0d17]">QF Survival &gt; 50%</option>
          </select>
        </div>
      </div>

      {/* Top 3 Podium Cards */}
      {podium.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-end">
          {/* 2nd Place */}
          {podium[1] && (
            <PodiumCard candidate={podium[1]} rank={2} qfProb={teamQfMap[podium[1].team_name.toLowerCase()] || 0} />
          )}

          {/* 1st Place (Center and larger) */}
          {podium[0] && (
            <PodiumCard candidate={podium[0]} rank={1} qfProb={teamQfMap[podium[0].team_name.toLowerCase()] || 0} featured />
          )}

          {/* 3rd Place */}
          {podium[2] && (
            <PodiumCard candidate={podium[2]} rank={3} qfProb={teamQfMap[podium[2].team_name.toLowerCase()] || 0} />
          )}
        </div>
      )}

      {/* Leaderboard Table List */}
      <div className="doppelrand-card">
        <div className="doppelrand-inner space-y-4">
          <h3 className="text-xl font-display font-semibold text-white">Full Leaderboard</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-white/5 text-[10px] uppercase font-mono text-slate-400 tracking-wider">
                  <th className="py-3 px-4 w-12 text-center">Rank</th>
                  <th className="py-3 px-4">Player</th>
                  <th className="py-3 px-4">Squad</th>
                  <th className="py-3 px-4 text-center">Exp Minutes</th>
                  <th className="py-3 px-4 text-center">QF Reach</th>
                  <th className="py-3 px-4">Goal Density (P10 - Mean - P90)</th>
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
                    const qf = teamQfMap[c.team_name.toLowerCase()] || 0.0;
                    return (
                      <tr key={c.reep_player_id} className="hover:bg-white/[0.02] transition-all duration-200">
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
                          {/* Goal density bar visual */}
                          <div className="space-y-1">
                            <div className="flex justify-between items-center text-[9px] font-mono text-slate-500">
                              <span>P50: {c.p50_goals.toFixed(0)}</span>
                              <span>Mean: {c.mean_goals.toFixed(1)}</span>
                              <span>P90: {c.p90_goals.toFixed(0)}</span>
                            </div>
                            <div className="h-1.5 w-full bg-white/5 rounded-full relative overflow-hidden">
                              {/* Range bar */}
                              <div 
                                style={{
                                  left: `${(c.p50_goals / 10) * 100}%`,
                                  width: `${((c.p90_goals - c.p50_goals) / 10) * 100}%`,
                                }}
                                className="absolute h-full bg-fifagold/20 rounded-full"
                              ></div>
                              {/* Mean dot */}
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
    </div>
  );
}

// Sub-component: Podium Cards for top 3 candidates
function PodiumCard({ candidate, rank, qfProb, featured }) {
  return (
    <div className={`doppelrand-card ${featured ? 'md:scale-105 border-fifagold/30 shadow-[0_25px_50px_rgba(212,175,55,0.1)]' : ''}`}>
      <div className="doppelrand-inner flex flex-col justify-between space-y-4">
        {/* Rank Badge */}
        <div className="flex justify-between items-center">
          <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
            rank === 1 ? 'bg-fifagold/20 border border-fifagold/30 text-fifagold' : 'bg-white/5 border border-white/10 text-slate-400'
          }`}>
            Rank {rank}
          </span>
          <SoccerBallIcon className={`w-5 h-5 ${featured ? 'text-fifagold animate-spin-slow' : 'text-slate-500'}`} />
        </div>

        {/* Candidate Details */}
        <div className="space-y-1">
          <h3 className="text-xl font-display font-extrabold text-white leading-tight">
            {candidate.player_name}
          </h3>
          <p className="text-xs text-slate-400">
            {candidate.team_name}
          </p>
        </div>

        {/* Stats */}
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
            <span className="text-slate-500">Exp Minutes</span>
            <span className="text-white font-semibold">{candidate.expected_minutes.toFixed(0)} min</span>
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
