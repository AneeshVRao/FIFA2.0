import React, { useState } from 'react';
import useSWR from 'swr';
import { TrophyIcon, WarningIcon } from '../components/Icons';

const fetcher = (url) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
});

export default function BracketExplorer() {
  const { data: matchesData } = useSWR('/predictions/matches', fetcher);
  const [drilldownTeamId, setDrilldownTeamId] = useState(null);

  // Fetch stage probs for the selected team
  const { data: teamProbs, error: probsError } = useSWR(
    drilldownTeamId ? `/teams/${drilldownTeamId}/stage-probs` : null,
    fetcher
  );

  const loading = !matchesData;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-12 h-12 rounded-full border-t-2 border-fifagold animate-spin"></div>
        <p className="font-mono text-xs text-slate-400 uppercase tracking-widest">
          Parsing bracket projections...
        </p>
      </div>
    );
  }

  // Filter knockout matches (match_73 through match_104)
  const knockoutMatches = matchesData.matches.filter(
    (m) => m.stage !== 'group' && m.match_id !== 'match_103' // exclude third place for clean tree
  );
  const thirdPlaceMatch = matchesData.matches.find((m) => m.match_id === 'match_103');

  // Group matches by stage
  const r32 = knockoutMatches.filter((m) => m.stage === 'r32');
  const r16 = knockoutMatches.filter((m) => m.stage === 'r16');
  const qf = knockoutMatches.filter((m) => m.stage === 'quarterfinal');
  const sf = knockoutMatches.filter((m) => m.stage === 'semifinal');
  const final = knockoutMatches.filter((m) => m.stage === 'final');

  // Helper to check if team is a slot placeholder or actual team
  const isRealTeam = (teamId) => teamId && !teamId.startsWith('slot_');

  return (
    <div className="space-y-12 animate-fade-in py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/5 pb-8">
        <div>
          <h1 className="text-4xl md:text-5xl font-display font-extrabold text-white tracking-tight leading-none">
            Tournament Bracket Explorer
          </h1>
          <p className="text-sm text-slate-400 mt-2 max-w-xl">
            Explore simulated knockout brackets. Select any team to inspect their stage-by-stage progression probabilities.
          </p>
        </div>
      </div>

      {/* Main Bracket Layout (Horizontally scrollable tree) */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Left Col: Horizontal Bracket Scrollable Container */}
        <div className="xl:col-span-3 overflow-x-auto pb-6 -mx-4 px-4 xl:mx-0 xl:px-0">
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

        {/* Right Col: Team Drilldown sidebar info */}
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
                      
                      {/* Champion */}
                      <StageProbRow label="Champion" prob={teamProbs.stage_probabilities.champion} color="bg-fifagold" />
                      {/* Final */}
                      <StageProbRow label="Reach Final" prob={teamProbs.stage_probabilities.final} color="bg-slate-300" />
                      {/* Semifinal */}
                      <StageProbRow label="Reach SF" prob={teamProbs.stage_probabilities.semifinal} color="bg-blue-400" />
                      {/* Quarterfinal */}
                      <StageProbRow label="Reach QF" prob={teamProbs.stage_probabilities.quarterfinal} color="bg-slate-500" />
                      {/* R16 */}
                      <StageProbRow label="Reach R16" prob={teamProbs.stage_probabilities.r16} color="bg-slate-600" />
                      {/* R32 */}
                      <StageProbRow label="Reach R32" prob={teamProbs.stage_probabilities.r32} color="bg-slate-700" />
                      {/* Group Advance */}
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
                    <span className="text-[10px] font-mono uppercase text-slate-400">Loading probabilities...</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="doppelrand-card h-64 flex items-center justify-center text-center p-6">
              <div className="space-y-2">
                <TrophyIcon className="w-8 h-8 text-slate-600 mx-auto" />
                <h3 className="text-sm font-display font-semibold text-slate-400">No Team Selected</h3>
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
