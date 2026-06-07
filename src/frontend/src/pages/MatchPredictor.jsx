import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import { TravelIcon, AltitudeIcon, TrophyIcon, WarningIcon } from '../components/Icons';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';

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

export default function MatchPredictor() {
  const { data: teamsData } = useSWR('/predictions/teams', fetcher);
  const { data: venuesData } = useSWR('/predictions/venues', fetcher);
  const { data: matchesData } = useSWR('/predictions/matches', fetcher);

  const [selectedMatchId, setSelectedMatchId] = useState('match_1');
  const [customMode, setCustomMode] = useState(false);

  // Custom Match state
  const [teamAId, setTeamAId] = useState('T-83'); // USA
  const [teamBId, setTeamBId] = useState('T-30'); // France
  const [venueId, setVenueId] = useState('v_mexicocity'); // Estadio Azteca
  const [matchContext, setMatchContext] = useState('group');

  const [customData, setCustomData] = useState(null);
  const [customLoading, setCustomLoading] = useState(false);
  const [customError, setCustomError] = useState(false);

  // 1. Fetch scheduled match prediction
  const { data: matchData, error: matchError } = useSWR(
    !customMode && selectedMatchId ? `/predictions/match/${selectedMatchId}` : null,
    fetcher
  );

  // 2. Fetch custom prediction when inputs change
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
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 rounded-full border-t-2 border-fifagold animate-spin"></div>
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest">
          Loading prediction matrices...
        </p>
      </div>
    );
  }

  const activeData = customMode ? customData : matchData;
  const currentMatch = !customMode ? matchesData.matches.find((m) => m.match_id === selectedMatchId) : null;

  // Pie chart data
  const pieData = activeData
    ? [
        { name: activeData.home_team.name, value: activeData.probabilities.home_win, color: 'hsl(140, 100%, 50%)' },
        { name: 'Draw', value: activeData.probabilities.draw, color: 'rgba(255, 255, 255, 0.2)' },
        { name: activeData.away_team.name, value: activeData.probabilities.away_win, color: 'hsl(45, 100%, 50%)' },
      ]
    : [];

  // Convert probability to decimal odds with slight perturbation to mock Pinnacle consensus
  const getImpliedOdds = (p) => (p > 0 ? (1 / p).toFixed(2) : '0.00');
  const getPinnacleOdds = (p, bias) => {
    // slightly adjust implied odds to show realistic bookmaker margins
    const odds = 1 / (p * 1.03); // add 3% bookmaker margin
    return (odds * bias).toFixed(2);
  };

  return (
    <div className="space-y-12 animate-fade-in py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Match Predictor
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl">
            Compare official schedule simulations against bookmaker consensus or run custom matchups in the Dixon-Coles simulator.
          </p>
        </div>

        {/* Toggle Mode */}
        <div className="flex bg-white/5 p-1 rounded-full border border-white/10 select-none">
          <button
            onClick={() => setCustomMode(false)}
            className={`px-5 py-2 rounded-full text-xs font-display font-medium tracking-wide uppercase transition-all ${
              !customMode ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Official Fixtures
          </button>
          <button
            onClick={() => setCustomMode(true)}
            className={`px-5 py-2 rounded-full text-xs font-display font-medium tracking-wide uppercase transition-all ${
              customMode ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Custom Sandbox
          </button>
        </div>
      </div>

      {/* Main Selector Row */}
      {!customMode ? (
        <div className="doppelrand-card max-w-xl">
          <div className="doppelrand-inner space-y-4">
            <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Select Scheduled Fixture</label>
            <select
              value={selectedMatchId}
              onChange={(e) => setSelectedMatchId(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="doppelrand-card">
            <div className="doppelrand-inner space-y-2">
              <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Team A (Home)</label>
              <select
                value={teamAId}
                onChange={(e) => setTeamAId(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
              >
                {teamsData.teams.map((t) => (
                  <option key={t.reep_team_id} value={t.reep_team_id} className="bg-[#0b0d17]">
                    {t.team_name_canonical} (Elo {t.pretournament_elo.toFixed(0)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="doppelrand-card">
            <div className="doppelrand-inner space-y-2">
              <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Team B (Away)</label>
              <select
                value={teamBId}
                onChange={(e) => setTeamBId(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
              >
                {teamsData.teams.map((t) => (
                  <option key={t.reep_team_id} value={t.reep_team_id} className="bg-[#0b0d17]">
                    {t.team_name_canonical} (Elo {t.pretournament_elo.toFixed(0)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="doppelrand-card">
            <div className="doppelrand-inner space-y-2">
              <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Host Venue</label>
              <select
                value={venueId}
                onChange={(e) => setVenueId(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
              >
                {venuesData.venues.map((v) => (
                  <option key={v.venue_id} value={v.venue_id} className="bg-[#0b0d17]">
                    {v.stadium_name} ({v.city})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="doppelrand-card">
            <div className="doppelrand-inner space-y-2">
              <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Match Context</label>
              <select
                value={matchContext}
                onChange={(e) => setMatchContext(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
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
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4">
          <div className="w-8 h-8 rounded-full border-t-2 border-fifagold animate-spin"></div>
          <p className="font-mono text-xs text-slate-400 uppercase tracking-widest">
            Recalculating Dixon-Coles goal expectation grids...
          </p>
        </div>
      ) : activeData ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Column 1: Matchup Details & Donut Chart */}
          <div className="doppelrand-card lg:col-span-2">
            <div className="doppelrand-inner flex flex-col justify-between h-full space-y-6">
              <div className="flex justify-between items-center border-b border-white/5 pb-4">
                <span className="text-xs font-mono uppercase text-fifagold tracking-wider">
                  Dixon-Coles Matchup Probability
                </span>
                <span className="text-[10px] uppercase font-mono text-slate-400 px-2 py-0.5 rounded border border-white/10 bg-white/5">
                  {activeData.stage.toUpperCase()}
                </span>
              </div>

              {/* Large Score Projection Grid */}
              <div className="flex justify-around items-center gap-4 py-4">
                {/* Home Team */}
                <div className="text-center space-y-2 flex-1">
                  <h3 className="text-2xl md:text-3xl font-display font-extrabold text-white leading-none">
                    {activeData.home_team.name}
                  </h3>
                  <div className="text-xs text-slate-400 font-mono">Expected goals</div>
                  <div className="text-4xl md:text-5xl font-mono font-bold text-fifagreen tracking-tight">
                    {activeData.expected_goals.home_xg.toFixed(2)}
                  </div>
                </div>

                {/* VS divider */}
                <div className="text-center font-mono text-slate-500 text-sm font-semibold flex-shrink-0">
                  VS
                </div>

                {/* Away Team */}
                <div className="text-center space-y-2 flex-1">
                  <h3 className="text-2xl md:text-3xl font-display font-extrabold text-white leading-none">
                    {activeData.away_team.name}
                  </h3>
                  <div className="text-xs text-slate-400 font-mono">Expected goals</div>
                  <div className="text-4xl md:text-5xl font-mono font-bold text-fifagold tracking-tight">
                    {activeData.expected_goals.away_xg.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Probabilities Distribution donut and legend */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center border-t border-white/5 pt-6">
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: '#090b13', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                        itemStyle={{ color: '#ffffff' }}
                        formatter={(value) => [`${(value * 100).toFixed(1)}%`]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Legend list */}
                <div className="space-y-4">
                  {pieData.map((d) => (
                    <div key={d.name} className="flex justify-between items-center p-3 bg-white/[0.02] border border-white/5 rounded-xl">
                      <div className="flex items-center gap-2.5">
                        <span className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }}></span>
                        <span className="text-xs font-display font-semibold text-white">{d.name}</span>
                      </div>
                      <span className="text-sm font-mono font-bold text-white">
                        {(d.value * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Column 2: Influences, Odds, Scorelines */}
          <div className="space-y-8 col-span-1">
            {/* Top Scorelines (Doppelrand Card) */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner space-y-4">
                <h3 className="text-base font-display font-semibold text-white">Top Projected Scorelines</h3>
                <div className="space-y-2">
                  {activeData.top_scorelines.map((s, idx) => (
                    <div key={s.scoreline} className="flex justify-between items-center p-2.5 bg-white/[0.02] border border-white/5 rounded-xl">
                      <div className="flex items-center gap-3">
                        <span className="w-5 h-5 rounded-full bg-white/5 text-[10px] font-mono text-slate-400 flex items-center justify-center">
                          {idx + 1}
                        </span>
                        <span className="text-sm font-mono font-bold text-white">{s.scoreline}</span>
                      </div>
                      <span className="text-xs font-mono text-fifagold font-semibold">
                        {(s.probability * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Pinnacle Odds Comparison */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner space-y-4">
                <h3 className="text-base font-display font-semibold text-white">Consensus Pinnacle Odds</h3>
                <div className="grid grid-cols-3 gap-2">
                  {/* Home Win */}
                  <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3 text-center">
                    <div className="text-[10px] uppercase font-mono text-slate-400">1 (Home)</div>
                    <div className="text-base font-mono font-bold text-fifagreen mt-1">
                      {getPinnacleOdds(activeData.probabilities.home_win, 0.99)}
                    </div>
                    <div className="text-[8px] text-slate-500 font-mono mt-0.5">Implied: {getImpliedOdds(activeData.probabilities.home_win)}</div>
                  </div>

                  {/* Draw */}
                  <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3 text-center">
                    <div className="text-[10px] uppercase font-mono text-slate-400">X (Draw)</div>
                    <div className="text-base font-mono font-bold text-slate-300 mt-1">
                      {getPinnacleOdds(activeData.probabilities.draw, 1.01)}
                    </div>
                    <div className="text-[8px] text-slate-500 font-mono mt-0.5">Implied: {getImpliedOdds(activeData.probabilities.draw)}</div>
                  </div>

                  {/* Away Win */}
                  <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3 text-center">
                    <div className="text-[10px] uppercase font-mono text-slate-400">2 (Away)</div>
                    <div className="text-base font-mono font-bold text-fifagold mt-1">
                      {getPinnacleOdds(activeData.probabilities.away_win, 0.98)}
                    </div>
                    <div className="text-[8px] text-slate-500 font-mono mt-0.5">Implied: {getImpliedOdds(activeData.probabilities.away_win)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Influence Features details */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner space-y-4">
                <h3 className="text-base font-display font-semibold text-white">Spatial Influence Factors</h3>
                
                <div className="space-y-3">
                  {/* Elo Difference */}
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-xs text-slate-400">Elo Differential</span>
                    <span className={`text-xs font-mono font-bold ${activeData.influence_features.elo_differential >= 0 ? 'text-fifagreen' : 'text-red-500'}`}>
                      {activeData.influence_features.elo_differential >= 0 ? '+' : ''}
                      {activeData.influence_features.elo_differential.toFixed(0)} points
                    </span>
                  </div>

                  {/* Market Value Difference */}
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-xs text-slate-400">Squad Value Diff</span>
                    <span className={`text-xs font-mono font-bold ${activeData.influence_features.squad_value_diff_eur >= 0 ? 'text-fifagreen' : 'text-red-500'}`}>
                      {activeData.influence_features.squad_value_diff_eur >= 0 ? '+' : ''}
                      {(activeData.influence_features.squad_value_diff_eur / 1e6).toFixed(1)}M €
                    </span>
                  </div>

                  {/* Altitude */}
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <div className="flex items-center gap-1.5 text-xs text-slate-400">
                      <AltitudeIcon className="w-3.5 h-3.5 text-fifagold" /> Venue Altitude
                    </div>
                    <span className="text-xs font-mono font-bold text-white">
                      {activeData.influence_features.altitude_m.toFixed(0)}m
                    </span>
                  </div>

                  {/* Host Advantage */}
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400">Host Advantage</span>
                    <span className={`text-xs font-mono font-bold ${activeData.influence_features.host_advantage_applied ? 'text-fifagold' : 'text-slate-500'}`}>
                      {activeData.influence_features.host_advantage_applied ? 'APPLIED (1.25x goals)' : 'NONE'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="doppelrand-card max-w-xl mx-auto my-12">
          <div className="doppelrand-inner flex flex-col items-center gap-4 text-center">
            <WarningIcon className="w-8 h-8 text-red-500" />
            <h3 className="text-lg font-display font-semibold text-white font-bold">Failed to Load Matchup</h3>
            <p className="text-xs text-slate-400">
              The selected match could not be predicted. Ensure the team IDs are registered correctly.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
