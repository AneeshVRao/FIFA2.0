import os
import json
import logging
import duckdb
import pandas as pd
import numpy as np
import random
from multiprocessing import Pool
from typing import Dict, List, Tuple, Any
from src.simulation.tournament import simulate_group_stage, calculate_standings, advance_third_place_teams, assign_r32_pairings, simulate_knockout_stage
from src.simulation.shootout_sim import get_shootout_roster
from src.data.live_ingestion import fetch_injury_risk

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("simulation_runner")

# Helper to calculate Bayesian shrinkage prior weight
def calculate_bayesian_prior_weight(pos: str, caps: int, goals: int) -> float:
    if pos == "Forward":
        alpha, beta = 2.0, 10.0
        base_weight = 0.40
    elif pos == "Midfielder":
        alpha, beta = 0.5, 10.0
        base_weight = 0.20
    elif pos == "Defender":
        alpha, beta = 0.1, 10.0
        base_weight = 0.05
    else:
        alpha, beta = 0.0, 10.0
        base_weight = 0.00
    hist_rate = (goals + alpha) / (caps + beta)
    return 0.5 * base_weight + 0.5 * hist_rate

# Helper to simulate a single tournament run
def simulate_single_tournament(
    seed: int,
    group_assignments: Dict[str, List[Dict[str, Any]]],
    venues: List[Dict[str, Any]],
    player_dict: Dict[str, List[Dict[str, Any]]],
    actual_matches: Dict[str, Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Simulates a single complete 2026 World Cup tournament.
    """
    # Seed the random number generators
    np.random.seed(seed)
    random.seed(seed)
    
    # 1. Group Stage
    group_matches, team_states = simulate_group_stage(group_assignments, venues, actual_matches)
    
    # 2. Standings & Tiebreakers
    standings = calculate_standings(group_matches, team_states)
    
    # 3. Third-Place advancement
    adv_3rd, elim_3rd = advance_third_place_teams(standings)
    
    # 4. R32 bracket assignments
    r32_matches = assign_r32_pairings(standings, adv_3rd)
    
    # 5. Knockout Stage
    bracket_runs, knockout_matches = simulate_knockout_stage(r32_matches, player_dict, None)
    
    # Track stages reached
    stage_reached = {}
    for team_name in team_states:
        stage_reached[team_name] = "Group"
        
    # Mark third place advanced
    for t in adv_3rd:
        stage_reached[t["team_name"]] = "R32" # advanced from group
        
    for gcode, t_list in standings.items():
        # Top 2 advance to R32
        stage_reached[t_list[0]["team_name"]] = "R32"
        stage_reached[t_list[1]["team_name"]] = "R32"
        
    # Mark knockout achievements
    for match in knockout_matches:
        stage = match["stage"]
        m_num = match["match_num"]
        winner = match["winner"]
        loser = match["loser"]
        
        # Determine loser's final stage
        if 73 <= m_num <= 88:
            stage_reached[loser] = "R32"
        elif 89 <= m_num <= 96:
            stage_reached[loser] = "R16"
        elif 97 <= m_num <= 100:
            stage_reached[loser] = "QF"
        elif m_num == 103:
            stage_reached[loser] = "SF" # 4th place
            stage_reached[winner] = "SF" # 3rd place
            
    stage_reached[bracket_runs["runner_up"]] = "Final"
    stage_reached[bracket_runs["champion"]] = "Champion"
    
    # Track standings position for all teams
    group_positions = {}
    team_goals_scored = {}
    for gcode, t_list in standings.items():
        for pos_idx, t in enumerate(t_list):
            group_positions[t["team_name"]] = pos_idx + 1
            team_goals_scored[t["team_name"]] = t["goals_for"]
            
    # Combine matches
    all_matches = group_matches + knockout_matches
    
    return {
        "champion": bracket_runs["champion"],
        "runner_up": bracket_runs["runner_up"],
        "third_place": bracket_runs["third_place"],
        "fourth_place": bracket_runs["fourth_place"],
        "stage_reached": stage_reached,
        "group_positions": group_positions,
        "team_goals_scored": team_goals_scored,
        "matches": all_matches
    }

def run_simulation_batch(args) -> List[Dict[str, Any]]:
    """Runs a batch of simulations sequentially within a process."""
    batch_size, start_seed, group_assignments, venues, player_dict, actual_matches = args
    results = []
    for i in range(batch_size):
        results.append(simulate_single_tournament(start_seed + i, group_assignments, venues, player_dict, actual_matches))
    return results

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_path = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    teams_json_path = os.path.join(base_dir, "data", "wc_2026_teams.json")
    
    logger.info("Connecting to DuckDB and loading pre-tournament rosters...")
    con = duckdb.connect(db_path)
    
    # Load 2026 group structures
    data = json.load(open(teams_json_path))
    
    # Load dim_teams
    df_teams = con.execute("SELECT * FROM dim_teams").fetchdf()
    team_meta = df_teams.to_dict(orient="records")
    team_meta_dict = {t["team_name_canonical"]: t for t in team_meta}
    
    # Build group assignments
    group_assignments = {}
    for gcode, teams in data["groups"].items():
        group_assignments[gcode] = []
        for t in teams:
            tname = t["name"]
            if tname == 'USA': tname = 'United States'
            if tname in ['Curaçao', 'Curaao', 'Curacao']: tname = 'Curaçao'
            meta = team_meta_dict[tname]
            group_assignments[gcode].append(meta)
            
    # Load dim_venues
    df_venues = con.execute("SELECT * FROM dim_venues").fetchdf()
    venues = df_venues.to_dict(orient="records")
    
    # Load dim_players
    df_players = con.execute("SELECT * FROM dim_players").fetchdf()
    players_list = df_players.to_dict(orient="records")
    
    # Group players by team name
    player_dict = {}
    # Map team_id to team_name
    team_id_to_name = {t["reep_team_id"]: t["team_name_canonical"] for t in team_meta}
    for p in players_list:
        tname = team_id_to_name.get(p["reep_team_id"], "Unknown")
        player_dict.setdefault(tname, []).append(p)
        
    # Load actual completed matches from DB
    df_actual = con.execute('SELECT match_id, goals_a, goals_b FROM fct_matches WHERE goals_a IS NOT NULL').fetchdf()
    actual_matches = {}
    for _, row in df_actual.iterrows():
        actual_matches[row["match_id"]] = {"goals_a": int(row["goals_a"]), "goals_b": int(row["goals_b"])}
    
    con.close()
    
    # Dynamic Team Strength Updates (Fatigue Penalty)
    # Fetch injury risks via Football Intelligence Hub
    api_key = os.getenv("APIFY_API_TOKEN", "apify_api_sxiDqx2ZWJEGMLb2N3MSTsdai0c30x3nl0lN_placeholder")
    injury_risks = fetch_injury_risk(api_key)
    
    # Penalize team pre-tournament Elo based on key player fatigue/injury
    for group_teams in group_assignments.values():
        for team in group_teams:
            tname = team["team_name_canonical"]
            # Sum up injury risk for this team's players
            team_risk = 0.0
            for p in player_dict.get(tname, []):
                pid = p["reep_player_id"]
                if pid in injury_risks:
                    team_risk += injury_risks[pid]
            # Example logic: reduce Elo by 0.5 per point of cumulative risk 
            # (e.g., player_1 has 85 risk -> team loses 42.5 Elo)
            if team_risk > 0:
                logger.info(f"Applying fatigue penalty of -{team_risk * 0.5:.1f} Elo to {tname}")
                team["pretournament_elo"] -= (team_risk * 0.5)
    
    import sys
    n_sims = 100000
    if len(sys.argv) > 1:
        try:
            n_sims = int(sys.argv[1])
        except ValueError:
            pass
            
    logger.info(f"Initializing {n_sims:,} Monte Carlo simulations...")
    batch_size = 50
    n_batches = max(1, n_sims // batch_size)
    # Adjust n_sims to be a multiple of batch_size
    n_sims = n_batches * batch_size

    
    # Multiprocessing arguments
    tasks = []
    for b in range(n_batches):
        tasks.append((batch_size, b * batch_size, group_assignments, venues, player_dict, actual_matches))
        
    logger.info(f"Running simulations in parallel using 8 CPU cores...")
    # Run in parallel
    with Pool(processes=8) as pool:
        batches_results = pool.map(run_simulation_batch, tasks)
        
    # Flatten results list
    sim_results = [res for batch in batches_results for res in batch]
    logger.info(f"Simulations completed! Aggregating results...")
    
    # 1. Aggregate stage probabilities
    # Stages: Group, R32, R16, QF, SF, Final, Champion
    stage_counts = {tname: {"Group": 0, "R32": 0, "R16": 0, "QF": 0, "SF": 0, "Final": 0, "Champion": 0} for tname in team_meta_dict}
    
    # 2. Aggregate group position frequencies
    pos_counts = {tname: {1: 0, 2: 0, 3: 0, 4: 0, "3rd_advance": 0} for tname in team_meta_dict}
    
    # 3. Aggregate player expected goals (Golden Boot)
    team_goals_by_sim = {tname: np.zeros(n_sims, dtype=np.int32) for tname in team_meta_dict}
    
    # 4. Matchup forecasts aggregation
    # Key: (team_a, team_b) sorted -> counts and scorelines
    matchup_stats = {}
    
    for sim_idx, run in enumerate(sim_results):
        # Stage advancement
        for tname, stage in run["stage_reached"].items():
            stage_counts[tname][stage] += 1
            # Propagate upwards (e.g. if Champion, also reached Final, SF, etc.)
            if stage == "Champion":
                stage_counts[tname]["Final"] += 1
                stage_counts[tname]["SF"] += 1
                stage_counts[tname]["QF"] += 1
                stage_counts[tname]["R16"] += 1
                stage_counts[tname]["R32"] += 1
            elif stage == "Final":
                stage_counts[tname]["SF"] += 1
                stage_counts[tname]["QF"] += 1
                stage_counts[tname]["R16"] += 1
                stage_counts[tname]["R32"] += 1
            elif stage == "SF":
                stage_counts[tname]["QF"] += 1
                stage_counts[tname]["R16"] += 1
                stage_counts[tname]["R32"] += 1
            elif stage == "QF":
                stage_counts[tname]["R16"] += 1
                stage_counts[tname]["R32"] += 1
            elif stage == "R16":
                stage_counts[tname]["R32"] += 1
                
        # Group positions
        for tname, pos in run["group_positions"].items():
            pos_counts[tname][pos] += 1
            if pos == 3 and run["stage_reached"][tname] != "Group":
                # Advanced as best 3rd
                pos_counts[tname]["3rd_advance"] += 1
                
        # Team goals scored (accumulate from all matches: group and knockout)
        for match in run["matches"]:
            team_goals_by_sim[match["team_a"]][sim_idx] += match["goals_a"]
            team_goals_by_sim[match["team_b"]][sim_idx] += match["goals_b"]
            
        # Matchups
        for match in run["matches"]:
            ta, tb = match["team_a"], match["team_b"]
            ga, gb = match["goals_a"], match["goals_b"]
            
            # Keep lexicographical order to group uniquely
            if ta < tb:
                key = (ta, tb)
                res_outcome = 1 if ga > gb else (2 if ga < gb else 0)
                scoreline_str = f"{ga}-{gb}"
                xg_a = match.get("lam", 1.25)
                xg_b = match.get("mu", 1.05)
            else:
                key = (tb, ta)
                res_outcome = 2 if ga > gb else (1 if ga < gb else 0)
                scoreline_str = f"{gb}-{ga}"
                xg_a = match.get("mu", 1.05)
                xg_b = match.get("lam", 1.25)
                
            m_stats = matchup_stats.setdefault(key, {
                "count": 0, "win_a": 0, "draw": 0, "win_b": 0,
                "tot_xg_a": 0.0, "tot_xg_b": 0.0, "scorelines": {}
            })
            m_stats["count"] += 1
            if res_outcome == 1:
                m_stats["win_a"] += 1
            elif res_outcome == 2:
                m_stats["win_b"] += 1
            else:
                m_stats["draw"] += 1
            m_stats["tot_xg_a"] += xg_a
            m_stats["tot_xg_b"] += xg_b
            m_stats["scorelines"][scoreline_str] = m_stats["scorelines"].get(scoreline_str, 0) + 1
            
    # Calculate player level Golden Boot probabilities
    # Calculate player relative goal contribution weights
    all_players = []
    
    for tname, players in player_dict.items():
        # Compute expected matches played by this team (SF reach guarantees 8 matches total: 7 + Final/3rd match)
        counts = stage_counts[tname]
        expected_matches = 3.0 + float(counts["R32"] + counts["R16"] + counts["QF"] + 2 * counts["SF"]) / n_sims
        
        # Calculate minutes per match based on starter/squad status
        gks = [p for p in players if p["position"] == "Goalkeeper"]
        outfields = [p for p in players if p["position"] != "Goalkeeper"]
        
        # Goalkeepers: Top GK plays 90 mins, others 0
        gks.sort(key=lambda x: (x.get("international_caps") or 0, x.get("market_value_eur") or 0), reverse=True)
        gk_minutes = {}
        for i, gk in enumerate(gks):
            gk_minutes[gk["reep_player_id"]] = 90.0 if i == 0 else 0.0
            
        # Outfielders: Compute scoring weights first to help rank importance
        outfield_weights = []
        for p in outfields:
            pos = p["position"]
            caps = p.get("international_caps", 15) or 15
            goals = p.get("international_goals", 0) or 0
            
            weight = calculate_bayesian_prior_weight(pos, caps, goals)
            outfield_weights.append((p, weight))
            
        # Sort outfielders by weight descending, then market value descending
        outfield_weights.sort(key=lambda x: (x[1], x[0].get("market_value_eur") or 0), reverse=True)
        
        outfielder_minutes = {}
        for i, (p, w) in enumerate(outfield_weights):
            if i < 10:
                outfielder_minutes[p["reep_player_id"]] = 80.0 # Starters
            elif i < 15:
                outfielder_minutes[p["reep_player_id"]] = 30.0 # Key subs
            else:
                outfielder_minutes[p["reep_player_id"]] = 5.0 # Bench
                
        # Combine all and scale goal weights by playing time shares
        total_adjusted_weight = 0.0
        player_simulation_weights = []
        
        for p in players:
            pid = p["reep_player_id"]
            pos = p["position"]
            
            # Retrieve playing minutes per match
            if pos == "Goalkeeper":
                min_per_match = gk_minutes.get(pid, 0.0)
                weight = 0.0
            else:
                min_per_match = outfielder_minutes.get(pid, 5.0)
                # Recalculate base weight
                caps = p.get("international_caps", 15) or 15
                goals = p.get("international_goals", 0) or 0
                weight = calculate_bayesian_prior_weight(pos, caps, goals)
                
            expected_minutes = expected_matches * min_per_match
            adjusted_weight = weight * (min_per_match / 90.0)
            # Concentrate weights using a power exponent (e.g. 2.5) to focus goals on primary goalscoring forwards/midfielders
            adjusted_weight = adjusted_weight ** 2.5
            
            player_simulation_weights.append((p, adjusted_weight, expected_minutes))
            total_adjusted_weight += adjusted_weight
            
        for p, adj_w, exp_min in player_simulation_weights:
            frac = adj_w / max(0.001, total_adjusted_weight) if adj_w > 0 else 0.0
            all_players.append({
                "player_dict": p,
                "tname": tname,
                "frac": frac,
                "expected_minutes": exp_min
            })
            
    # Perform deterministic simulation for Golden Boot & Bracket matching
    logger.info("Running deterministic simulation run (seed 42) to align Golden Boot and Match data...")
    official_run = simulate_single_tournament(42, group_assignments, venues, player_dict, actual_matches)
    
    official_team_goals = {tname: 0 for tname in team_meta_dict}
    for m in official_run["matches"]:
        official_team_goals[m["team_a"]] += m["goals_a"]
        official_team_goals[m["team_b"]] += m["goals_b"]

    # Perform vectorized Binomial goals drawing for all players across all simulations based on deterministic bracket goals
    n_players = len(all_players)
    player_goals_matrix = np.zeros((n_players, n_sims), dtype=np.int16)
    
    logger.info(f"Simulating individual goals for {n_players} players over {n_sims} runs (aligned with seed 42)...")
    for idx, item in enumerate(all_players):
        tname = item["tname"]
        frac = item["frac"]
        if frac > 0:
            deterministic_goals = official_team_goals[tname]
            player_goals_matrix[idx, :] = np.random.binomial(deterministic_goals, frac, size=n_sims)
            
    # Compute Golden Boot winners per simulation run
    logger.info("Computing Golden Boot winner probabilities and percentiles...")
    max_goals_per_sim = np.max(player_goals_matrix, axis=0)
    is_winner = (player_goals_matrix == max_goals_per_sim) & (player_goals_matrix > 0)
    winners_per_sim = np.sum(is_winner, axis=0)
    
    # Share the award equally among all tied players in each simulation run
    share_per_sim = np.zeros_like(winners_per_sim, dtype=np.float64)
    non_zero_mask = winners_per_sim > 0
    share_per_sim[non_zero_mask] = 1.0 / winners_per_sim[non_zero_mask]
    
    golden_boot_probs = np.sum(is_winner * share_per_sim[np.newaxis, :], axis=1) / n_sims
    
    # Build final player goals distributions data
    player_goals_dist = []
    for idx, item in enumerate(all_players):
        p = item["player_dict"]
        tname = item["tname"]
        exp_min = item["expected_minutes"]
        
        goals_arr = player_goals_matrix[idx, :]
        mean_player_goals = np.mean(goals_arr)
        p10 = int(np.percentile(goals_arr, 10))
        p50 = int(np.percentile(goals_arr, 50))
        p90 = int(np.percentile(goals_arr, 90))
        p_gb = float(golden_boot_probs[idx])
        
        player_goals_dist.append({
            "reep_player_id": p["reep_player_id"],
            "sim_run_id": "sim_mc_100k",
            "mean_goals": float(mean_player_goals),
            "p10_goals": float(p10),
            "p50_goals": float(p50),
            "p90_goals": float(p90),
            "p_golden_boot": p_gb,
            "expected_minutes": float(exp_min)
        })
        
    # Reconnect to DuckDB to write gold tables
    logger.info(f"Writing aggregated analytical tables to DuckDB database...")
    con = duckdb.connect(db_path)
    
    # 1. Table team_stage_probabilities
    team_probs_rows = []
    for tname, state in team_meta_dict.items():
        counts = stage_counts[tname]
        pos = pos_counts[tname]
        team_probs_rows.append({
            "reep_team_id": state["reep_team_id"],
            "sim_run_id": "sim_mc_100k",
            "p_group_advance": float(counts["R32"] / n_sims),
            "p_r32": float(counts["R32"] / n_sims),
            "p_r16": float(counts["R16"] / n_sims),
            "p_qf": float(counts["QF"] / n_sims),
            "p_sf": float(counts["SF"] / n_sims),
            "p_final": float(counts["Final"] / n_sims),
            "p_champion": float(counts["Champion"] / n_sims),
            "p_group_1st": float(pos[1] / n_sims),
            "p_group_2nd": float(pos[2] / n_sims),
            "p_group_3rd_advance": float(pos["3rd_advance"] / n_sims),
            "n_simulations": n_sims,
            "computed_at": pd.Timestamp.now()
        })
    df_stage_probs = pd.DataFrame(team_probs_rows)
    con.execute("CREATE OR REPLACE TABLE team_stage_probabilities AS SELECT * FROM df_stage_probs")
    
    # 2. Table golden_boot_distribution
    df_gb = pd.DataFrame(player_goals_dist)
    con.execute("CREATE OR REPLACE TABLE golden_boot_distribution AS SELECT * FROM df_gb")
    
    # 3. Table matchup_forecasts
    matchup_rows = []
    for (ta, tb), stats in matchup_stats.items():
        cnt = stats["count"]
        # Top 5 scorelines
        sorted_scorelines = sorted(stats["scorelines"].items(), key=lambda x: x[1], reverse=True)[:5]
        scorelines_json = json.dumps([{"score": s[0], "probability": float(s[1]/cnt)} for s in sorted_scorelines])
        
        matchup_rows.append({
            "team_a_id": team_meta_dict[ta]["reep_team_id"],
            "team_b_id": team_meta_dict[tb]["reep_team_id"],
            "p_team_a_win": float(stats["win_a"] / cnt),
            "p_draw": float(stats["draw"] / cnt),
            "p_team_b_win": float(stats["win_b"] / cnt),
            "team_a_xg": float(stats["tot_xg_a"] / cnt),
            "team_b_xg": float(stats["tot_xg_b"] / cnt),
            "most_likely_scorelines": scorelines_json,
            "matches_played": cnt
        })
    df_matchups = pd.DataFrame(matchup_rows)
    con.execute("CREATE OR REPLACE TABLE matchup_forecasts AS SELECT * FROM df_matchups")
    
    # 4. Table group_table_distributions
    group_dist_rows = []
    for tname, state in team_meta_dict.items():
        pos = pos_counts[tname]
        group_dist_rows.append({
            "reep_team_id": state["reep_team_id"],
            "team_name": tname,
            "group_code": state["group_code"],
            "p_1st": float(pos[1] / n_sims),
            "p_2nd": float(pos[2] / n_sims),
            "p_3rd": float(pos[3] / n_sims),
            "p_4th": float(pos[4] / n_sims),
            "p_3rd_advance": float(pos["3rd_advance"] / n_sims)
        })
    df_group_dists = pd.DataFrame(group_dist_rows)
    con.execute("CREATE OR REPLACE TABLE group_table_distributions AS SELECT * FROM df_group_dists")
    
    # 5. Table bracket_path_frequencies (summarizes champions and podiums)
    podium_rows = []
    # Count final matchups frequencies
    finals_counts = {}
    for run in sim_results:
        key = (run["champion"], run["runner_up"])
        finals_counts[key] = finals_counts.get(key, 0) + 1
        
    sorted_paths = sorted(finals_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    for (champ, runner), cnt in sorted_paths:
        podium_rows.append({
            "champion_id": team_meta_dict[champ]["reep_team_id"],
            "runner_up_id": team_meta_dict[runner]["reep_team_id"],
            "frequency_pct": float(cnt / n_sims),
            "n_simulations": n_sims
        })
    df_paths = pd.DataFrame(podium_rows)
    con.execute("CREATE OR REPLACE TABLE bracket_path_frequencies AS SELECT * FROM df_paths")
    
    # 6. Table fct_matches (Single representative tournament run with seed 42)
    logger.info("Populating fct_matches with the deterministic run...")
    
    matches_rows = []
    group_idx = 1
    for m in official_run["matches"]:
        team_a_name = m["team_a"]
        team_b_name = m["team_b"]
        team_a_id = team_meta_dict[team_a_name]["reep_team_id"]
        team_b_id = team_meta_dict[team_b_name]["reep_team_id"]
        
        if m["stage"] == "group":
            match_id = f"match_{group_idx}"
            group_idx += 1
            
            # Use actual results if they exist instead of simulated ones for writing back to fct_matches
            actual_ga = actual_matches.get(match_id, {}).get("goals_a") if actual_matches else None
            actual_gb = actual_matches.get(match_id, {}).get("goals_b") if actual_matches else None
            
            matches_rows.append({
                "match_id": match_id,
                "stage": "group",
                "team_a_id": team_a_id,
                "team_a_name": team_a_name,
                "team_b_id": team_b_id,
                "team_b_name": team_b_name,
                "goals_a": actual_ga if actual_ga is not None else None,
                "goals_b": actual_gb if actual_gb is not None else None,
                "went_to_extra_time": False,
                "went_to_penalties": False,
                "penalty_winner": None,
                "venue_id": m["venue_id"]
            })
        else:
            match_id = f"match_{m['match_num']}"
            m_num = m['match_num']
            if 73 <= m_num <= 88:
                m_stage = "r32"
            elif 89 <= m_num <= 96:
                m_stage = "r16"
            elif 97 <= m_num <= 100:
                m_stage = "quarterfinal"
            elif 101 <= m_num <= 102:
                m_stage = "semifinal"
            elif m_num == 103:
                m_stage = "third_place"
            elif m_num == 104:
                m_stage = "final"
            else:
                m_stage = m["stage"]
                
            matches_rows.append({
                "match_id": match_id,
                "stage": m_stage,
                "team_a_id": team_a_id,
                "team_a_name": team_a_name,
                "team_b_id": team_b_id,
                "team_b_name": team_b_name,
                "goals_a": None,
                "goals_b": None,
                "went_to_extra_time": bool(m["went_to_extra_time"]),
                "went_to_penalties": bool(m["went_to_penalties"]),
                "penalty_winner": m["penalty_winner"],
                "venue_id": None
            })
            
    df_fct_matches = pd.DataFrame(matches_rows)
    con.execute("CREATE OR REPLACE TABLE fct_matches AS SELECT * FROM df_fct_matches")
    
    con.close()
    
    logger.info("========================================")
    logger.info("Phase 3: Tournament Simulation Successfully Completed!")
    logger.info("========================================")
    
if __name__ == "__main__":
    main()
