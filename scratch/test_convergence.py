import os
import json
import logging
import duckdb
import numpy as np
import random
import sys
from multiprocessing import Pool
from typing import Dict, List, Any
from src.simulation.run_simulation import simulate_single_tournament

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("convergence_test")

def run_batch_worker(args):
    batch_size, start_seed, group_assignments, venues, player_dict = args
    champions = []
    for i in range(batch_size):
        res = simulate_single_tournament(start_seed + i, group_assignments, venues, player_dict)
        champions.append(res["champion"])
    return champions

def main():
    n_sims_per_batch = 10000
    if len(sys.argv) > 1:
        try:
            n_sims_per_batch = int(sys.argv[1])
        except ValueError:
            pass

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    teams_json_path = os.path.join(base_dir, "data", "wc_2026_teams.json")

    con = duckdb.connect(db_path)
    data = json.load(open(teams_json_path))
    df_teams = con.execute("SELECT * FROM dim_teams").fetchdf()
    team_meta = df_teams.to_dict(orient="records")
    team_meta_dict = {t["team_name_canonical"]: t for t in team_meta}

    group_assignments = {}
    for gcode, teams in data["groups"].items():
        group_assignments[gcode] = []
        for t in teams:
            tname = t["name"]
            if tname == 'USA': tname = 'United States'
            if tname == 'Curaçao': tname = 'Curaçao'
            if tname == 'Curaao': tname = 'Curaçao'
            if tname == 'Curacao': tname = 'Curaçao'
            meta = team_meta_dict[tname]
            group_assignments[gcode].append(meta)

    df_venues = con.execute("SELECT * FROM dim_venues").fetchdf()
    venues = df_venues.to_dict(orient="records")

    df_players = con.execute("SELECT * FROM dim_players").fetchdf()
    players_list = df_players.to_dict(orient="records")

    player_dict = {}
    team_id_to_name = {t["reep_team_id"]: t["team_name_canonical"] for t in team_meta}
    for p in players_list:
        tname = team_id_to_name.get(p["reep_team_id"], "Unknown")
        player_dict.setdefault(tname, []).append(p)
    con.close()

    n_batches = 5
    batch_champions = {i: [] for i in range(n_batches)}

    logger.info(f"Starting convergence test: 5 batches of {n_sims_per_batch:,} runs each...")

    chunk_size = 50
    for b_idx in range(n_batches):
        logger.info(f"Running batch {b_idx + 1}/5...")
        # Prepare multiprocessing tasks for this batch
        tasks = []
        n_chunks = n_sims_per_batch // chunk_size
        start_seed_batch = b_idx * n_sims_per_batch
        
        for c in range(n_chunks):
            tasks.append((chunk_size, start_seed_batch + c * chunk_size, group_assignments, venues, player_dict))
            
        with Pool(processes=8) as pool:
            chunks_champions = pool.map(run_batch_worker, tasks)
            
        for chunk in chunks_champions:
            batch_champions[b_idx].extend(chunk)

    # Aggregate champion probabilities for each team across the 5 batches
    team_probs_across_batches = {tname: [] for tname in team_meta_dict}
    for b_idx in range(n_batches):
        champs = batch_champions[b_idx]
        counts = {tname: 0 for tname in team_meta_dict}
        for c in champs:
            if c in counts:
                counts[c] += 1
        for tname in team_meta_dict:
            team_probs_across_batches[tname].append(counts[tname] / n_sims_per_batch)

    # Compute standard deviations
    stds = {}
    for tname, probs in team_probs_across_batches.items():
        std = np.std(probs)
        stds[tname] = std

    # Print results
    print("\n=== CONVERGENCE RESULTS ===")
    sorted_stds = sorted(stds.items(), key=lambda x: x[1], reverse=True)
    for tname, std in sorted_stds[:10]:
        probs_str = ", ".join([f"{p*100:.2f}%" for p in team_probs_across_batches[tname]])
        print(f"  {tname:<25}: SD = {std*100:.3f}% (Probabilities: [{probs_str}])")

    max_std = max(stds.values())
    print(f"\nMaximum standard deviation across batches: {max_std*100:.3f}%")
    if max_std < 0.005:
        print("SUCCESS: Convergence criteria met (max SD < 0.5%)!")
    else:
        print("WARNING: Convergence criteria NOT met (max SD >= 0.5%). Consider increasing the number of runs per batch.")

if __name__ == "__main__":
    main()
