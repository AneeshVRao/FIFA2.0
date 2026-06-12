import React, { useState } from 'react';
import useSWR from 'swr';
import { TrophyIcon, SoccerBallIcon, StadiumIcon, WarningIcon } from '../components/Icons';
import BroadcastMap from '../components/BroadcastMap';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

// Confederation Color Mapper (Ethereal Glass Neon Palette)
const getConfederationColor = (confed) => {
  switch (confed?.toUpperCase()) {
    case 'UEFA': return '#6366f1';      // Indigo
    case 'CONMEBOL': return '#10b981';  // Emerald
    case 'CONCACAF': return '#f59e0b';  // Amber
    case 'CAF': return '#ef4444';       // Red
    case 'AFC': return '#06b6d4';       // Cyan
    case 'OFC': return '#ec4899';       // Pink
    default: return 'hsl(45, 100%, 50%)'; // Gold
  }
};

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#050505]/90 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-2xl">
        <p className="text-white font-display font-bold text-lg mb-1">{payload[0].payload.name}</p>
        <div className="flex items-center gap-4">
          <p className="text-fifagold font-mono text-xl">{payload[0].value.toFixed(1)}%</p>
          <p className="text-[10px] text-slate-500 font-mono tracking-widest uppercase">{payload[0].payload.confederation}</p>
        </div>
      </div>
    );
  }
  return null;
};

export default function Dashboard({ onSelectMatch }) {
  const { data: winnerData, error: winnerError } = useSWR('/predictions/winner', fetcher);
  const { data: matchesData, error: matchesError } = useSWR('/predictions/matches', fetcher);
  const { data: venuesData, error: venuesError } = useSWR('/predictions/venues', fetcher);
  const { data: bootData, error: bootError } = useSWR('/players/golden-boot?limit=5', fetcher);

  const [selectedVenueId, setSelectedVenueId] = useState('v_mexicocity');
  const [searchQuery, setSearchQuery] = useState('');

  const loading = !winnerData || !matchesData || !venuesData || !bootData;
  const error = winnerError || matchesError || venuesError || bootError;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] gap-8">
        <div className="relative flex items-center justify-center">
          <div className="absolute w-32 h-32 rounded-full border border-fifagold/20 border-t-fifagold animate-spin"></div>
          <TrophyIcon className="w-8 h-8 text-fifagold/50 animate-pulse" />
        </div>
        <p className="font-mono text-[10px] text-white/40 uppercase tracking-[0.3em] animate-pulse">
          Synchronizing Telemetry...
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
          <h3 className="text-3xl font-display font-semibold text-white tracking-tight">Telemetry Sync Failure</h3>
          <p className="text-sm text-slate-400 font-mono tracking-widest uppercase">
            Backend Prediction Engine Offline
          </p>
        </div>
      </div>
    );
  }

  // Get top 10 champion contenders for the bar chart
  const chartData = winnerData.teams.slice(0, 10).map((t) => ({
    name: t.team_name,
    probability: t.p_champion * 100,
    confederation: t.confederation,
  }));

  const getFlightPath = (venueId) => {
    const pairs = {
      v_mexicocity: 'v_losangeles', v_guadalajara: 'v_mexicocity', v_monterrey: 'v_dallas',
      v_losangeles: 'v_sanfrancisco', v_sanfrancisco: 'v_seattle', v_seattle: 'v_vancouver',
      v_vancouver: 'v_toronto', v_toronto: 'v_boston', v_boston: 'v_newyork',
      v_newyork: 'v_philadelphia', v_philadelphia: 'v_atlanta', v_atlanta: 'v_miami',
      v_miami: 'v_houston', v_houston: 'v_dallas', v_dallas: 'v_kansascity', v_kansascity: 'v_toronto',
    };
    
    const startId = pairs[venueId] || 'v_newyork';
    const dists = { v_mexicocity: 2420, v_guadalajara: 460, v_monterrey: 920, v_losangeles: 550, v_sanfrancisco: 1100, v_seattle: 230, v_vancouver: 3350, v_toronto: 900, v_boston: 300, v_newyork: 150, v_philadelphia: 1050, v_atlanta: 980, v_miami: 1550, v_houston: 380, v_dallas: 780, v_kansascity: 1850 };
    const alts = { v_mexicocity: 2240, v_guadalajara: 1560, v_monterrey: 535, v_losangeles: 40, v_sanfrancisco: 12, v_seattle: 4, v_vancouver: 5, v_toronto: 76, v_boston: 85, v_newyork: 10, v_philadelphia: 5, v_atlanta: 315, v_miami: 3, v_houston: 15, v_dallas: 180, v_kansascity: 275 };

    return {
      start: { id: startId },
      end: { id: venueId },
      distance_km: dists[venueId] || 1000,
      altitude_diff_m: Math.abs((alts[venueId] || 0) - (alts[startId] || 0))
    };
  };

  return (
    <div className="space-y-32 animate-fade-in-up py-24">
      {/* Hero Header Section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-12 border-b border-white/10 pb-16">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-fifagold/20 bg-fifagold/5 mb-8">
            <TrophyIcon className="w-4 h-4 text-fifagold" /> 
            <span className="text-[10px] text-fifagold uppercase tracking-[0.2em] font-medium">Phase 4 Telemetry Active</span>
          </div>
          <h1 className="text-5xl lg:text-7xl font-display font-extrabold text-white tracking-tighter leading-[1.1]">
            Global <span className="text-transparent bg-clip-text bg-gradient-to-r from-fifagold to-fifagreen">Forecast</span>
          </h1>
          <p className="text-lg text-slate-400 mt-6 font-sans leading-relaxed">
            Real-time multi-dimensional Monte Carlo simulations mapping tournament probability surfaces across 16 host cities.
          </p>
        </div>

        {/* Top Winner Card (Doppelrand) */}
        <div className="doppelrand-card w-full lg:w-96 shrink-0 group">
          <div className="doppelrand-inner flex flex-col justify-between h-48 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-fifagold/10 via-[#0b0d17] to-[#0b0d17]">
            <div className="flex justify-between items-start">
              <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center border border-white/10 group-hover:scale-110 transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]">
                <TrophyIcon className="w-6 h-6 text-fifagold" />
              </div>
              <span className="text-[10px] uppercase font-mono text-fifagold/50 tracking-[0.2em]">Model Favorite</span>
            </div>
            
            <div>
              <h2 className="text-4xl font-display font-bold text-white tracking-tight">
                {winnerData.teams[0]?.team_name}
              </h2>
              <div className="flex items-end gap-3 mt-2">
                <div className="text-3xl font-mono font-light text-fifagold">
                  {(winnerData.teams[0]?.p_champion * 100).toFixed(1)}<span className="text-xl text-fifagold/50">%</span>
                </div>
                <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mb-1">Win Probability</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: 3D Globe + Venue Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 h-[600px] xl:h-[700px]">
          <BroadcastMap
            selectedVenueId={selectedVenueId}
            onSelectVenue={(vid) => setSelectedVenueId(vid)}
            flightPath={getFlightPath(selectedVenueId)}
          />
        </div>

        {/* Selected Venue Details (Doppelrand Bezel Card) */}
        <div className="lg:col-span-4 doppelrand-card h-full group">
          <div className="doppelrand-inner flex flex-col justify-between h-full bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-white/5 via-[#0b0d17] to-[#0b0d17] p-10">
            <div className="space-y-8">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                  <StadiumIcon className="w-5 h-5 text-white/50" />
                </div>
                <div className="text-[10px] text-white/40 uppercase tracking-[0.2em] font-mono">
                  Venue Telemetry
                </div>
              </div>
              
              <div>
                <h2 className="text-4xl font-display font-bold text-white tracking-tight leading-none mb-4">
                  {venuesData.venues.find((v) => v.venue_id === selectedVenueId)?.city}
                </h2>
                <p className="text-lg text-slate-400 font-sans">
                  {venuesData.venues.find((v) => v.venue_id === selectedVenueId)?.venue_name}
                </p>
              </div>
            </div>

            <div className="space-y-6 pt-12 border-t border-white/5">
              <div className="flex justify-between items-end">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Altitude (ASL)</span>
                <span className="text-2xl font-mono text-white">
                  {venuesData.venues.find((v) => v.venue_id === selectedVenueId)?.altitude_m} <span className="text-sm text-slate-500">m</span>
                </span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Matches Hosted</span>
                <span className="text-2xl font-mono text-white">
                  {venuesData.venues.find((v) => v.venue_id === selectedVenueId)?.matches_hosted}
                </span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">Nation</span>
                <span className="text-sm font-display uppercase tracking-widest text-fifagold">
                  {venuesData.venues.find((v) => v.venue_id === selectedVenueId)?.nation}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Asymmetrical Bento Grid: Top 5 Golden Boot & Champion Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Golden Boot Top 5 Stack */}
        <div className="lg:col-span-4 space-y-6">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 rounded-full bg-fifagold/10 flex items-center justify-center border border-fifagold/20">
              <SoccerBallIcon className="w-5 h-5 text-fifagold" />
            </div>
            <h3 className="text-2xl font-display font-bold text-white tracking-tight">
              Golden Boot Projections
            </h3>
          </div>
          
          <div className="space-y-4">
            {bootData.leaderboard.slice(0, 5).map((player, idx) => (
              <div key={player.reep_player_id} className="doppelrand-card group cursor-default">
                <div className="doppelrand-inner p-6 flex items-center justify-between group-hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center gap-6">
                    <div className="text-2xl font-mono font-light text-white/20 group-hover:text-fifagold transition-colors">
                      0{idx + 1}
                    </div>
                    <div>
                      <h4 className="text-lg font-display font-bold text-white truncate max-w-[150px]">
                        {player.player_name}
                      </h4>
                      <p className="text-[10px] text-slate-400 font-mono tracking-widest uppercase mt-1">{player.team_name}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-mono text-fifagold">
                      {(player.p_golden_boot * 100).toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-slate-500 font-mono tracking-widest uppercase mt-1">
                      {player.mean_goals.toFixed(1)} xG
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Champion Probability Chart */}
        <div className="lg:col-span-8 doppelrand-card h-full">
          <div className="doppelrand-inner h-full flex flex-col p-10 relative overflow-hidden">
            <div className="flex items-center justify-between mb-12">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center border border-white/10">
                  <TrophyIcon className="w-5 h-5 text-white/50" />
                </div>
                <div>
                  <h3 className="text-2xl font-display font-bold text-white tracking-tight">Champion Probability Surface</h3>
                  <div className="text-[10px] uppercase font-mono text-slate-500 tracking-widest mt-1">Top 10 Global Contenders</div>
                </div>
              </div>
            </div>
            
            <div className="flex-1 min-h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                  <XAxis 
                    dataKey="name" 
                    stroke="rgba(255,255,255,0.2)" 
                    tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11, fontFamily: 'Space Grotesk' }}
                    axisLine={false}
                    tickLine={false}
                    dy={10}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.2)" 
                    tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 11, fontFamily: 'JetBrains Mono' }}
                    tickFormatter={(val) => `${val}%`}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                  <Bar dataKey="probability" radius={[4, 4, 0, 0]} maxBarSize={60}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={getConfederationColor(entry.confederation)} fillOpacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
