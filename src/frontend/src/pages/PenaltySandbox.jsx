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
    // Goal width is roughly [-100, 100], height is [-120, 0] relative to center
    let targetX = 0;
    let targetY = -70; // middle height
    let keeperX = 0;

    if (kick.result === 'scored') {
      // corner targets
      targetX = Math.random() > 0.5 ? -80 : 80;
      targetY = Math.random() > 0.5 ? -100 : -40;
      keeperX = targetX > 0 ? -40 : 40; // dive away
    } else if (kick.result === 'saved') {
      // save targets (ball and keeper collide)
      targetX = Math.random() > 0.5 ? -40 : 40;
      targetY = -60;
      keeperX = targetX; // dive to ball
    } else {
      // missed targets (wide/over)
      targetX = Math.random() > 0.5 ? -130 : 130;
      targetY = Math.random() > 0.5 ? -140 : -20;
      keeperX = targetX > 0 ? 50 : -50;
    }

    // Set up Anime.js timeline for shootout sequence
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
      // update tally
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
      
      // reset keeper
      anime({
        targets: keeperRef.current,
        translateX: 0,
        duration: 300,
        easing: 'easeOutQuad',
      });

      // wait 1.2s before next kick
      setTimeout(() => {
        animateNextKick(sequence, index + 1, nextTally, updatedKicks);
      }, 1200);
    });
  };

  const getTeamName = (tid) => {
    return teamsData?.teams.find((t) => t.reep_team_id === tid)?.team_name_canonical || 'Select Team';
  };

  return (
    <div className="space-y-12 animate-fade-in py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Bayesian Shootout Sandbox
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl">
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
          className="doppelrand-card bg-fifagold hover:border-white/20 active-press select-none w-full border-none p-0 cursor-pointer disabled:opacity-50"
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Visual Goalpost Animation View */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex justify-between items-center bg-white/[0.02] border border-white/5 rounded-2xl p-4">
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400">Shootout Telemetry</span>
                <h3 className="text-sm font-display font-bold text-white mt-1">
                  {getTeamName(teamAId)} vs {getTeamName(teamBId)}
                </h3>
              </div>
              <div className="text-right">
                <span className="text-[10px] uppercase font-mono text-fifagold">Win Probabilities</span>
                <div className="text-sm font-mono font-bold text-white mt-1">
                  {(simulationData.win_probabilities.team_a * 100).toFixed(1)}% vs {(simulationData.win_probabilities.team_b * 100).toFixed(1)}%
                </div>
              </div>
            </div>

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

          {/* Rosters and Bayesian Priors display */}
          <div className="space-y-8 col-span-1">
            {/* Team A Roster priors */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner space-y-4">
                <h3 className="text-sm font-display font-semibold text-white">
                  {getTeamName(teamAId)} Bayesian Priors
                </h3>
                
                <div className="space-y-3">
                  {simulationData.rosters.team_a.map((p) => (
                    <div key={p.player_name} className="space-y-1">
                      <div className="flex justify-between items-center text-[10px] uppercase font-mono text-slate-400">
                        <span>{p.player_name} ({p.pos})</span>
                        <span className="text-fifagold">{(p.conversion_prior * 100).toFixed(1)}%</span>
                      </div>
                      
                      {/* Progress bar */}
                      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                        <div 
                          style={{ width: `${p.conversion_prior * 100}%` }}
                          className="h-full bg-fifagold rounded-full"
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Team B Roster priors */}
            <div className="doppelrand-card">
              <div className="doppelrand-inner space-y-4">
                <h3 className="text-sm font-display font-semibold text-white">
                  {getTeamName(teamBId)} Bayesian Priors
                </h3>
                
                <div className="space-y-3">
                  {simulationData.rosters.team_b.map((p) => (
                    <div key={p.player_name} className="space-y-1">
                      <div className="flex justify-between items-center text-[10px] uppercase font-mono text-slate-400">
                        <span>{p.player_name} ({p.pos})</span>
                        <span className="text-fifagold">{(p.conversion_prior * 100).toFixed(1)}%</span>
                      </div>
                      
                      {/* Progress bar */}
                      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                        <div 
                          style={{ width: `${p.conversion_prior * 100}%` }}
                          className="h-full bg-fifagold rounded-full"
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
