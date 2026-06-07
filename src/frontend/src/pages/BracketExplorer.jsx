import React, { useState, useEffect } from 'react';
import useSWR from 'swr';
import { TrophyIcon, WarningIcon, StadiumIcon } from '../components/Icons';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

export default function BracketExplorer() {
  const { data: matchesData } = useSWR('/predictions/matches', fetcher);
  const { data: teamsData } = useSWR('/predictions/teams', fetcher);

  const [drilldownTeamId, setDrilldownTeamId] = useState(null);
  const [bracketView, setBracketView] = useState('knockout'); // knockout vs group
  const [expandedGroup, setExpandedGroup] = useState(null); // active expanded group card
  const [groupTeamsData, setGroupTeamsData] = useState([]);
  const [groupLoading, setGroupLoading] = useState(false);

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

  const loading = !matchesData || !teamsData;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 rounded-full border-t-2 border-fifagold animate-spin"></div>
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest animate-pulse">
          Parsing bracket projections...
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
    <div className="space-y-12 animate-fade-in py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Tournament Bracket Explorer
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl font-sans">
            Explore simulated knockout brackets. Select any team to inspect their stage-by-stage progression probabilities.
          </p>
        </div>

        {/* View Toggle */}
        <div className="flex bg-white/5 p-1 rounded-full border border-white/10 select-none">
          <button
            onClick={() => setBracketView('knockout')}
            className={`px-5 py-2 rounded-full text-xs font-display font-medium tracking-wide uppercase transition-all ${
              bracketView === 'knockout' ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Knockout Bracket
          </button>
          <button
            onClick={() => setBracketView('group')}
            className={`px-5 py-2 rounded-full text-xs font-display font-medium tracking-wide uppercase transition-all ${
              bracketView === 'group' ? 'bg-fifagold text-[#050505] font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Group Table Distributions
          </button>
        </div>
      </div>

      {/* Main Bracket Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Left Area: Bracket or Group Table Grid */}
        <div className="xl:col-span-3">
          {bracketView === 'knockout' ? (
            <div className="overflow-x-auto pb-6 -mx-4 px-4 xl:mx-0 xl:px-0">
              <div className="flex gap-8 min-w-[1000px] select-none h-[720px]">
                {/* 1. Round of 32 */}
                <div className="flex-1 flex flex-col justify-around h-full">
                  <div className="text-[10px] uppercase font-mono text-slate-500 text-center tracking-widest mb-2">Round of 32</div>
                  {r32.map((m) => (
                    <BracketNode key={m.match_id} match={m} onSelectTeam={setDrilldownTeamId} selectedTeamId={drilldownTeamId} isRealTeam={isRealTeam} />
                  ))}
                </div>

                {/* 2. Round of 16 */}
                <div className="flex-1 flex flex-col justify-around h-full">
                  <div className="text-[10px] uppercase font-mono text-slate-500 text-center tracking-widest mb-2">Round of 16</div>
                  {r16.map((m) => (
                    <BracketNode key={m.match_id} match={m} onSelectTeam={setDrilldownTeamId} selectedTeamId={drilldownTeamId} isRealTeam={isRealTeam} />
                  ))}
                </div>

                {/* 3. Quarterfinals */}
                <div className="flex-1 flex flex-col justify-around h-full">
                  <div className="text-[10px] uppercase font-mono text-slate-500 text-center tracking-widest mb-2">Quarterfinals</div>
                  {qf.map((m) => (
                    <BracketNode key={m.match_id} match={m} onSelectTeam={setDrilldownTeamId} selectedTeamId={drilldownTeamId} isRealTeam={isRealTeam} />
                  ))}
                </div>

                {/* 4. Semifinals */}
                <div className="flex-1 flex flex-col justify-around h-full">
                  <div className="text-[10px] uppercase font-mono text-slate-500 text-center tracking-widest mb-2">Semifinals</div>
                  {sf.map((m) => (
                    <BracketNode key={m.match_id} match={m} onSelectTeam={setDrilldownTeamId} selectedTeamId={drilldownTeamId} isRealTeam={isRealTeam} />
                  ))}
                </div>

                {/* 5. Final */}
                <div className="flex-1 flex flex-col justify-center gap-16 h-full">
                  <div>
                    <div className="text-[10px] uppercase font-mono text-slate-500 text-center tracking-widest mb-2">Final</div>
                    {final.map((m) => (
                      <BracketNode key={m.match_id} match={m} onSelectTeam={setDrilldownTeamId} selectedTeamId={drilldownTeamId} isRealTeam={isRealTeam} />
                    ))}
                  </div>
                  
                  {thirdPlaceMatch && (
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-500 text-center tracking-widest mb-2">Third Place</div>
                      <BracketNode match={thirdPlaceMatch} onSelectTeam={setDrilldownTeamId} selectedTeamId={drilldownTeamId} isRealTeam={isRealTeam} />
                    </div>
                  )}
                </div>
              </div>
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
    </div>
  );
}

// Sub-component: Individual bracket node
function BracketNode({ match, onSelectTeam, selectedTeamId, isRealTeam }) {
  const isTeamASelected = selectedTeamId === match.team_a_id;
  const isTeamBSelected = selectedTeamId === match.team_b_id;

  return (
    <div className="bg-[#090b13] border border-white/5 rounded-2xl p-2 w-[180px] hover:border-fifagold/30 transition-all duration-300 shadow-lg">
      <div className="text-[8px] font-mono text-slate-500 uppercase flex justify-between items-center mb-1 px-1">
        <span>Match {match.match_id.replace('match_', '')}</span>
      </div>

      <div className="space-y-1">
        {/* Team A */}
        <div
          onClick={() => isRealTeam(match.team_a_id) && onSelectTeam(match.team_a_id)}
          className={`px-2 py-1.5 rounded-lg text-xs font-display flex justify-between items-center transition-all ${
            isRealTeam(match.team_a_id) 
              ? 'cursor-pointer hover:bg-white/5 text-white font-semibold' 
              : 'text-slate-500'
          } ${isTeamASelected ? 'bg-fifagold/10 text-fifagold border border-fifagold/20' : 'border border-transparent'}`}
        >
          <span className="truncate">{match.team_a_name}</span>
        </div>

        {/* Team B */}
        <div
          onClick={() => isRealTeam(match.team_b_id) && onSelectTeam(match.team_b_id)}
          className={`px-2 py-1.5 rounded-lg text-xs font-display flex justify-between items-center transition-all ${
            isRealTeam(match.team_b_id) 
              ? 'cursor-pointer hover:bg-white/5 text-white font-semibold' 
              : 'text-slate-500'
          } ${isTeamBSelected ? 'bg-fifagold/10 text-fifagold border border-fifagold/20' : 'border border-transparent'}`}
        >
          <span className="truncate">{match.team_b_name}</span>
        </div>
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
