import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, Tuple

logger = logging.getLogger("transformation_elo")

# Default starting Elo
INITIAL_ELO = 1500.0

def get_k_factor(tournament: str) -> float:
    """
    Returns K-factor based on tournament importance.
    Matches standard international Elo conventions.
    """
    t_lower = tournament.lower()
    if "friendly" in t_lower:
        return 20.0
    elif "fifa world cup qualification" in t_lower or "world cup qualification" in t_lower:
        return 40.0
    elif "fifa world cup" in t_lower:
        return 60.0
    elif "cup" in t_lower or "championship" in t_lower:
        # Continental tournaments (Euros, Copa America, etc.)
        return 50.0
    return 30.0

def calculate_expected_score(elo_a: float, elo_b: float, neutral: bool) -> Tuple[float, float]:
    """
    Calculates expected score using logistic curve.
    Adds home advantage of 100 Elo points if not neutral.
    """
    home_adv = 0.0 if neutral else 100.0
    dr = (elo_a + home_adv) - elo_b
    exp_a = 1.0 / (10.0 ** (-dr / 400.0) + 1.0)
    exp_b = 1.0 - exp_a
    return exp_a, exp_b

def compute_historical_elos(results_path: str, output_path: str) -> Dict[str, float]:
    """
    Reads results.csv and runs chronological Elo ratings update.
    Saves the final pre-tournament ratings at June 6, 2026.
    """
    logger.info("Starting chronological Elo computation from 1872...")
    
    # Load international results
    df = pd.read_csv(results_path)
    
    # Parse date and sort chronologically
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    
    # Filter matches up to the prediction freeze date (June 6, 2026)
    freeze_date = pd.to_datetime("2026-06-06")
    df = df[df["date"] <= freeze_date].reset_index(drop=True)
    
    # Tracking current Elo
    current_elos: Dict[str, float] = {}
    
    # To store Elo trace for debugging/auditing
    elo_trace = []
    
    for idx, row in df.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        
        # Initialize if new team
        if home_team not in current_elos:
            current_elos[home_team] = INITIAL_ELO
        if away_team not in current_elos:
            current_elos[away_team] = INITIAL_ELO
            
        elo_home_before = current_elos[home_team]
        elo_away_before = current_elos[away_team]
        
        # Determine actual outcome
        home_score = row["home_score"]
        away_score = row["away_score"]
        
        # Skip match if score is missing/nan
        if pd.isna(home_score) or pd.isna(away_score):
            continue
            
        if home_score > away_score:
            w_home, w_away = 1.0, 0.0
        elif home_score < away_score:
            w_home, w_away = 0.0, 1.0
        else:
            w_home, w_away = 0.5, 0.5
            
        # Calculate expected scores
        exp_home, exp_away = calculate_expected_score(elo_home_before, elo_away_before, row["neutral"])
        
        # Update Elo
        k = get_k_factor(row["tournament"])
        
        delta_home = k * (w_home - exp_home)
        
        current_elos[home_team] += delta_home
        current_elos[away_team] -= delta_home
        
        elo_trace.append({
            "date": row["date"],
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "tournament": row["tournament"],
            "neutral": row["neutral"],
            "elo_home_before": elo_home_before,
            "elo_away_before": elo_away_before,
            "elo_home_after": current_elos[home_team],
            "elo_away_after": current_elos[away_team]
        })
        
    # Convert trace to dataframe and save
    trace_df = pd.DataFrame(elo_trace)
    trace_df.to_csv(output_path, index=False)
    logger.info(f"Chronological Elo trace successfully calculated and saved to {output_path}")
    
    # Save final ratings for reference
    final_ratings_path = os.path.join(os.path.dirname(output_path), "final_ratings.csv")
    final_df = pd.DataFrame(list(current_elos.items()), columns=["team_name", "elo_rating"]).sort_values("elo_rating", ascending=False)
    final_df.to_csv(final_ratings_path, index=False)
    logger.info(f"Final pre-tournament Elo ratings saved to {final_ratings_path}")
    
    # Print top 15 teams to verify
    logger.info(f"Top 15 International Teams by Elo as of 2026-06-06:\n{final_df.head(15).to_string(index=False)}")
    
    return current_elos

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "footballdata", "results.csv"))
    output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "footballdata", "elo_trace.csv"))
    
    if os.path.exists(results_file):
        compute_historical_elos(results_file, output_file)
    else:
        logger.error(f"Cannot run Elo transformation. File not found: {results_file}")
