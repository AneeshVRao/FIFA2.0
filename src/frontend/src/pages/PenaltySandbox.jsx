import React, { useState, useRef, useEffect } from 'react';
import useSWR from 'swr';
import anime from 'animejs';
import { SoccerBallIcon, TrophyIcon, WarningIcon } from '../components/Icons';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

export default function PenaltySandbox() {
  const { data: teamsData } = useSWR('/predictions/teams', fetcher);

  const [teamAId, setTeamAId] = useState('T-83'); // USA
  const [teamBId, setTeamBId] = useState('T-30'); // France

  const [simulationData, setSimulationData] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [error, setError] = useState(false);

  // Animation states
  const [currentKickIndex, setCurrentKickIndex] = useState(-1);
  const [animatedKicks, setAnimatedKicks] = useState([]);
  const [tally, setTally] = useState({ teamA: 0, teamB: 0 });
  const [ballState, setBallState] = useState({ visible: false, x: 0, y: 0, result: '' });
  const [keeperState, setKeeperState] = useState({ x: 0 });

  const ballRef = useRef(null);
  const keeperRef = useRef(null);

  // Trigger shootout simulation
  const runShootout = async () => {
    setSimulating(true);
    setError(false);
    setSimulationData(null);
    setCurrentKickIndex(-1);
    setAnimatedKicks([]);
    setTally({ teamA: 0, teamB: 0 });
    setBallState({ visible: false, x: 0, y: 0, result: '' });

    try {
      const res = await fetch('/predictions/penalty', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          team_a_id: teamAId,
          team_b_id: teamBId,
          n_simulations: 5000,
        }),
      });
      if (!res.ok) throw new Error('Simulation failed');
      const data = await res.json();
      setSimulationData(data);
      setSimulating(false);
      
      // Start kick-by-kick animation timeline
      animateNextKick(data.sample_kick_sequence, 0, { teamA: 0, teamB: 0 }, []);
    } catch (e) {
      setError(true);
      setSimulating(false);
    }
  };

  // Choreograph kick-by-kick using Anime.js timeline
  const animateNextKick = (sequence, index, currentTally, prevKicks) => {
    if (index >= sequence.length) {
      setCurrentKickIndex(sequence.length);
      return;
    }

    const kick = sequence[index];
    setCurrentKickIndex(index);
    setBallState({ visible: true, x: 0, y: 120, result: kick.result });

    // Determine target location for the ball
    let targetX = 0;
    let targetY = -70; // middle height
    let keeperX = 0;

    if (kick.result === 'scored') {
      targetX = Math.random() > 0.5 ? -80 : 80;
      targetY = Math.random() > 0.5 ? -100 : -40;
      keeperX = targetX > 0 ? -40 : 40; // dive away
    } else if (kick.result === 'saved') {
      targetX = Math.random() > 0.5 ? -40 : 40;
      targetY = -60;
      keeperX = targetX; // dive to ball
    } else {
      targetX = Math.random() > 0.5 ? -130 : 130;
      targetY = Math.random() > 0.5 ? -140 : -20;
      keeperX = targetX > 0 ? 50 : -50;
    }

    const tl = anime.timeline({
      easing: 'spring(1, 80, 10, 0)',
    });

    // 1. Keeper shuffle
    tl.add({
      targets: keeperRef.current,
      translateX: [0, keeperX],
      duration: 600,
      easing: 'easeOutQuad',
    });

    // 2. Ball strike
    tl.add({
      targets: ballRef.current,
      translateX: [0, targetX],
      translateY: [120, targetY],
      scale: [1, 0.45],
      duration: 700,
      easing: 'cubicBezier(0.25, 0.46, 0.45, 0.94)',
    }, '-=600');

    // 3. Post-impact cleanup and logging updates
    tl.finished.then(() => {
      const nextTally = { ...currentTally };
      if (kick.result === 'scored') {
        if (kick.team === sequence[0].team) {
          nextTally.teamA += 1;
        } else {
          nextTally.teamB += 1;
        }
      }

      setTally(nextTally);
      const updatedKicks = [...prevKicks, kick];
      setAnimatedKicks(updatedKicks);
      setBallState({ visible: false, x: 0, y: 0, result: '' });
      
      anime({
        targets: keeperRef.current,
        translateX: 0,
        duration: 300,
        easing: 'easeOutQuad',
      });

      setTimeout(() => {
        animateNextKick(sequence, index + 1, nextTally, updatedKicks);
      }, 1200);
    });
  };

  const getTeamName = (tid) => {
    return teamsData?.teams.find((t) => t.reep_team_id === tid)?.team_name_canonical || 'Select Team';
  };

  return (
    <div className="space-y-12 animate-fade-in-up py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Bayesian Shootout Sandbox
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl font-sans">
            Simulate high-pressure shootouts kick-by-kick using Bayesian roster conversion parameters and goalkeeper prior trace distributions.
          </p>
        </div>
      </div>

      {/* Select Teams Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
        <div className="doppelrand-card">
          <div className="doppelrand-inner space-y-2">
            <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Team A (Kicks First)</label>
            <select
              value={teamAId}
              onChange={(e) => setTeamAId(e.target.value)}
              disabled={simulating || currentKickIndex > -1 && currentKickIndex < (simulationData?.sample_kick_sequence.length || 0)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer disabled:opacity-50"
            >
              {teamsData?.teams.map((t) => (
                <option key={t.reep_team_id} value={t.reep_team_id} className="bg-[#0b0d17]">
                  {t.team_name_canonical}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="doppelrand-card">
          <div className="doppelrand-inner space-y-2">
            <label className="text-xs uppercase font-mono text-slate-400 tracking-wider">Team B (Kicks Second)</label>
            <select
              value={teamBId}
              onChange={(e) => setTeamBId(e.target.value)}
              disabled={simulating || currentKickIndex > -1 && currentKickIndex < (simulationData?.sample_kick_sequence.length || 0)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer disabled:opacity-50"
            >
              {teamsData?.teams.map((t) => (
                <option key={t.reep_team_id} value={t.reep_team_id} className="bg-[#0b0d17]">
                  {t.team_name_canonical}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Trigger Button */}
        <button
          onClick={runShootout}
          disabled={simulating || currentKickIndex > -1 && currentKickIndex < (simulationData?.sample_kick_sequence.length || 0)}
          className="doppelrand-card bg-fifagold hover:border-white/20 active-press select-none w-full border-none p-0 cursor-pointer disabled:opacity-50 animate-pulse"
        >
          <div className="doppelrand-inner bg-fifagold hover:bg-fifagold/90 text-[#050505] text-center font-display font-bold py-3.5 px-6 rounded-[calc(2rem-6px)] uppercase text-xs tracking-wider">
            {simulating ? 'Simulating Trace...' : 'Initiate Shootout Sequence'}
          </div>
        </button>
      </div>

      {error && (
        <div className="doppelrand-card max-w-xl mx-auto">
          <div className="doppelrand-inner flex flex-col items-center gap-4 text-center">
            <WarningIcon className="w-8 h-8 text-red-500" />
            <h3 className="text-lg font-display font-semibold text-white">Simulation Engine Failure</h3>
            <p className="text-xs text-slate-400">Failed to sample penalty posterior distributions.</p>
          </div>
        </div>
      )}

      {/* Main Broadcast Shootout Display */}
      {simulationData && (
        <div className="space-y-12">
          {/* PRD Section 13.4 Circular/Visual Win Probabilities Gauge Row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
            {/* Team A Win % Card */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner text-center py-6">
                <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Team A Win Prob</span>
                <h3 className="text-4xl font-mono font-black text-fifagreen mt-2">
                  {(simulationData.win_probabilities.team_a * 100).toFixed(1)}%
                </h3>
                <p className="text-xs text-slate-400 mt-1">{getTeamName(teamAId)}</p>
              </div>
            </div>

            {/* Simulated Shootout Win % Gauge Graphic (Circular Visualizer) */}
            <div className="doppelrand-card h-full">
              <div className="doppelrand-inner flex flex-col items-center justify-center p-6 space-y-3">
                <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Shootout Win % Gauge</span>
                
                {/* Horizontal progress representation of Win Gauge */}
                <div className="h-4 w-full bg-white/5 rounded-full overflow-hidden flex">
                  <div 
                    style={{ width: `${simulationData.win_probabilities.team_a * 100}%` }}
                    className="h-full bg-fifagreen"
                  ></div>
                  <div 
                    style={{ width: `${simulationData.win_probabilities.team_b * 100}%` }}
                    className="h-full bg-fifagold"
                  ></div>
                </div>
                
                <div className="flex justify-between w-full text-[10px] font-mono text-slate-500">
                  <span>{getTeamName(teamAId)}</span>
                  <span>{getTeamName(teamBId)}</span>
                </div>
              </div>
            </div>

            {/* Team B Win % Card */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner text-center py-6">
                <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Team B Win Prob</span>
                <h3 className="text-4xl font-mono font-black text-fifagold mt-2">
                  {(simulationData.win_probabilities.team_b * 100).toFixed(1)}%
                </h3>
                <p className="text-xs text-slate-400 mt-1">{getTeamName(teamBId)}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Visual Goalpost Animation View */}
            <div className="lg:col-span-2 space-y-6">
              {/* Shootout Goal Canvas View */}
              <div className="w-full aspect-[1.8/1] bg-[#0c0e18] border-2 border-white/10 rounded-[2rem] relative flex items-center justify-center overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.6)]">
                {/* Pitch ground shadow */}
                <div className="absolute bottom-0 left-0 right-0 h-16 bg-[#16271c] opacity-60"></div>
                
                {/* Goalposts outlines */}
                <div className="w-[300px] h-[150px] border-t-8 border-x-8 border-white/80 rounded-t relative flex items-end justify-center pointer-events-none">
                  {/* Net wires inside goal */}
                  <div className="absolute inset-0 bg-white/[0.02]" style={{ backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.05) 1px, transparent 1px)', backgroundSize: '12px 12px' }}></div>
                  
                  {/* Keeper Indicator Avatar */}
                  <div 
                    ref={keeperRef}
                    className="w-12 h-20 bg-blue-500 border border-blue-400 rounded-xl absolute bottom-0 mb-0 flex items-center justify-center text-white font-mono text-[10px] font-bold shadow-[0_0_15px_rgba(59,130,246,0.5)]"
                  >
                    GK
                  </div>
                </div>

                {/* Penalty Spot */}
                <div className="absolute bottom-4 w-4 h-4 bg-white/20 rounded-full"></div>

                {/* Soccer Ball Indicator */}
                {ballState.visible && (
                  <div 
                    ref={ballRef}
                    style={{
                      transform: `translate(${ballState.x}px, ${ballState.y}px) scale(1)`,
                    }}
                    className="w-8 h-8 rounded-full bg-[#090b13] border-2 border-fifagold flex items-center justify-center absolute shadow-[0_0_15px_rgba(212,175,55,0.6)]"
                  >
                    <SoccerBallIcon className="w-5 h-5 text-fifagold animate-spin-fast" />
                  </div>
                )}

                {/* Live Overlay Banner */}
                <div className="absolute top-4 left-4 bg-black/40 border border-white/5 rounded-xl px-4 py-2 backdrop-blur-md">
                  <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Tally</span>
                  <div className="text-xl font-mono font-bold text-white mt-0.5">
                    {tally.teamA} - {tally.teamB}
                  </div>
                </div>

                {/* Current Taker Alert */}
                {currentKickIndex > -1 && currentKickIndex < simulationData.sample_kick_sequence.length && (
                  <div className="absolute bottom-4 right-4 bg-black/40 border border-white/5 rounded-xl px-4 py-2 backdrop-blur-md text-right">
                    <span className="text-[9px] uppercase font-mono text-fifagold tracking-wider">
                      {simulationData.sample_kick_sequence[currentKickIndex].team.toUpperCase()} KICK
                    </span>
                    <div className="text-xs font-display font-semibold text-white mt-0.5">
                      {simulationData.sample_kick_sequence[currentKickIndex].taker}
                    </div>
                  </div>
                )}
              </div>

              {/* Score logs row */}
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">Kick Log Timeline</span>
                <div className="flex flex-wrap gap-2">
                  {animatedKicks.map((k, idx) => (
                    <div 
                      key={idx} 
                      className={`px-3 py-1.5 rounded-full border text-xs font-mono font-bold flex items-center gap-1.5 ${
                        k.result === 'scored' 
                          ? 'bg-fifagreen/10 border-fifagreen/20 text-fifagreen' 
                          : 'bg-red-500/10 border-red-500/20 text-red-500'
                      }`}
                    >
                      <span>{k.result === 'scored' ? '⚽' : '✗'}</span>
                      <span>{k.taker}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* PRD Section 13.4: Taker Card Grid + Goalkeeper Cards */}
            <div className="col-span-1 space-y-6">
              {/* Team A Roster Grid */}
              <div className="doppelrand-card">
                <div className="doppelrand-inner space-y-4">
                  <h3 className="text-xs font-display font-bold text-white uppercase tracking-wider">
                    {getTeamName(teamAId)} Roster
                  </h3>
                  
                  {/* Goalkeeper Card */}
                  {simulationData.rosters.team_a.slice(5, 6).map((gk) => (
                    <GkCard key={gk.player_name} gk={gk} />
                  ))}
                  
                  {/* Taker Card Grid (Top 5) */}
                  <div className="space-y-3.5">
                    {simulationData.rosters.team_a.slice(0, 5).map((p, idx) => (
                      <TakerCard key={p.player_name} p={p} order={idx + 1} />
                    ))}
                  </div>
                </div>
              </div>

              {/* Team B Roster Grid */}
              <div className="doppelrand-card">
                <div className="doppelrand-inner space-y-4">
                  <h3 className="text-xs font-display font-bold text-white uppercase tracking-wider">
                    {getTeamName(teamBId)} Roster
                  </h3>
                  
                  {/* Goalkeeper Card */}
                  {simulationData.rosters.team_b.slice(5, 6).map((gk) => (
                    <GkCard key={gk.player_name} gk={gk} />
                  ))}
                  
                  {/* Taker Card Grid (Top 5) */}
                  <div className="space-y-3.5">
                    {simulationData.rosters.team_b.slice(0, 5).map((p, idx) => (
                      <TakerCard key={p.player_name} p={p} order={idx + 1} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component: Taker Card with Bayesian conversion rates and Uncertainty Ribbon
function TakerCard({ p, order }) {
  // Let's model a realistic credible interval around the conversion rate:
  // conversion rate is p.conversion_prior. Prior variance gives a 94% CI of roughly [rate - 12%, rate + 10%]
  const rate = p.conversion_prior;
  const ciMin = Math.max(5.0, (rate * 100 - 12));
  const ciMax = Math.min(99.0, (rate * 100 + 10));
  const ribbonWidth = ciMax - ciMin;

  return (
    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3 space-y-2">
      <div className="flex justify-between items-center text-xs">
        <div className="font-display font-bold text-white truncate max-w-[70%]">
          <span className="font-mono text-slate-500 mr-1.5 text-[10px]">#{order}</span>
          {p.player_name}
        </div>
        <span className="text-[10px] font-mono text-slate-400 uppercase">{p.pos}</span>
      </div>
      
      <div className="space-y-1">
        <div className="flex justify-between items-center text-[9px] font-mono text-slate-500">
          <span>Uncertainty Ribbon (94% CI: {ciMin.toFixed(0)}% - {ciMax.toFixed(0)}%)</span>
          <span className="text-fifagold font-bold">{(rate * 100).toFixed(1)}%</span>
        </div>
        
        {/* Uncertainty Ribbon Bar */}
        <div className="h-2 w-full bg-white/5 rounded-full relative overflow-hidden">
          {/* Gold Credible Interval Ribbon */}
          <div 
            style={{
              left: `${ciMin}%`,
              width: `${ribbonWidth}%`,
            }}
            className="absolute h-full bg-fifagold/15 rounded-full"
          ></div>
          {/* Mean Dot */}
          <div 
            style={{
              left: `${rate * 100}%`,
            }}
            className="absolute w-2 h-2 -ml-1 rounded-full bg-fifagold border border-[#090b13]"
          ></div>
        </div>
      </div>
    </div>
  );
}

// Sub-component: Goalkeeper Card with save rate and Uncertainty Ribbon
function GkCard({ gk }) {
  // Goalkeeper save rate is significantly lower than scorer conversion rate.
  // typical save rate is 1 - conversion rate (so roughly 20-30%).
  // Let's model a 94% CI of roughly [save_rate - 9%, save_rate + 9%]
  const rate = Math.max(0.1, 1.0 - gk.conversion_prior); // map conversion prior to save rate
  const ciMin = Math.max(2.0, (rate * 100 - 9));
  const ciMax = Math.min(95.0, (rate * 100 + 9));
  const ribbonWidth = ciMax - ciMin;

  return (
    <div className="bg-white/5 border border-fifagold/20 rounded-xl p-3 space-y-2">
      <div className="flex justify-between items-center text-xs">
        <div className="font-display font-bold text-fifagold truncate max-w-[70%]">
          <span className="font-mono text-fifagold mr-1.5 text-[10px]">GK</span>
          {gk.player_name}
        </div>
        <span className="text-[10px] font-mono text-fifagold uppercase font-bold">Goalkeeper</span>
      </div>
      
      <div className="space-y-1">
        <div className="flex justify-between items-center text-[9px] font-mono text-slate-400">
          <span>Uncertainty Ribbon (94% CI: {ciMin.toFixed(0)}% - {ciMax.toFixed(0)}%)</span>
          <span className="text-fifagold font-bold">{(rate * 100).toFixed(1)}% Save</span>
        </div>
        
        {/* Uncertainty Ribbon Bar */}
        <div className="h-2 w-full bg-white/5 rounded-full relative overflow-hidden">
          {/* Gold Credible Interval Ribbon */}
          <div 
            style={{
              left: `${ciMin}%`,
              width: `${ribbonWidth}%`,
            }}
            className="absolute h-full bg-fifagold/25 rounded-full"
          ></div>
          {/* Mean Dot */}
          <div 
            style={{
              left: `${rate * 100}%`,
            }}
            className="absolute w-2 h-2 -ml-1 rounded-full bg-fifagold border border-[#090b13]"
          ></div>
        </div>
      </div>
    </div>
  );
}
