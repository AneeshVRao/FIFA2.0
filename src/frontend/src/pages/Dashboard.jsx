import React, { useState } from 'react';
import useSWR from 'swr';
import { TrophyIcon, SoccerBallIcon, StadiumIcon, WarningIcon } from '../components/Icons';
import BroadcastMap from '../components/BroadcastMap';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

export default function Dashboard() {
  const { data: winnerData, error: winnerError } = useSWR('/predictions/winner', fetcher);
  const { data: matchesData, error: matchesError } = useSWR('/predictions/matches', fetcher);
  const { data: venuesData, error: venuesError } = useSWR('/predictions/venues', fetcher);

  const [selectedVenueId, setSelectedVenueId] = useState('v_mexicocity');
  const [searchQuery, setSearchQuery] = useState('');

  const loading = !winnerData || !matchesData || !venuesData;
  const error = winnerError || matchesError || venuesError;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 rounded-full border-t-2 border-fifagold animate-spin"></div>
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest">
          Synchronizing broadcast telemetry...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="doppelrand-card max-w-xl mx-auto my-12">
        <div className="doppelrand-inner flex flex-col items-center gap-4 text-center">
          <WarningIcon className="w-8 h-8 text-red-500 animate-pulse" />
          <h3 className="text-lg font-display font-semibold text-white">Telemetry Sync Failure</h3>
          <p className="text-xs text-slate-400">
            Failed to connect to the prediction engine. Ensure the backend FastAPI server is running.
          </p>
        </div>
      </div>
    );
  }

  // Get top 8 champion contenders for the bar chart
  const chartData = winnerData.teams.slice(0, 8).map((t) => ({
    name: t.team_name,
    probability: t.p_champion * 100,
  }));

  // Filter matches based on search query
  const filteredMatches = matchesData.matches
    .filter((m) => {
      const q = searchQuery.toLowerCase();
      return (
        m.team_a_name.toLowerCase().includes(q) ||
        m.team_b_name.toLowerCase().includes(q) ||
        m.venue_name.toLowerCase().includes(q) ||
        m.stage.toLowerCase().includes(q)
      );
    })
    .slice(0, 8); // limit to 8 results for dashboard view

  const resolvedVenue = venuesData.venues.find((v) => v.venue_id === selectedVenueId);

  return (
    <div className="space-y-12 animate-fade-in py-6">
      {/* Hero Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-fifagold/20 bg-fifagold/5 text-[10px] text-fifagold uppercase tracking-[0.2em] font-medium mb-3">
            <TrophyIcon className="w-3.5 h-3.5" /> Phase 4 Telemetry Active
          </div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Broadcast Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl">
            Real-time simulations and spatial telemetry mapped across the 16 host cities of the FIFA World Cup 2026.
          </p>
        </div>

        {/* Top Winner Card */}
        <div className="doppelrand-card w-full md:w-auto min-w-[280px]">
          <div className="doppelrand-inner flex justify-between items-center">
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Model Favorite</span>
              <h2 className="text-2xl font-display font-bold text-white mt-1">
                {winnerData.teams[0]?.team_name}
              </h2>
            </div>
            <div className="text-right">
              <span className="text-[10px] uppercase font-mono text-fifagold tracking-wider">Win Prob</span>
              <div className="text-2xl font-mono font-bold text-fifagold mt-1">
                {(winnerData.teams[0]?.p_champion * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: 3D Globe + Venue Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 h-[500px]">
          <BroadcastMap
            selectedVenueId={selectedVenueId}
            onSelectVenue={(vid) => setSelectedVenueId(vid)}
          />
        </div>

        {/* Selected Venue Details (Doppelrand Bezel Card) */}
        <div className="doppelrand-card h-full">
          <div className="doppelrand-inner flex flex-col justify-between h-full space-y-6">
            <div>
              <div className="flex items-center gap-2 text-fifagold text-xs uppercase tracking-widest font-mono mb-2">
                <StadiumIcon className="w-4 h-4" /> Venue Telemetry
              </div>
              <h2 className="text-2xl font-display font-bold text-white">
                {resolvedVenue?.stadium_name}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                {resolvedVenue?.city}, {resolvedVenue?.host_nation}
              </p>
            </div>

            <div className="space-y-4 flex-1 my-4">
              <div className="flex justify-between items-center border-b border-white/5 py-2">
                <span className="text-xs text-slate-400">Altitude</span>
                <span className="text-sm font-mono font-semibold text-white">
                  {resolvedVenue?.altitude_m.toLocaleString()} m
                  {resolvedVenue?.altitude_m > 1500 && (
                    <span className="text-fifagold text-[10px] ml-1.5 uppercase font-mono bg-fifagold/10 border border-fifagold/20 px-1.5 py-0.5 rounded">
                      High Altitude
                    </span>
                  )}
                </span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 py-2">
                <span className="text-xs text-slate-400">Capacity</span>
                <span className="text-sm font-mono font-semibold text-white">
                  {resolvedVenue?.capacity.toLocaleString()} seats
                </span>
              </div>
              <div className="flex justify-between items-center border-b border-white/5 py-2">
                <span className="text-xs text-slate-400">Coordinates</span>
                <span className="text-xs font-mono text-slate-300">
                  {resolvedVenue?.latitude.toFixed(4)}° N, {resolvedVenue?.longitude.toFixed(4)}° W
                </span>
              </div>
            </div>

            <div className="p-3 bg-white/5 border border-white/10 rounded-xl">
              <div className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Altitudinal Drag Offset</div>
              <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                {resolvedVenue?.altitude_m > 1500 
                  ? 'High altitude reduces air resistance. Ball velocity increases but aerodynamic curve diminishes, boosting expected goals (xG) on long-range strikes by up to 8%.'
                  : 'Low altitude venue. Ball movement exhibits standard aerodynamic curvature and drag coefficients.'
                }
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Champion Probabilities Chart + Search Fixtures */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Chart Card */}
        <div className="doppelrand-card">
          <div className="doppelrand-inner space-y-6">
            <h3 className="text-xl font-display font-semibold text-white">
              Model Champion Probabilities
            </h3>
            
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30, top: 0, bottom: 0 }}>
                  <XAxis type="number" stroke="rgba(255,255,255,0.2)" fontSize={10} tickFormatter={(v) => `${v}%`} />
                  <YAxis dataKey="name" type="category" stroke="rgba(255,255,255,0.4)" fontSize={10} width={80} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#090b13', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    labelStyle={{ color: '#ffffff', fontWeight: 'bold' }}
                    itemStyle={{ color: 'hsl(45, 100%, 50%)' }}
                    formatter={(v) => [`${v.toFixed(2)}%`, 'Champion Probability']}
                  />
                  <Bar dataKey="probability" fill="hsl(45, 100%, 50%)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Fixture Navigator Card */}
        <div className="doppelrand-card">
          <div className="doppelrand-inner flex flex-col justify-between h-full space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <h3 className="text-xl font-display font-semibold text-white">
                Fixture Navigator
              </h3>
              
              <input
                type="text"
                placeholder="Search teams or venues..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-full px-4 py-1.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full md:w-56 font-sans transition-all"
              />
            </div>

            <div className="space-y-3 max-h-[280px] overflow-y-auto pr-2 flex-1">
              {filteredMatches.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-12">No matching fixtures found.</p>
              ) : (
                filteredMatches.map((m) => (
                  <div key={m.match_id} className="flex justify-between items-center bg-white/[0.02] border border-white/5 rounded-2xl p-3 hover:bg-white/5 transition-all duration-300">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] uppercase font-mono text-fifagold px-1.5 py-0.5 rounded bg-fifagold/10 border border-fifagold/20">
                          {m.stage.toUpperCase()}
                        </span>
                        {m.group_code && (
                          <span className="text-[9px] uppercase font-mono text-slate-400">
                            Group {m.group_code}
                          </span>
                        )}
                      </div>
                      
                      <div className="text-sm font-display font-bold text-white mt-1.5 flex items-center gap-1.5">
                        <span className="truncate">{m.team_a_name}</span>
                        <span className="text-slate-500 font-mono text-xs">vs</span>
                        <span className="truncate">{m.team_b_name}</span>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <div className="text-[10px] text-slate-400 font-sans">{m.venue_name}</div>
                      <div className="text-[9px] text-slate-500 font-mono mt-0.5">{m.altitude_m}m altitude</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
