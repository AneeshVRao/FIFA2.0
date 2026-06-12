import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import { TrophyIcon, WarningIcon, StadiumIcon, SoccerBallIcon } from '../components/Icons';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

const matchConnections = {
  'match_73': 'match_89', 'match_74': 'match_89',
  'match_75': 'match_90', 'match_76': 'match_90',
  'match_77': 'match_91', 'match_78': 'match_91',
  'match_79': 'match_92', 'match_80': 'match_92',
  'match_81': 'match_93', 'match_82': 'match_93',
  'match_83': 'match_94', 'match_84': 'match_94',
  'match_85': 'match_95', 'match_86': 'match_95',
  'match_87': 'match_96', 'match_88': 'match_96',
  'match_89': 'match_97', 'match_90': 'match_97',
  'match_91': 'match_98', 'match_92': 'match_98',
  'match_93': 'match_99', 'match_94': 'match_99',
  'match_95': 'match_100', 'match_96': 'match_100',
  'match_97': 'match_101', 'match_98': 'match_101',
  'match_99': 'match_102', 'match_100': 'match_102',
  'match_101': 'match_104', 'match_102': 'match_104',
};

export default function BracketExplorer() {
  const { data: matchesData } = useSWR('/predictions/matches', fetcher);
  const { data: teamsData } = useSWR('/predictions/teams', fetcher);

  const [drilldownTeamId, setDrilldownTeamId] = useState(null);
  const [bracketView, setBracketView] = useState('knockout'); // knockout vs group
  const [expandedGroup, setExpandedGroup] = useState(null); // active expanded group card
  const [groupTeamsData, setGroupTeamsData] = useState([]);
  const [groupLoading, setGroupLoading] = useState(false);
  
  // Time Machine Standings Simulator State
  const [scores, setScores] = useState({});
  const [groupMode, setGroupMode] = useState('probabilities');

  // Zoom and Pan States for Interactive SVG Bracket
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(0.85); // Scale down slightly to fit groups
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const handleMouseDown = (e) => {
    if (e.button !== 0) return; // Only left click
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.closest('button') || e.target.closest('.interactive-node')) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e) => {
    const zoomFactor = 1.05;
    const nextZoom = e.deltaY < 0 ? zoom * zoomFactor : zoom / zoomFactor;
    setZoom(Math.max(0.35, Math.min(2.5, nextZoom)));
  };

  // Coordinates mapping helper
  const getMatchPos = (matchId) => {
    const mNum = parseInt(matchId.replace('match_', ''));
    if (mNum >= 73 && mNum <= 80) { // Left R32
      const idx = mNum - 73;
      return { x: 400, y: 60 + idx * 150 };
    }
    if (mNum >= 81 && mNum <= 88) { // Right R32
      const idx = mNum - 81;
      return { x: 2400, y: 60 + idx * 150 };
    }
    if (mNum >= 89 && mNum <= 92) { // Left R16
      const idx = mNum - 89;
      return { x: 700, y: 135 + idx * 300 };
    }
    if (mNum >= 93 && mNum <= 96) { // Right R16
      const idx = mNum - 93;
      return { x: 2100, y: 135 + idx * 300 };
    }
    if (mNum >= 97 && mNum <= 98) { // Left QF
      const idx = mNum - 97;
      return { x: 1000, y: 285 + idx * 600 };
    }
    if (mNum >= 99 && mNum <= 100) { // Right QF
      const idx = mNum - 99;
      return { x: 1800, y: 285 + idx * 600 };
    }
    if (mNum === 101) { // Left SF
      return { x: 1300, y: 585 };
    }
    if (mNum === 102) { // Right SF
      return { x: 1500, y: 585 };
    }
    if (mNum === 104) { // Final
      return { x: 1400, y: 385 };
    }
    if (mNum === 103) { // Third Place
      return { x: 1400, y: 785 };
    }
    return { x: 0, y: 0 };
  };

  const getGroupPos = (groupCode) => {
    const idx = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].indexOf(groupCode);
    if (idx < 6) { // Left side Groups A-F
      return { x: 100, y: 100 + idx * 200 };
    } else { // Right side Groups G-L
      const rIdx = idx - 6;
      return { x: 2700, y: 100 + rIdx * 200 };
    }
  };

  // Poisson sampler for match score simulation
  const poissonSample = (lambda) => {
    let L = Math.exp(-lambda);
    let k = 0;
    let p = 1.0;
    do {
      k++;
      p *= Math.random();
    } while (p > L);
    return k - 1;
  };

  const handleSimulateNextMatch = async (groupCode) => {
    const groupIndex = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].indexOf(groupCode);
    const startMatchNum = groupIndex * 6 + 1;
    const matchIds = Array.from({ length: 6 }, (_, i) => `match_${startMatchNum + i}`);
    
    // Find the first match without a score
    const firstUnplayed = matchIds.find(mid => {
      const s = scores[mid];
      return !s || s.goals_a === null || s.goals_a === '';
    });
    if (!firstUnplayed) return;
    
    await simulateSingleMatch(firstUnplayed);
  };

  const handleSimulateAllMatches = async (groupCode) => {
    const groupIndex = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].indexOf(groupCode);
    const startMatchNum = groupIndex * 6 + 1;
    const matchIds = Array.from({ length: 6 }, (_, i) => `match_${startMatchNum + i}`);
    
    const nextScores = { ...scores };
    await Promise.all(matchIds.map(async (mid) => {
      try {
        const res = await fetch(`/predictions/match/${mid}`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        const ha = data.expected_goals?.home_xg || 1.25;
        const hb = data.expected_goals?.away_xg || 1.05;
        nextScores[mid] = {
          goals_a: poissonSample(ha),
          goals_b: poissonSample(hb)
        };
      } catch {
        nextScores[mid] = {
          goals_a: Math.floor(Math.random() * 3),
          goals_b: Math.floor(Math.random() * 2)
        };
      }
    }));
    setScores(nextScores);
  };

  const simulateSingleMatch = async (matchId) => {
    try {
      const res = await fetch(`/predictions/match/${matchId}`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const ha = data.expected_goals?.home_xg || 1.25;
      const hb = data.expected_goals?.away_xg || 1.05;
      setScores(prev => ({
        ...prev,
        [matchId]: {
          goals_a: poissonSample(ha),
          goals_b: poissonSample(hb)
        }
      }));
    } catch {
      setScores(prev => ({
        ...prev,
        [matchId]: {
          goals_a: Math.floor(Math.random() * 3),
          goals_b: Math.floor(Math.random() * 2)
        }
      }));
    }
  };

  const handleResetGroupScores = (groupCode) => {
    const groupIndex = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].indexOf(groupCode);
    const startMatchNum = groupIndex * 6 + 1;
    const matchIds = Array.from({ length: 6 }, (_, i) => `match_${startMatchNum + i}`);
    
    setScores(prev => {
      const next = { ...prev };
      matchIds.forEach(mid => {
        delete next[mid];
      });
      return next;
    });
  };

  const getStandings = (groupCode) => {
    if (!teamsData || !matchesData) return [];
    
    // Get the 4 teams in this group
    const groupTeams = teamsData.teams
      .filter((t) => t.group_code === groupCode)
      .map((t) => ({
        id: t.reep_team_id,
        name: t.team_name_canonical,
        P: 0,
        W: 0,
        D: 0,
        L: 0,
        GF: 0,
        GA: 0,
        GD: 0,
        Pts: 0,
      }));
      
    const groupIndex = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'].indexOf(groupCode);
    const startMatchNum = groupIndex * 6 + 1;
    const matchIds = Array.from({ length: 6 }, (_, i) => `match_${startMatchNum + i}`);
    
    // Apply scores
    matchIds.forEach((mid) => {
      const match = matchesData.matches.find((m) => m.match_id === mid);
      if (!match) return;
      
      const score = scores[mid];
      let ga, gb;
      
      if (score && score.goals_a !== null && score.goals_b !== null && score.goals_a !== '' && score.goals_b !== '') {
        ga = parseInt(score.goals_a);
        gb = parseInt(score.goals_b);
      } else if (match.home_goals !== null && match.home_goals !== undefined && match.away_goals !== null && match.away_goals !== undefined) {
        ga = match.home_goals;
        gb = match.away_goals;
      }
      
      if (ga !== undefined && gb !== undefined) {
        const teamA = groupTeams.find((t) => t.id === match.team_a_id);
        const teamB = groupTeams.find((t) => t.id === match.team_b_id);
        
        if (teamA && teamB) {
          teamA.P += 1;
          teamB.P += 1;
          teamA.GF += ga;
          teamA.GA += gb;
          teamA.GD += (ga - gb);
          teamB.GF += gb;
          teamB.GA += ga;
          teamB.GD += (gb - ga);
          
          if (ga > gb) {
            teamA.W += 1;
            teamA.Pts += 3;
            teamB.L += 1;
          } else if (ga < gb) {
            teamB.W += 1;
            teamB.Pts += 3;
            teamA.L += 1;
          } else {
            teamA.D += 1;
            teamA.Pts += 1;
            teamB.D += 1;
            teamB.Pts += 1;
          }
        }
      }
    });
    
    // Sort: Pts -> GD -> GF -> Alphabetical name
    groupTeams.sort((a, b) => {
      if (b.Pts !== a.Pts) return b.Pts - a.Pts;
      if (b.GD !== a.GD) return b.GD - a.GD;
      if (b.GF !== a.GF) return b.GF - a.GF;
      return a.name.localeCompare(b.name);
    });
    
    return groupTeams;
  };

  // Fetch stage probs for the selected team in the sidebar
  const { data: teamProbs, error: probsError } = useSWR(
    drilldownTeamId ? `/teams/${drilldownTeamId}/stage-probs` : null,
    fetcher
  );

  // Load group details in parallel when a group is expanded (PRD & React Best Practices)
  useEffect(() => {
    if (bracketView === 'group' && expandedGroup && teamsData) {
      setGroupLoading(true);
      const groupTeams = teamsData.teams.filter((t) => t.group_code === expandedGroup);
      
      // Fetch details for all 4 teams in parallel to avoid waterfalled requests
      Promise.all(
        groupTeams.map((t) =>
          fetch(`/teams/${t.reep_team_id}/stage-probs`).then((res) => res.json())
        )
      )
        .then((results) => {
          setGroupTeamsData(results);
          setGroupLoading(false);
        })
        .catch(() => {
          setGroupLoading(false);
        });
    } else {
      setGroupTeamsData([]);
    }
  }, [bracketView, expandedGroup, teamsData]);

  const [selectedMatch, setSelectedMatch] = useState(null);
  const loading = !matchesData || !teamsData;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] gap-8">
        <div className="relative flex items-center justify-center">
          <div className="absolute w-32 h-32 rounded-full border border-fifagold/20 border-t-fifagold animate-spin"></div>
          <TrophyIcon className="w-8 h-8 text-fifagold/50 animate-pulse" />
        </div>
        <p className="font-mono text-[10px] text-white/40 uppercase tracking-[0.3em] animate-pulse">
          Parsing 104-Match Tournament Matrix...
        </p>
      </div>
    );
  }

  // Filter knockout matches (match_73 through match_104)
  const knockoutMatches = matchesData.matches.filter(
    (m) => m.stage !== 'group' && m.match_id !== 'match_103'
  );
  const thirdPlaceMatch = matchesData.matches.find((m) => m.match_id === 'match_103');

  // Group matches by stage
  const r32 = knockoutMatches.filter((m) => m.stage === 'r32');
  const r16 = knockoutMatches.filter((m) => m.stage === 'r16');
  const qf = knockoutMatches.filter((m) => m.stage === 'quarterfinal');
  const sf = knockoutMatches.filter((m) => m.stage === 'semifinal');
  const final = knockoutMatches.filter((m) => m.stage === 'final');

  const isRealTeam = (teamId) => teamId && !teamId.startsWith('slot_');

  // Group codes list (Group A to L)
  const groupCodes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'];

  return (
    <div className="space-y-24 animate-fade-in-up py-24">
      {/* Cinematic Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-12 border-b border-white/10 pb-16">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-fifagold/20 bg-fifagold/5 mb-8">
            <TrophyIcon className="w-4 h-4 text-fifagold" /> 
            <span className="text-[10px] text-fifagold uppercase tracking-[0.2em] font-medium">Tournament Matrix</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-display font-extrabold text-white tracking-tighter leading-[1.1]">
            Tournament <span className="text-transparent bg-clip-text bg-gradient-to-r from-fifagold to-white/50">Pathways</span>
          </h1>
          <p className="text-lg text-slate-400 mt-6 font-sans leading-relaxed">
            Navigate the 104-match Monte Carlo tournament graph. Pan, zoom, and explore simulated outcomes.
          </p>
        </div>

        {/* View Toggles */}
        <div className="flex bg-white/5 p-2 rounded-full border border-white/10 select-none shrink-0">
          <button
            onClick={() => setBracketView('knockout')}
            className={`px-8 py-3 rounded-full text-xs font-display font-bold tracking-widest uppercase transition-all duration-300 active:scale-[0.98] ${
              bracketView === 'knockout' ? 'bg-fifagold text-[#050505] shadow-[0_0_20px_rgba(212,175,55,0.4)]' : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            Knockout Map
          </button>
          <button
            onClick={() => setBracketView('group')}
            className={`px-8 py-3 rounded-full text-xs font-display font-bold tracking-widest uppercase transition-all duration-300 active:scale-[0.98] ${
              bracketView === 'group' ? 'bg-fifagold text-[#050505] shadow-[0_0_20px_rgba(212,175,55,0.4)]' : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            Group Stage Simulator
          </button>
        </div>
      </div>

      {/* Main Bracket Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Left Area: Bracket or Group Table Grid */}
        <div className="xl:col-span-3 doppelrand-card">
          <div className="doppelrand-inner h-[800px] relative overflow-hidden p-0">
          {bracketView === 'knockout' ? (
            <div className="relative w-full h-full overflow-hidden select-none bg-[radial-gradient(ellipse_at_center,_rgba(212,175,55,0.03)_0%,_transparent_70%)]">
              {/* Zoom/Pan Controls overlay */}
              <div className="absolute bottom-8 right-8 z-10 flex gap-3">
                <button 
                  onClick={() => setZoom(z => Math.min(2.5, z * 1.15))} 
                  className="w-10 h-10 rounded-full bg-[#050505] border border-white/10 text-white flex items-center justify-center hover:bg-white/10 transition-all font-bold cursor-pointer hover:border-fifagold shadow-xl active:scale-95"
                  title="Zoom In"
                >
                  +
                </button>
                <button 
                  onClick={() => setZoom(z => Math.max(0.35, z / 1.15))} 
                  className="w-10 h-10 rounded-full bg-[#050505] border border-white/10 text-white flex items-center justify-center hover:bg-white/10 transition-all font-bold cursor-pointer hover:border-fifagold shadow-xl active:scale-95"
                  title="Zoom Out"
                >
                  -
                </button>
                <button 
                  onClick={() => { setZoom(0.7); setPan({ x: 100, y: 100 }); }} 
                  className="px-6 h-10 rounded-full bg-[#050505] border border-white/10 text-white flex items-center justify-center hover:bg-white/10 transition-all text-[10px] font-mono cursor-pointer hover:border-fifagold shadow-xl active:scale-95 tracking-widest"
                  title="Reset View"
                >
                  RESET
                </button>
              </div>

              <svg
                width="100%"
                height="100%"
                viewBox="0 0 2800 1300"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onWheel={handleWheel}
                className="cursor-grab active:cursor-grabbing w-full h-full"
              >
                <defs>
                  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="2.5" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                </defs>
                <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                  {/* Edges: Group to R32 */}
                  {(() => {
                    const groupConns = [];
                    matchesData.matches.filter(m => m.stage !== 'group').forEach((m) => {
                      const mNum = parseInt(m.match_id.replace('match_', ''));
                      if (mNum >= 73 && mNum <= 88) {
                        const getGroupForTeam = (teamId) => {
                          if (!teamId || !teamsData) return null;
                          const t = teamsData.teams.find((x) => x.reep_team_id === teamId);
                          return t ? t.group_code : null;
                        };
                        const groupA = getGroupForTeam(m.team_a_id);
                        const groupB = getGroupForTeam(m.team_b_id);
                        
                        if (groupA) groupConns.push({ group: groupA, match: m.match_id, teamId: m.team_a_id });
                        if (groupB) groupConns.push({ group: groupB, match: m.match_id, teamId: m.team_b_id });
                      }
                    });
                    
                    return groupConns.map((conn, idx) => {
                      const gPos = getGroupPos(conn.group);
                      const mPos = getMatchPos(conn.match);
                      const isLeft = gPos.x < 1400;
                      const p1 = isLeft ? { x: gPos.x + 220, y: gPos.y + 65 } : { x: gPos.x, y: gPos.y + 65 };
                      const p2 = isLeft ? { x: mPos.x, y: mPos.y + 37 } : { x: mPos.x + 180, y: mPos.y + 37 };
                      
                      const controlX = (p1.x + p2.x) / 2;
                      const isHighlighted = drilldownTeamId === conn.teamId;
                      const pathD = `M ${p1.x} ${p1.y} C ${controlX} ${p1.y}, ${controlX} ${p2.y}, ${p2.x} ${p2.y}`;
                      
                      return (
                        <path
                          key={`group-conn-${idx}`}
                          d={pathD}
                          fill="none"
                          stroke={isHighlighted ? '#d4af37' : 'rgba(255, 255, 255, 0.05)'}
                          strokeWidth={isHighlighted ? 2.5 : 1}
                          filter={isHighlighted ? 'url(#glow)' : 'none'}
                          className="transition-all duration-300"
                        />
                      );
                    });
                  })()}

                  {/* Edges: Match to Match */}
                  {Object.entries(matchConnections).map(([srcId, tgtId]) => {
                    const srcPos = getMatchPos(srcId);
                    const tgtPos = getMatchPos(tgtId);
                    if (!srcPos || !tgtPos) return null;
                    
                    const isLeft = srcPos.x < 1400;
                    const p1 = isLeft ? { x: srcPos.x + 180, y: srcPos.y + 37 } : { x: srcPos.x, y: srcPos.y + 37 };
                    const p2 = isLeft ? { x: tgtPos.x, y: tgtPos.y + 37 } : { x: tgtPos.x + 180, y: tgtPos.y + 37 };
                    
                    const controlX = (p1.x + p2.x) / 2;
                    const pathD = `M ${p1.x} ${p1.y} C ${controlX} ${p1.y}, ${controlX} ${p2.y}, ${p2.x} ${p2.y}`;
                    
                    const srcMatch = matchesData.matches.find((m) => m.match_id === srcId);
                    const tgtMatch = matchesData.matches.find((m) => m.match_id === tgtId);
                    
                    let isHighlighted = false;
                    let isActive = false;
                    
                    if (srcMatch && tgtMatch && drilldownTeamId) {
                      const isTeamInSrc = srcMatch.team_a_id === drilldownTeamId || srcMatch.team_b_id === drilldownTeamId;
                      const isTeamInTgt = tgtMatch.team_a_id === drilldownTeamId || tgtMatch.team_b_id === drilldownTeamId;
                      if (isTeamInSrc && isTeamInTgt) {
                        isHighlighted = true;
                      }
                    }
                    
                    if (srcMatch && tgtMatch) {
                      const hasScore = srcMatch.home_goals !== null && srcMatch.away_goals !== null;
                      const winnerName = hasScore ? (srcMatch.home_goals > srcMatch.away_goals ? srcMatch.team_a_name : (srcMatch.away_goals > srcMatch.home_goals ? srcMatch.team_b_name : (srcMatch.went_to_penalties ? srcMatch.penalty_winner : null))) : null;
                      if (winnerName && (tgtMatch.team_a_name === winnerName || tgtMatch.team_b_name === winnerName)) {
                        isActive = true;
                      }
                    }
                    
                    return (
                      <path
                        key={`match-conn-${srcId}-${tgtId}`}
                        d={pathD}
                        fill="none"
                        stroke={isHighlighted ? '#d4af37' : (isActive ? 'rgba(212, 175, 55, 0.25)' : 'rgba(255, 255, 255, 0.05)')}
                        strokeWidth={isHighlighted ? 3 : (isActive ? 1.5 : 1)}
                        filter={isHighlighted ? 'url(#glow)' : 'none'}
                        className="transition-all duration-300"
                      />
                    );
                  })}

                  {/* Edges: SF to Third Place */}
                  {['match_101', 'match_102'].map((sfId) => {
                    const sfPos = getMatchPos(sfId);
                    const tpPos = getMatchPos('match_103');
                    if (!sfPos || !tpPos) return null;
                    
                    const isLeft = sfId === 'match_101';
                    const p1 = isLeft ? { x: sfPos.x + 180, y: sfPos.y + 37 } : { x: sfPos.x, y: sfPos.y + 37 };
                    const p2 = isLeft ? { x: tpPos.x, y: tpPos.y + 37 } : { x: tpPos.x + 180, y: tpPos.y + 37 };
                    
                    const controlX = (p1.x + p2.x) / 2;
                    const pathD = `M ${p1.x} ${p1.y} C ${controlX} ${p1.y}, ${controlX} ${p2.y}, ${p2.x} ${p2.y}`;
                    
                    const sfMatch = matchesData.matches.find((m) => m.match_id === sfId);
                    const tpMatch = matchesData.matches.find((m) => m.match_id === 'match_103');
                    
                    let isHighlighted = false;
                    let isActive = false;
                    
                    if (sfMatch && tpMatch && drilldownTeamId) {
                      const isTeamInSrc = sfMatch.team_a_id === drilldownTeamId || sfMatch.team_b_id === drilldownTeamId;
                      const isTeamInTgt = tpMatch.team_a_id === drilldownTeamId || tpMatch.team_b_id === drilldownTeamId;
                      if (isTeamInSrc && isTeamInTgt) {
                        isHighlighted = true;
                      }
                    }
                    
                    if (sfMatch && tpMatch) {
                      const hasScore = sfMatch.home_goals !== null && sfMatch.away_goals !== null;
                      const loserName = hasScore ? (sfMatch.home_goals < sfMatch.away_goals ? sfMatch.team_a_name : (sfMatch.away_goals < sfMatch.home_goals ? sfMatch.team_b_name : (sfMatch.went_to_penalties ? (sfMatch.penalty_winner === sfMatch.team_a_name ? sfMatch.team_b_name : sfMatch.team_a_name) : null))) : null;
                      if (loserName && (tpMatch.team_a_name === loserName || tpMatch.team_b_name === loserName)) {
                        isActive = true;
                      }
                    }
                    
                    return (
                      <path
                        key={`match-conn-loser-${sfId}`}
                        d={pathD}
                        fill="none"
                        stroke={isHighlighted ? '#d4af37' : (isActive ? 'rgba(212, 175, 55, 0.2)' : 'rgba(255, 255, 255, 0.03)')}
                        strokeWidth={isHighlighted ? 2.5 : 1}
                        strokeDasharray="4,4"
                        filter={isHighlighted ? 'url(#glow)' : 'none'}
                        className="transition-all duration-300"
                      />
                    );
                  })}

                  {/* Group Standings Nodes */}
                  {groupCodes.map((code) => {
                    const gPos = getGroupPos(code);
                    const gStandings = getStandings(code);
                    return (
                      <foreignObject key={`group-node-${code}`} x={gPos.x} y={gPos.y} width={220} height={140} className="interactive-node">
                        <div 
                          onClick={() => {
                            setExpandedGroup(code);
                            setBracketView('group');
                          }}
                          className="bg-[#0b0d19]/90 border border-white/5 rounded-2xl p-3 w-[220px] h-[130px] hover:border-fifagold/30 transition-all duration-300 shadow-lg cursor-pointer hover:bg-[#111322] flex flex-col justify-between"
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-display font-extrabold text-white">Group {code}</span>
                            <span className="text-[8px] font-mono text-slate-500 uppercase tracking-wider">STANDINGS</span>
                          </div>
                          <div className="space-y-0.5 mt-1">
                            {gStandings.slice(0, 4).map((t, idx) => (
                              <div key={t.id} className="flex justify-between items-center text-[9px] text-slate-300">
                                <div className="flex items-center gap-1">
                                  <span className="font-mono text-slate-500 w-3">{idx + 1}</span>
                                  <span className="truncate w-24 text-left font-semibold">{t.name}</span>
                                </div>
                                <span className="font-mono font-bold text-fifagold">{t.Pts} pts</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </foreignObject>
                    );
                  })}

                  {/* Knockout Match Nodes */}
                  {matchesData.matches.filter(m => m.stage !== 'group').map((match) => {
                    const mPos = getMatchPos(match.match_id);
                    if (!mPos) return null;
                    
                    const isTeamASelected = drilldownTeamId === match.team_a_id;
                    const isTeamBSelected = drilldownTeamId === match.team_b_id;
                    const isA = isRealTeam(match.team_a_id);
                    const isB = isRealTeam(match.team_b_id);
                    
                    const hasScore = match.home_goals !== null && match.away_goals !== null;
                    const isWinnerA = hasScore && (match.home_goals > match.away_goals || (match.went_to_penalties && match.penalty_winner === match.team_a_name));
                    const isWinnerB = hasScore && (match.away_goals > match.home_goals || (match.went_to_penalties && match.penalty_winner === match.team_b_name));
                    
                    return (
                      <foreignObject key={`match-node-${match.match_id}`} x={mPos.x} y={mPos.y} width={180} height={80} className="interactive-node">
                        <div 
                          onClick={() => isA && isB && setSelectedMatch(match)}
                          className={`bg-[#0b0d19]/90 border border-white/5 rounded-xl p-1.5 w-[180px] hover:border-fifagold/30 transition-all duration-300 shadow-lg select-none flex flex-col justify-between h-[74px] ${
                            isA && isB ? 'cursor-pointer hover:bg-[#111322]' : ''
                          } ${drilldownTeamId && (isTeamASelected || isTeamBSelected) ? 'border-fifagold/40 bg-fifagold/[0.03]' : ''}`}
                        >
                          <div className="text-[7px] font-mono text-slate-500 uppercase flex justify-between items-center px-1">
                            <span>M-{match.match_id.replace('match_', '')} · {match.stage.toUpperCase()}</span>
                            {match.went_to_penalties && (
                              <span className="text-fifagold text-[6px] font-bold px-0.5 rounded bg-fifagold/10">PSO</span>
                            )}
                          </div>
                          <div className="space-y-0.5">
                            <div 
                              onClick={(e) => {
                                if (isA) {
                                  e.stopPropagation();
                                  setDrilldownTeamId(match.team_a_id);
                                }
                              }}
                              className={`px-1.5 py-0.5 rounded text-[10px] flex justify-between items-center ${
                                isA ? `hover:bg-white/5 ${isWinnerA ? 'text-fifagold font-bold font-extrabold' : 'text-slate-300 opacity-80'}` : 'text-slate-500'
                              } ${isTeamASelected ? 'bg-fifagold/20 text-fifagold font-bold' : ''}`}
                            >
                              <span className="truncate w-28 text-left">{match.team_a_name}</span>
                              {hasScore && <span className="font-mono">{match.home_goals}</span>}
                            </div>
                            <div 
                              onClick={(e) => {
                                if (isB) {
                                  e.stopPropagation();
                                  setDrilldownTeamId(match.team_b_id);
                                }
                              }}
                              className={`px-1.5 py-0.5 rounded text-[10px] flex justify-between items-center ${
                                isB ? `hover:bg-white/5 ${isWinnerB ? 'text-fifagold font-bold font-extrabold' : 'text-slate-300 opacity-80'}` : 'text-slate-500'
                              } ${isTeamBSelected ? 'bg-fifagold/20 text-fifagold font-bold' : ''}`}
                            >
                              <span className="truncate w-28 text-left">{match.team_b_name}</span>
                              {hasScore && <span className="font-mono">{match.away_goals}</span>}
                            </div>
                          </div>
                        </div>
                      </foreignObject>
                    );
                  })}
                </g>
              </svg>
            </div>
          ) : (
            /* PRD Section 13.5: Group Standings Distributions (12 Groups A-L) */
            <div className="space-y-6">
              <div className="text-xs font-mono uppercase text-slate-400 tracking-wider">
                Select any group card to expand simulated standings finish distributions
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {groupCodes.map((code) => {
                  const isExpanded = expandedGroup === code;
                  return (
                    <div 
                      key={code} 
                      onClick={() => setExpandedGroup(isExpanded ? null : code)}
                      className={`doppelrand-card cursor-pointer transition-all duration-300 ${
                        isExpanded ? 'md:col-span-3 border-fifagold/30' : 'hover:border-white/20'
                      }`}
                    >
                      <div className="doppelrand-inner p-5 space-y-4">
                        <div className="flex justify-between items-center">
                          <h3 className="text-lg font-display font-bold text-white">Group {code}</h3>
                          <span className="text-[9px] font-mono text-slate-500">
                            {isExpanded ? 'CLICK TO COLLAPSE' : 'CLICK TO EXPAND'}
                          </span>
                        </div>

                        {isExpanded ? (
                          groupLoading ? (
                            <div className="flex items-center justify-center py-8 gap-3">
                              <div className="w-5 h-5 rounded-full border-t-2 border-fifagold animate-spin"></div>
                              <span className="text-[10px] font-mono text-slate-400">Loading standings...</span>
                            </div>
                          ) : (
                            <div className="space-y-4 pt-2 border-t border-white/5 animate-fade-in">
                              {/* Tab toggle between Probabilities and Time Machine */}
                              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-2">
                                <div className="flex bg-white/5 p-0.5 rounded-full border border-white/10 select-none">
                                  <button
                                    onClick={(e) => { e.stopPropagation(); setGroupMode('probabilities'); }}
                                    className={`px-4 py-1.5 rounded-full text-[10px] font-display font-medium uppercase transition-all cursor-pointer ${
                                      groupMode === 'probabilities' ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
                                    }`}
                                  >
                                    Simulated Probs
                                  </button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); setGroupMode('timemachine'); }}
                                    className={`px-4 py-1.5 rounded-full text-[10px] font-display font-medium uppercase transition-all cursor-pointer ${
                                      groupMode === 'timemachine' ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
                                    }`}
                                  >
                                    Time Machine Simulator
                                  </button>
                                </div>

                                {groupMode === 'timemachine' && (
                                  <div className="flex gap-2">
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleSimulateNextMatch(code); }}
                                      className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-[10px] font-display font-semibold hover:border-fifagold/40 hover:text-white text-slate-300 transition-all uppercase cursor-pointer"
                                    >
                                      Simulate Next
                                    </button>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleSimulateAllMatches(code); }}
                                      className="px-3 py-1.5 rounded-full bg-fifagold/10 border border-fifagold/30 hover:bg-fifagold/20 text-fifagold text-[10px] font-display font-bold transition-all uppercase cursor-pointer"
                                    >
                                      Simulate All
                                    </button>
                                    <button
                                      onClick={(e) => { e.stopPropagation(); handleResetGroupScores(code); }}
                                      className="px-3 py-1.5 rounded-full bg-red-950/20 border border-red-500/20 hover:bg-red-950/40 text-red-400 text-[10px] font-display font-semibold transition-all uppercase cursor-pointer"
                                    >
                                      Reset
                                    </button>
                                  </div>
                                )}
                              </div>

                              {groupMode === 'probabilities' ? (
                                <div className="space-y-4 pt-2">
                                  {/* Stacked stand column headers */}
                                  <div className="grid grid-cols-12 text-[9px] font-mono uppercase text-slate-500 text-center">
                                    <div className="col-span-4 text-left pl-2">Squad</div>
                                    <div className="col-span-2 text-fifagreen">1st</div>
                                    <div className="col-span-2 text-blue-400">2nd</div>
                                    <div className="col-span-2 text-fifagold">3rd Adv</div>
                                    <div className="col-span-2 text-red-500">Eliminated</div>
                                  </div>

                                  {groupTeamsData.map((team) => (
                                    <div key={team.reep_team_id} className="grid grid-cols-12 items-center text-xs text-center py-2 border-b border-white/5">
                                      <div 
                                        className="col-span-4 text-left font-display font-bold text-white pl-2 cursor-pointer hover:text-fifagold"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setDrilldownTeamId(team.reep_team_id);
                                        }}
                                      >
                                        {team.team_name}
                                      </div>
                                      <div className="col-span-2 font-mono">{(team.group_finish_distribution.first * 100).toFixed(1)}%</div>
                                      <div className="col-span-2 font-mono">{(team.group_finish_distribution.second * 100).toFixed(1)}%</div>
                                      <div className="col-span-2 font-mono">{(team.group_finish_distribution.third_advance * 100).toFixed(1)}%</div>
                                      <div className="col-span-2 font-mono">{(team.group_finish_distribution.eliminated * 100).toFixed(1)}%</div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                /* TIME MACHINE STANDINGS SIMULATOR */
                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2 border-t border-white/5">
                                  {/* Standings Table */}
                                  <div className="lg:col-span-6 space-y-3">
                                    <div className="flex justify-between items-center text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                                      <span>Recalculated Standings</span>
                                      <span>PTS &rarr; GD &rarr; GF</span>
                                    </div>
                                    
                                    <div className="overflow-x-auto border border-white/5 rounded-2xl bg-[#070911]/50 p-2">
                                      <table className="w-full text-xs text-left border-collapse">
                                        <thead>
                                          <tr className="border-b border-white/5 text-[9px] uppercase font-mono text-slate-500 tracking-wider">
                                            <th className="py-2 px-2.5 w-6 text-center">#</th>
                                            <th className="py-2 px-2">Squad</th>
                                            <th className="py-2 px-1 text-center">P</th>
                                            <th className="py-2 px-1 text-center">W</th>
                                            <th className="py-2 px-1 text-center">D</th>
                                            <th className="py-2 px-1 text-center">L</th>
                                            <th className="py-2 px-1 text-center">GD</th>
                                            <th className="py-2 px-2 text-right">Pts</th>
                                          </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                          {getStandings(code).map((team, idx) => (
                                            <tr key={team.id} className="hover:bg-white/[0.01]">
                                              <td className="py-2 px-2.5 text-center font-mono font-bold text-slate-500">{idx + 1}</td>
                                              <td className="py-2 px-2 font-display font-semibold text-white truncate max-w-[120px]">{team.name}</td>
                                              <td className="py-2 px-1 text-center font-mono text-slate-400">{team.P}</td>
                                              <td className="py-2 px-1 text-center font-mono text-slate-400">{team.W}</td>
                                              <td className="py-2 px-1 text-center font-mono text-slate-400">{team.D}</td>
                                              <td className="py-2 px-1 text-center font-mono text-slate-400">{team.L}</td>
                                              <td className={`py-2 px-1 text-center font-mono font-semibold ${team.GD > 0 ? 'text-fifagreen' : (team.GD < 0 ? 'text-red-400' : 'text-slate-500')}`}>
                                                {team.GD > 0 ? `+${team.GD}` : team.GD}
                                              </td>
                                              <td className="py-2 px-2 text-right font-mono font-bold text-fifagold">{team.Pts}</td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </div>

                                  {/* Fixtures List */}
                                  <div className="lg:col-span-6 space-y-3">
                                    <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                                      Group Fixtures
                                    </div>
                                    <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
                                      {matchesData.matches.filter(m => m.group_code === code).map((match) => {
                                        const mid = match.match_id;
                                        const score = scores[mid] || { goals_a: '', goals_b: '' };
                                        return (
                                          <div key={mid} className="bg-[#090b13] border border-white/5 rounded-xl p-2.5 flex justify-between items-center hover:border-white/10 transition-all">
                                            <span className="text-[9px] font-mono text-slate-500 w-12 text-left">
                                              M-{mid.replace('match_', '')}
                                            </span>
                                            
                                            <div className="flex items-center gap-2 flex-1 justify-center px-2">
                                              <span className="text-[11px] font-display font-semibold text-white truncate text-right w-16">
                                                {match.team_a_name}
                                              </span>
                                              
                                              <div className="flex items-center gap-1 select-none pointer-events-auto">
                                                <input
                                                  type="number"
                                                  min="0"
                                                  max="15"
                                                  value={score.goals_a === null ? '' : score.goals_a}
                                                  onClick={(e) => e.stopPropagation()}
                                                  onChange={(e) => {
                                                    const val = e.target.value;
                                                    setScores(prev => ({
                                                      ...prev,
                                                      [mid]: {
                                                        ...prev[mid],
                                                        goals_a: val === '' ? '' : parseInt(val)
                                                      }
                                                    }));
                                                  }}
                                                  className="w-8 h-6 rounded bg-white/5 border border-white/10 text-center font-mono font-bold text-xs text-white focus:outline-none focus:border-fifagold/40 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                                                />
                                                <span className="text-slate-600 text-[10px]">-</span>
                                                <input
                                                  type="number"
                                                  min="0"
                                                  max="15"
                                                  value={score.goals_b === null ? '' : score.goals_b}
                                                  onClick={(e) => e.stopPropagation()}
                                                  onChange={(e) => {
                                                    const val = e.target.value;
                                                    setScores(prev => ({
                                                      ...prev,
                                                      [mid]: {
                                                        ...prev[mid],
                                                        goals_b: val === '' ? '' : parseInt(val)
                                                      }
                                                    }));
                                                  }}
                                                  className="w-8 h-6 rounded bg-white/5 border border-white/10 text-center font-mono font-bold text-xs text-white focus:outline-none focus:border-fifagold/40 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                                                />
                                              </div>

                                              <span className="text-[11px] font-display font-semibold text-white truncate text-left w-16">
                                                {match.team_b_name}
                                              </span>
                                            </div>

                                            <button
                                              onClick={(e) => { e.stopPropagation(); simulateSingleMatch(mid); }}
                                              className="p-1 rounded bg-white/5 border border-white/10 hover:border-fifagold/40 hover:text-fifagold transition-all cursor-pointer text-slate-400 select-none pointer-events-auto"
                                              title="Simulate Match"
                                            >
                                              <SoccerBallIcon className="w-3 h-3" />
                                            </button>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        ) : (
                          /* Collasped preview of teams list */
                          <div className="flex flex-wrap gap-1.5">
                            {teamsData.teams
                              .filter((t) => t.group_code === code)
                              .map((t) => (
                                <span key={t.reep_team_id} className="text-[10px] font-display font-semibold px-2 py-0.5 rounded bg-white/5 text-slate-300">
                                  {t.team_name_canonical}
                                </span>
                              ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              </div>
            )}
            </div>
          </div>

        {/* Right Area: Team Drilldown sidebar info */}
        <div className="col-span-1">
          {drilldownTeamId ? (
            <div className="doppelrand-card sticky top-24">
              <div className="doppelrand-inner space-y-6">
                {teamProbs ? (
                  <div className="space-y-6 animate-fade-in">
                    <div>
                      <div className="flex items-center gap-1.5 text-fifagold text-xs uppercase tracking-widest font-mono mb-2">
                        <TrophyIcon className="w-4 h-4" /> Team Projections
                      </div>
                      <h2 className="text-2xl font-display font-extrabold text-white">
                        {teamProbs.team_name}
                      </h2>
                    </div>

                    {/* Stage Probs progress indicators */}
                    <div className="space-y-3 border-y border-white/5 py-4">
                      <h4 className="text-[10px] font-mono uppercase text-slate-400 tracking-wider mb-2">Knockout Stage Progression</h4>
                      
                      <StageProbRow label="Champion" prob={teamProbs.stage_probabilities.champion} color="bg-fifagold" />
                      <StageProbRow label="Reach Final" prob={teamProbs.stage_probabilities.final} color="bg-slate-300" />
                      <StageProbRow label="Reach SF" prob={teamProbs.stage_probabilities.semifinal} color="bg-blue-400" />
                      <StageProbRow label="Reach QF" prob={teamProbs.stage_probabilities.quarterfinal} color="bg-slate-500" />
                      <StageProbRow label="Reach R16" prob={teamProbs.stage_probabilities.r16} color="bg-slate-600" />
                      <StageProbRow label="Reach R32" prob={teamProbs.stage_probabilities.r32} color="bg-slate-700" />
                      <StageProbRow label="Group Advance" prob={teamProbs.stage_probabilities.group_advance} color="bg-fifagreen" />
                    </div>

                    {/* Group Finish distributions */}
                    <div className="space-y-3">
                      <h4 className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Group Finish Standings</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <StandingsCard label="1st Place" prob={teamProbs.group_finish_distribution.first} />
                        <StandingsCard label="2nd Place" prob={teamProbs.group_finish_distribution.second} />
                        <StandingsCard label="3rd Advance" prob={teamProbs.group_finish_distribution.third_advance} />
                        <StandingsCard label="Eliminated" prob={teamProbs.group_finish_distribution.eliminated} red />
                      </div>
                    </div>
                  </div>
                ) : probsError ? (
                  <div className="flex flex-col items-center justify-center py-6 gap-2 text-center text-red-500">
                    <WarningIcon className="w-6 h-6 animate-pulse" />
                    <span className="text-xs">Failed to load team data.</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <div className="w-6 h-6 rounded-full border-t-2 border-fifagold animate-spin"></div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 animate-pulse">Loading probabilities...</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="doppelrand-card h-64 flex items-center justify-center text-center p-6">
              <div className="space-y-2">
                <TrophyIcon className="w-8 h-8 text-slate-600 mx-auto" />
                <h3 className="text-sm font-display font-semibold text-slate-400 font-bold">No Team Selected</h3>
                <p className="text-xs text-slate-500">Select any highlighted team in the bracket tree to inspect projections.</p>
              </div>
            </div>
          )}
        </div>
        </div>
      
      {/* Click-to-Drill Side Drawer Modal Overlay */}
      {selectedMatch && (
        <MatchPredictionDrawer 
          match={selectedMatch} 
          onClose={() => setSelectedMatch(null)} 
        />
      )}
    </div>
  );
}

// Sub-component: Individual bracket node
function BracketNode({ match, onSelectTeam, selectedTeamId, isRealTeam, onSelectMatch }) {
  const isTeamASelected = selectedTeamId === match.team_a_id;
  const isTeamBSelected = selectedTeamId === match.team_b_id;
  const isA = isRealTeam(match.team_a_id);
  const isB = isRealTeam(match.team_b_id);
  
  const hasScore = match.home_goals !== null && match.away_goals !== null;
  const isWinnerA = hasScore && (match.home_goals > match.away_goals || (match.went_to_penalties && match.penalty_winner === match.team_a_name));
  const isWinnerB = hasScore && (match.away_goals > match.home_goals || (match.went_to_penalties && match.penalty_winner === match.team_b_name));

  return (
    <div 
      onClick={() => isA && isB && onSelectMatch && onSelectMatch(match)}
      className={`bg-[#090b13] border border-white/5 rounded-2xl p-2 w-[180px] hover:border-fifagold/30 transition-all duration-300 shadow-lg ${
        isA && isB ? 'cursor-pointer hover:bg-white/[0.02]' : ''
      }`}
    >
      <div className="text-[8px] font-mono text-slate-500 uppercase flex justify-between items-center mb-1 px-1">
        <span>Match {match.match_id.replace('match_', '')}</span>
        {isA && isB && (
          <div className="flex items-center gap-1">
            {match.went_to_penalties && (
              <span className="text-fifagold text-[7px] font-extrabold font-mono bg-fifagold/10 border border-fifagold/20 px-1 rounded">PSO</span>
            )}
            <span className="text-fifagold text-[7px] font-bold font-mono">ANALYZE</span>
          </div>
        )}
      </div>

      <div className="space-y-1">
        {/* Team A */}
        <div
          onClick={(e) => {
            if (isA) {
              e.stopPropagation();
              onSelectTeam(match.team_a_id);
            }
          }}
          className={`px-2 py-1.5 rounded-lg text-xs font-display flex justify-between items-center transition-all ${
            isA 
              ? `cursor-pointer hover:bg-white/5 ${isWinnerA ? 'text-fifagold font-bold' : 'text-slate-200 opacity-70'}` 
              : 'text-slate-500'
          } ${isTeamASelected ? 'bg-fifagold/10 text-fifagold border border-fifagold/20' : 'border border-transparent'}`}
        >
          <span className="truncate">{match.team_a_name}</span>
          {hasScore && (
            <span className={`font-mono text-xs ${isWinnerA ? 'text-fifagold font-extrabold' : 'text-slate-400'}`}>
              {match.home_goals}
            </span>
          )}
        </div>

        {/* Team B */}
        <div
          onClick={(e) => {
            if (isB) {
              e.stopPropagation();
              onSelectTeam(match.team_b_id);
            }
          }}
          className={`px-2 py-1.5 rounded-lg text-xs font-display flex justify-between items-center transition-all ${
            isB 
              ? `cursor-pointer hover:bg-white/5 ${isWinnerB ? 'text-fifagold font-bold' : 'text-slate-200 opacity-70'}` 
              : 'text-slate-500'
          } ${isTeamBSelected ? 'bg-fifagold/10 text-fifagold border border-fifagold/20' : 'border border-transparent'}`}
        >
          <span className="truncate">{match.team_b_name}</span>
          {hasScore && (
            <span className={`font-mono text-xs ${isWinnerB ? 'text-fifagold font-extrabold' : 'text-slate-400'}`}>
              {match.away_goals}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// Click-to-Drill: Drawer displaying prediction metrics for selected bracket match
function MatchPredictionDrawer({ match, onClose }) {
  const { data: predData, error } = useSWR(
    match ? `/predictions/match/${match.match_id}` : null,
    fetcher
  );

  if (!match) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-xs transition-all duration-300 animate-fade-in pointer-events-auto">
      {/* Click outside to close */}
      <div className="absolute inset-0 cursor-pointer" onClick={onClose}></div>
      
      {/* Drawer Panel Container */}
      <div className="w-full max-w-md h-full bg-[#090b13] border-l border-white/10 relative z-10 flex flex-col p-6 shadow-2xl animate-fade-in-up figma-glass overflow-hidden">
        {/* Glow ambient orbs */}
        <div className="absolute w-[200px] h-[200px] bg-fifagold/5 rounded-full blur-[40px] top-[-50px] right-[-50px] pointer-events-none"></div>

        {/* Header */}
        <div className="flex justify-between items-center border-b border-white/5 pb-4 mb-6 relative z-10">
          <div>
            <h3 className="text-lg font-display font-extrabold text-white uppercase tracking-wider">Match Projections</h3>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest mt-0.5 block">
              Match {match.match_id.replace('match_', '')} · {match.stage}
            </span>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/5 text-slate-400 hover:text-white transition-all cursor-pointer"
          >
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Prediction Data Panel */}
        {!predData && !error ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 rounded-full border-t-2 border-fifagold animate-spin"></div>
            <span className="text-[10px] font-mono uppercase text-slate-400 animate-pulse">Running Dixon-Coles solver...</span>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-2 text-red-500">
            <span className="text-xs">Failed to load match prediction.</span>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-6 pr-1 relative z-10 scrollbar-none">
            {/* Matchup Header */}
            <div className="flex justify-between items-center text-center bg-white/[0.02] border border-white/5 rounded-2xl p-4">
              <div className="flex-1">
                <div className="text-xs text-slate-200 font-display font-extrabold uppercase">{predData.home_team.name}</div>
                <div className="text-[9px] font-mono text-slate-500 uppercase mt-0.5">Home</div>
              </div>
              <div className="text-slate-600 text-xs font-mono px-3">VS</div>
              <div className="flex-1">
                <div className="text-xs text-slate-200 font-display font-extrabold uppercase">{predData.away_team.name}</div>
                <div className="text-[9px] font-mono text-slate-500 uppercase mt-0.5">Away</div>
              </div>
            </div>

            {/* Outcome Bars */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Outcome Probabilities</h4>
              <div className="space-y-2.5">
                <OutcomeProgressBar label={`${predData.home_team.name} Win`} prob={predData.probabilities.home_win} color="bg-fifagreen" />
                <OutcomeProgressBar label="Draw" prob={predData.probabilities.draw} color="bg-slate-500" />
                <OutcomeProgressBar label={`${predData.away_team.name} Win`} prob={predData.probabilities.away_win} color="bg-fifagold" />
              </div>
            </div>

            {/* Expected Goals */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Expected Goals (DC &lambda;)</h4>
              <div className="grid grid-cols-2 gap-4 bg-white/[0.02] border border-white/5 rounded-2xl p-4 text-center">
                <div>
                  <div className="text-2xl font-mono font-bold text-white">{predData.expected_goals.home_xg.toFixed(2)}</div>
                  <div className="text-[9px] font-mono text-slate-500 uppercase mt-1">Home Expected Goals</div>
                </div>
                <div>
                  <div className="text-2xl font-mono font-bold text-white">{predData.expected_goals.away_xg.toFixed(2)}</div>
                  <div className="text-[9px] font-mono text-slate-500 uppercase mt-1">Away Expected Goals</div>
                </div>
              </div>
            </div>

            {/* Top scorelines */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Top Scoreline Probabilities</h4>
              <div className="space-y-2">
                {predData.top_scorelines.map((s, idx) => (
                  <div key={idx} className="flex justify-between items-center bg-white/[0.01] border border-white/5 rounded-xl px-4 py-2 text-xs">
                    <span className="font-mono text-slate-400">{idx + 1}. Scoreline: <strong className="text-white font-bold">{s.score}</strong></span>
                    <span className="font-mono text-fifagold font-bold">{(s.probability * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Telemetry info */}
            <div className="space-y-3">
              <h4 className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Venue & Travel Parameters</h4>
              <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 space-y-3 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Venue Stadium</span>
                  <span className="font-display text-white font-semibold">{match.venue_name}</span>
                </div>
                <div className="flex justify-between items-center border-t border-white/5 pt-2">
                  <span className="text-slate-400">Altitude</span>
                  <span className="font-mono text-white font-bold">{match.altitude_m} m</span>
                </div>
                {predData.influence_features && (
                  <>
                    <div className="flex justify-between items-center border-t border-white/5 pt-2">
                      <span className="text-slate-400">Travel Distance</span>
                      <span className="font-mono text-white font-bold">{Math.round(predData.influence_features.travel_distance_km || 0)} km</span>
                    </div>
                    <div className="flex justify-between items-center border-t border-white/5 pt-2">
                      <span className="text-slate-400">Rest Days Differential</span>
                      <span className="font-mono text-white font-bold">{predData.influence_features.rest_days_diff} days</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function OutcomeProgressBar({ label, prob, color }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-xs font-display">
        <span className="text-slate-300 font-semibold">{label}</span>
        <span className="text-white font-bold font-mono">{(prob * 100).toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
        <div style={{ width: `${prob * 100}%` }} className={`h-full rounded-full ${color}`}></div>
      </div>
    </div>
  );
}

// Sub-component: Progress Bar stage probabilities
function StageProbRow({ label, prob, color }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
        <span>{label}</span>
        <span className="text-white font-bold">{(prob * 100).toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
        <div style={{ width: `${prob * 100}%` }} className={`h-full rounded-full ${color}`}></div>
      </div>
    </div>
  );
}

// Sub-component: Standing cards
function StandingsCard({ label, prob, red }) {
  return (
    <div className="bg-white/[0.02] border border-white/5 rounded-xl p-2.5 text-center">
      <div className="text-[9px] uppercase font-mono text-slate-400">{label}</div>
      <div className={`text-sm font-mono font-bold mt-1 ${red ? 'text-red-400' : 'text-fifagold'}`}>
        {(prob * 100).toFixed(1)}%
      </div>
    </div>
  );
}
