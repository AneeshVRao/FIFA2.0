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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("simulation_runner")

# Helper to simulate a single tournament run
def simulate_single_tournament(
    seed: int,
    group_assignments: Dict[str, List[Dict[str, Any]]],
    venues: List[Dict[str, Any]],
    player_dict: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Simulates a single complete 2026 World Cup tournament.
    """
    # Seed the random number generators
    np.random.seed(seed)
    random.seed(seed)
    
    # 1. Group Stage
    group_matches, team_states = simulate_group_stage(group_assignments, venues, None)
    
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
    batch_size, start_seed, group_assignments, venues, player_dict = args
    results = []
    for i in range(batch_size):
        results.append(simulate_single_tournament(start_seed + i, group_assignments, venues, player_dict))
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
        
    con.close()
    
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
        tasks.append((batch_size, b * batch_size, group_assignments, venues, player_dict))
        
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
    # Track total goals scored by each team in simulation runs
    team_total_goals = {tname: 0.0 for tname in team_meta_dict}
    
    # 4. Matchup forecasts aggregation
    # Key: (team_a, team_b) sorted -> counts and scorelines
    matchup_stats = {}
    
    for run in sim_results:
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
                
        # Team goals scored
        for tname, goals in run["team_goals_scored"].items():
            team_total_goals[tname] += goals
            
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
    player_goals_dist = []
    for tname, players in player_dict.items():
        # Compute normalized goal contribution fractions for the team
        # Based on historical goals and caps (or defaults)
        total_weight = 0.0
        player_weights = []
        
        for p in players:
            pos = p["position"]
            caps = p.get("international_caps", 15) or 15
            goals = p.get("international_goals", 0) or 0
            
            # Base contribution prior
            if pos == "Forward": base_weight = 0.40
            elif pos == "Midfielder": base_weight = 0.20
            elif pos == "Defender": base_weight = 0.05
            else: base_weight = 0.00
            
            # Historical rate + prior smoothing
            hist_rate = goals / max(1.0, caps)
            weight = 0.5 * base_weight + 0.5 * hist_rate
            if pos == "Goalkeeper":
                weight = 0.0
                
            player_weights.append((p, weight))
            total_weight += weight
            
        # Draw player goals using Poisson distributions for Golden Boot table
        for p, w in player_weights:
            frac = w / max(0.001, total_weight)
            
            # Mean goals across all runs = frac * average team goals
            avg_team_goals = team_total_goals[tname] / n_sims
            mean_player_goals = frac * avg_team_goals
            
            # Generate simulated distributions for percentiles: p10, p50, p90
            # Sample 1000 draws to get percentiles
            simulated_draws = np.random.poisson(mean_player_goals, size=1000)
            p10 = int(np.percentile(simulated_draws, 10))
            p50 = int(np.percentile(simulated_draws, 50))
            p90 = int(np.percentile(simulated_draws, 90))
            
            # Outright Golden Boot winner probability is simplified:
            # We can approximate it by the fraction of team goals they score
            # Let's say their probability of winning Golden Boot is proportional to their mean goals
            player_goals_dist.append({
                "reep_player_id": p["reep_player_id"],
                "sim_run_id": "sim_mc_100k",
                "mean_goals": float(mean_player_goals),
                "p10_goals": float(p10),
                "p50_goals": float(p50),
                "p90_goals": float(p90),
                "p_golden_boot": 0.0, # Will normalize later
                "expected_minutes": float(frac * 450.0) # Approx minutes played
            })
            
    # Normalize Golden Boot probabilities
    tot_mean_goals = sum(p["mean_goals"] for p in player_goals_dist)
    for p in player_goals_dist:
        p["p_golden_boot"] = p["mean_goals"] / max(0.001, tot_mean_goals)
        
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
    
    con.close()
    
    logger.info("========================================")
    logger.info("Phase 3: Tournament Simulation Successfully Completed!")
    logger.info("========================================")
    
if __name__ == "__main__":
    main()
