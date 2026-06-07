import React, { useState, useEffect, useRef, useCallback } from 'react';
import useSWR from 'swr';
import { WarningIcon, SoccerBallIcon } from '../components/Icons';

// Simple debounce helper
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

export default function XGSandbox() {
  const [shotX, setShotX] = useState(88.0); // center of penalty box
  const [shotY, setShotY] = useState(50.0); // aligned with goal center
  const [situation, setSituation] = useState('open_play');
  const [bodyPart, setBodyPart] = useState('right_foot');
  const [defenders, setDefenders] = useState(1);
  const [pressure, setPressure] = useState(2.0);
  const [heatmapMode, setHeatmapMode] = useState(false); // PRD Section 13.3 Heatmap state

  const pitchRef = useRef(null);
  const isDragging = useRef(false);

  // Debounce the coordinates and numeric inputs to prevent network floods
  const debouncedX = useDebounce(shotX, 300);
  const debouncedY = useDebounce(shotY, 300);
  const debouncedDefenders = useDebounce(defenders, 300);
  const debouncedPressure = useDebounce(pressure, 300);

  const [xgResult, setXgResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  // Trigger POST request to xG endpoint
  useEffect(() => {
    setLoading(true);
    setError(false);
    fetch('/predictions/xg', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shot_x: parseFloat(debouncedX.toFixed(1)),
        shot_y: parseFloat(debouncedY.toFixed(1)),
        situation: situation,
        body_part: bodyPart,
        defenders_in_cone: parseInt(debouncedDefenders),
        defensive_pressure_m: parseFloat(debouncedPressure),
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('xG failed');
        return res.json();
      })
      .then((data) => {
        setXgResult(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [debouncedX, debouncedY, situation, bodyPart, debouncedDefenders, debouncedPressure]);

  // Handle Dragging
  const handlePitchInteraction = useCallback((clientX, clientY) => {
    if (!pitchRef.current) return;
    const rect = pitchRef.current.getBoundingClientRect();
    
    // Calculate relative percentage coordinates (0 - 100)
    // Left-to-right pitch. X goes from 60 (near midfield) to 98 (near goal line).
    // Y goes from 10 to 90.
    const relX = ((clientX - rect.left) / rect.width);
    const relY = ((clientY - rect.top) / rect.height);
    
    // Map to half-pitch: X goes from 50 (midfield) to 100 (goal)
    const newX = Math.max(50.0, Math.min(99.0, 50.0 + relX * 50.0));
    // Y goes from 0 to 100
    const newY = Math.max(5.0, Math.min(95.0, relY * 100.0));

    setShotX(newX);
    setShotY(newY);
  }, []);

  const onMouseDown = (e) => {
    isDragging.current = true;
    handlePitchInteraction(e.clientX, e.clientY);
  };

  const onMouseMove = (e) => {
    if (!isDragging.current) return;
    handlePitchInteraction(e.clientX, e.clientY);
  };

  const onMouseUp = () => {
    isDragging.current = false;
  };

  // Touch handlers for mobile viewport compatibility
  const onTouchStart = (e) => {
    isDragging.current = true;
    if (e.touches[0]) {
      handlePitchInteraction(e.touches[0].clientX, e.touches[0].clientY);
    }
  };

  const onTouchMove = (e) => {
    if (!isDragging.current) return;
    if (e.touches[0]) {
      handlePitchInteraction(e.touches[0].clientX, e.touches[0].clientY);
    }
  };

  const getDangerBadgeColor = (danger) => {
    switch (danger) {
      case 'low': return 'bg-slate-500/10 border-slate-500/20 text-slate-400';
      case 'medium': return 'bg-blue-500/10 border-blue-500/20 text-blue-400';
      case 'high': return 'bg-fifagold/10 border-fifagold/20 text-fifagold';
      case 'extreme': return 'bg-red-500/10 border-red-500/20 text-red-500 animate-pulse';
      default: return 'bg-slate-500/10 border-slate-500/20 text-slate-400';
    }
  };

  return (
    <div className="space-y-12 animate-fade-in py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Expected Goals (xG) Sandbox
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl font-sans">
            Drag the match ball across the attacking third to evaluate spatial metrics and examine SHAP attribution forces in real-time.
          </p>
        </div>

        {/* Heatmap Toggle (PRD Section 13.3) */}
        <div className="flex bg-white/5 p-1 rounded-full border border-white/10 select-none">
          <button
            onClick={() => setHeatmapMode(false)}
            className={`px-5 py-2 rounded-full text-xs font-display font-medium tracking-wide uppercase transition-all ${
              !heatmapMode ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Live Pointer
          </button>
          <button
            onClick={() => setHeatmapMode(true)}
            className={`px-5 py-2 rounded-full text-xs font-display font-medium tracking-wide uppercase transition-all ${
              heatmapMode ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            xG Heatmap Mode
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Pitch Container (2D Attacking Third vector view) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="text-xs font-mono uppercase text-slate-400 tracking-wider">
            Attacking half: Drag ball to update position
          </div>
          
          <div 
            ref={pitchRef}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onMouseUp}
            className="w-full aspect-[1.5/1] bg-[#142618] border-2 border-white/10 rounded-[2rem] relative select-none cursor-crosshair overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.6)]"
          >
            {/* Center Circle Arc */}
            <div className="absolute top-1/2 left-0 w-24 h-48 border-2 border-white/10 -translate-y-1/2 rounded-r-full pointer-events-none"></div>
            
            {/* Halfway Line */}
            <div className="absolute top-0 bottom-0 left-0 w-0 border-r-2 border-white/10 pointer-events-none"></div>

            {/* Penalty Box (Right Side) */}
            <div className="absolute top-[18%] bottom-[18%] right-0 w-[30%] border-y-2 border-l-2 border-white/20 pointer-events-none bg-white/[0.01]"></div>

            {/* 6-Yard Box */}
            <div className="absolute top-[35%] bottom-[35%] right-0 w-[10%] border-y-2 border-l-2 border-white/20 pointer-events-none"></div>

            {/* Penalty Spot */}
            <div className="absolute top-1/2 right-[11.5%] w-2 h-2 bg-white/40 rounded-full -translate-y-1/2 pointer-events-none"></div>

            {/* Goal Posts Outline (Right side) */}
            <div className="absolute top-[36.8%] bottom-[36.8%] right-0 w-2 bg-fifagold/80 border border-fifagold -translate-y-0.5 rounded-l pointer-events-none shadow-[0_0_15px_rgba(212,175,55,0.4)]"></div>

            {/* Heatmap Overlay (PRD Section 13.3) */}
            {heatmapMode && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none animate-fade-in">
                <defs>
                  <radialGradient id="xg-heatmap" cx="100%" cy="50%" r="55%">
                    <stop offset="0%" stopColor="rgba(239, 68, 68, 0.45)" />     {/* red hot goalmouth */}
                    <stop offset="12%" stopColor="rgba(245, 158, 11, 0.35)" />    {/* amber medium 6-yard */}
                    <stop offset="35%" stopColor="rgba(16, 185, 129, 0.15)" />    {/* green cool penalty box */}
                    <stop offset="70%" stopColor="rgba(16, 185, 129, 0.0)" />     {/* zero threat */}
                  </radialGradient>
                </defs>
                <rect width="100%" height="100%" fill="url(#xg-heatmap)" />
              </svg>
            )}

            {/* Defender Triangle Cones from Shot to Goal */}
            {!heatmapMode && shotX < 100 && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
                <polygon 
                  points={`
                    ${((shotX - 50) / 50) * 100}%,${shotY}%
                    100%,36.8%
                    100%,63.2%
                  `}
                  fill="hsl(45, 100%, 50%)"
                />
              </svg>
            )}

            {/* Draggable Ball Indicator */}
            {!heatmapMode && (
              <div 
                style={{
                  left: `${((shotX - 50) / 50) * 100}%`,
                  top: `${shotY}%`,
                }}
                className="absolute w-8 h-8 -ml-4 -mt-4 bg-[#090b13] border-2 border-fifagold rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(212,175,55,0.6)] pointer-events-none transition-all duration-75 active:scale-110 active:bg-fifagold active:text-[#090b13]"
              >
                <SoccerBallIcon className="w-5 h-5 text-fifagold animate-spin-slow" />
              </div>
            )}
          </div>

          <div className="flex justify-between items-center text-xs text-slate-500 font-mono">
            <span>Midfield (50.0, 50.0)</span>
            <span>Attacking Coordinates: ({shotX.toFixed(1)}, {shotY.toFixed(1)})</span>
            <span>Opponent Goal (100.0, 50.0)</span>
          </div>
        </div>

        {/* Input Parameters & Model Output */}
        <div className="space-y-8 col-span-1">
          {/* Inputs Section (Doppelrand Card) */}
          <div className="doppelrand-card">
            <div className="doppelrand-inner space-y-4">
              <h3 className="text-base font-display font-semibold text-white">Shot Context</h3>

              <div className="space-y-3">
                {/* Situation */}
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-mono text-slate-400">Situation</label>
                  <select
                    value={situation}
                    onChange={(e) => setSituation(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
                  >
                    <option value="open_play" className="bg-[#0b0d17]">Open Play</option>
                    <option value="free_kick" className="bg-[#0b0d17]">Direct Free Kick</option>
                    <option value="corner" className="bg-[#0b0d17]">Corner Kick</option>
                    <option value="penalty" className="bg-[#0b0d17]">Penalty Kick</option>
                  </select>
                </div>

                {/* Body Part */}
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-mono text-slate-400">Body Part</label>
                  <select
                    value={bodyPart}
                    onChange={(e) => setBodyPart(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-fifagold/40 w-full font-sans cursor-pointer"
                  >
                    <option value="right_foot" className="bg-[#0b0d17]">Right Foot</option>
                    <option value="left_foot" className="bg-[#0b0d17]">Left Foot</option>
                    <option value="head" className="bg-[#0b0d17]">Header</option>
                  </select>
                </div>

                {/* Defenders in Cone (PRD Section 13.3: 0 to 5) */}
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[10px] uppercase font-mono text-slate-400">
                    <span>Defenders in Goal Cone</span>
                    <span className="text-white font-mono">{defenders}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="5"
                    value={defenders}
                    onChange={(e) => setDefenders(parseInt(e.target.value))}
                    className="w-full accent-fifagold"
                  />
                </div>

                {/* Defensive Pressure (PRD Section 13.3: 0 to 10m) */}
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[10px] uppercase font-mono text-slate-400">
                    <span>Defensive Pressure Radius</span>
                    <span className="text-white font-mono">{pressure.toFixed(1)} m</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="10.0"
                    step="0.5"
                    value={pressure}
                    onChange={(e) => setPressure(parseFloat(e.target.value))}
                    className="w-full accent-fifagold"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Model Output (Doppelrand Card) */}
          <div className="doppelrand-card">
            <div className="doppelrand-inner space-y-6">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <div className="w-6 h-6 rounded-full border-t-2 border-fifagold animate-spin"></div>
                  <span className="text-[10px] font-mono uppercase text-slate-400">Running inference...</span>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center py-6 gap-2 text-center text-red-500">
                  <WarningIcon className="w-6 h-6" />
                  <span className="text-xs">Failed to evaluate xG.</span>
                </div>
              ) : xgResult ? (
                <div className="space-y-6">
                  {/* Big xG Number */}
                  <div className="text-center space-y-1">
                    <span className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">
                      Calibrated Expected Goals
                    </span>
                    <div className="text-5xl font-mono font-extrabold text-white tracking-tight">
                      {xgResult.xg_value.toFixed(2)}
                    </div>
                    <div className="mt-2">
                      <span className={`inline-block border text-[10px] font-mono uppercase px-2.5 py-0.5 rounded-full ${getDangerBadgeColor(xgResult.shot_danger_class)}`}>
                        {xgResult.shot_danger_class} DANGER
                      </span>
                    </div>
                  </div>

                  {/* Derived Spatial details */}
                  <div className="space-y-2.5 border-y border-white/5 py-4">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400 font-sans">Distance to Goal</span>
                      <span className="font-mono text-white font-semibold">
                        {xgResult.derived_metrics.distance_to_goal_m.toFixed(1)} m
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400 font-sans">Visibility Angle</span>
                      <span className="font-mono text-white font-semibold">
                        {xgResult.derived_metrics.angle_to_goal_deg.toFixed(1)}°
                      </span>
                    </div>
                  </div>

                  {/* SHAP Contributions */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-display font-semibold text-white">Local Feature Attributions (SHAP)</h4>
                    
                    <div className="space-y-3">
                      {xgResult.feature_shap_attribution.map((s) => {
                        const isPositive = s.shap_value >= 0;
                        const percentage = Math.min(100, Math.abs(s.shap_value) * 300); // scale for display
                        const displayFeatureName = s.feature
                          .replace('_to_goal_m', '')
                          .replace('_to_goal_deg', '')
                          .replace('_in_cone', '')
                          .replace('_pressure_m', '')
                          .replace('_', ' ');

                        return (
                          <div key={s.feature} className="space-y-1">
                            <div className="flex justify-between items-center text-[10px] uppercase font-mono text-slate-400">
                              <span>{displayFeatureName}</span>
                              <span className={isPositive ? 'text-fifagreen' : 'text-red-400'}>
                                {isPositive ? '+' : ''}{(s.shap_value * 100).toFixed(2)}%
                              </span>
                            </div>
                            
                            {/* Horizontal Bar */}
                            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden relative">
                              <div 
                                style={{
                                  width: `${percentage}%`,
                                  left: isPositive ? '50%' : 'auto',
                                  right: isPositive ? 'auto' : '50%',
                                }}
                                className={`h-full absolute rounded-full ${isPositive ? 'bg-fifagreen' : 'bg-red-500'}`}
                              ></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
