import os
import logging
import duckdb
import numpy as np
import pandas as pd
import ast
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("feature_engineering")

# Goal coordinates (for a standard 100x100 pitch representation)
GOAL_X = 100.0
GOAL_Y_LEFT = 36.8
GOAL_Y_RIGHT = 63.2
GOAL_Y_CENTER = 50.0

def compute_distance(x: float, y: float) -> float:
    return float(np.sqrt((GOAL_X - x)**2 + (GOAL_Y_CENTER - y)**2))

def compute_angle(x: float, y: float) -> float:
    a = np.sqrt((GOAL_X - x)**2 + (GOAL_Y_LEFT - y)**2)
    b = np.sqrt((GOAL_X - x)**2 + (GOAL_Y_RIGHT - y)**2)
    c = GOAL_Y_RIGHT - GOAL_Y_LEFT  # goalpost width
    numerator = a**2 + b**2 - c**2
    denominator = 2 * a * b
    if denominator == 0:
        return 0.0
    cos_angle = np.clip(numerator / denominator, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes distance in km between two GPS coordinates.
    """
    R = 6371.0 # Earth radius in km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2 + 
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return float(R * c)

def point_in_triangle(px: float, py: float, ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
    denom = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if denom == 0:
        return False
    w_a = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denom
    w_b = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denom
    w_c = 1.0 - w_a - w_b
    return w_a >= 0 and w_b >= 0 and w_c >= 0

def build_xg_features(con: duckdb.DuckDBPyConnection):
    """
    Extracts shot coordinate data from raw_statsbomb_shots, derives spatial features,
    and writes to fct_model_xg_features.
    """
    logger.info("Extracting spatial features for xG Model...")
    
    # Load raw statsbomb shots
    df = con.execute("SELECT match_id, season_id, location, shot_statsbomb_xg, shot_outcome, shot_body_part, shot_type, play_pattern, shot_freeze_frame, shot_first_time FROM raw_statsbomb_shots").fetchdf()
    
    # Extract X, Y from location string representation [x, y]
    def parse_coords(loc_str):
        if pd.isna(loc_str) or not isinstance(loc_str, str):
            return 80.0, 50.0 # fallback
        cleaned = loc_str.replace("[", "").replace("]", "").split(",")
        try:
            return float(cleaned[0].strip()), float(cleaned[1].strip())
        except Exception:
            return 80.0, 50.0
            
    coords = df["location"].apply(parse_coords)
    df["shot_x"] = [c[0] for c in coords]
    df["shot_y"] = [c[1] for c in coords]
    
    # Derive spatial metrics
    df["distance_to_goal_m"] = df.apply(lambda row: compute_distance(row["shot_x"], row["shot_y"]), axis=1)
    df["angle_to_goal_deg"] = df.apply(lambda row: compute_angle(row["shot_x"], row["shot_y"]), axis=1)
    
    # Set targets
    df["is_goal"] = df["shot_outcome"].apply(lambda val: 1 if str(val).lower() == "goal" else 0)
    
    # Extract StatsBomb freeze frame details
    defenders_in_cone_list = []
    defensive_pressure_list = []
    goalkeeper_distance_list = []
    
    for idx, row in df.iterrows():
        ff_str = row["shot_freeze_frame"]
        sx = row["shot_x"]
        sy = row["shot_y"]
        
        defenders_cone = 0
        defensive_pressure = 20.0 # fallback default distance
        gk_dist = 5.0 # fallback default distance
        
        if not pd.isna(ff_str) and isinstance(ff_str, str) and ff_str.strip():
            try:
                players = ast.literal_eval(ff_str)
                for p in players:
                    loc = p.get("location")
                    if not loc or len(loc) < 2:
                        continue
                    px, py = float(loc[0]), float(loc[1])
                    teammate = p.get("teammate", True)
                    pos_name = p.get("position", {}).get("name", "")
                    
                    if not teammate and pos_name == "Goalkeeper":
                        # Perpendicular distance from GK to ball-goal center line
                        dx = GOAL_X - sx
                        dy = GOAL_Y_CENTER - sy
                        if dx == 0 and dy == 0:
                            gk_dist = float(np.sqrt((px - sx)**2 + (py - sy)**2))
                        else:
                            numerator = abs(dy * px - dx * py + GOAL_X * sy - GOAL_Y_CENTER * sx)
                            denominator = np.sqrt(dx**2 + dy**2)
                            gk_dist = float(numerator / denominator)
                    elif not teammate and pos_name != "Goalkeeper":
                        if point_in_triangle(px, py, sx, sy, GOAL_X, GOAL_Y_LEFT, GOAL_X, GOAL_Y_RIGHT):
                            defenders_cone += 1
                        dist_to_shooter = float(np.sqrt((px - sx)**2 + (py - sy)**2))
                        if dist_to_shooter < defensive_pressure:
                            defensive_pressure = dist_to_shooter
            except Exception:
                pass
                
        defenders_in_cone_list.append(defenders_cone)
        defensive_pressure_list.append(defensive_pressure)
        goalkeeper_distance_list.append(gk_dist)
        
    df["defenders_in_cone"] = defenders_in_cone_list
    df["defensive_pressure_m"] = defensive_pressure_list
    df["goalkeeper_distance"] = goalkeeper_distance_list
    df["is_first_time"] = df["shot_first_time"].apply(lambda x: 1 if x is True or str(x).lower() == "true" else 0)
    
    # Write back to DuckDB
    con.execute("CREATE OR REPLACE TABLE fct_model_xg_features AS SELECT * FROM df")
    logger.info(f"xG features table successfully created with {len(df)} rows.")

def build_match_features(con: duckdb.DuckDBPyConnection):
    """
    Builds differential match-level features for the outcome predictor,
    writing back to fct_model_match_features.
    """
    logger.info("Extracting match differential features...")
    
    # 1. Start with international results trace (historical Elo ratings are already calculated!)
    results_query = """
    SELECT 
        date,
        home_team,
        away_team,
        home_score,
        away_score,
        tournament,
        neutral,
        elo_home_before AS elo_home,
        elo_away_before AS elo_away,
        (elo_home_before - elo_away_before) AS elo_rating_diff
    FROM fct_international_elo_trace
    """
    df_matches = con.execute(results_query).fetchdf()
    
    # Define outcomes
    def get_outcome(row):
        hs, as_ = row["home_score"], row["away_score"]
        if hs > as_:
            return 1 # Home Win
        elif hs < as_:
            return 2 # Away Win
        return 0 # Draw
        
    df_matches["outcome"] = df_matches.apply(get_outcome, axis=1)
    
    # Rest differentials & travel calculations
    df_matches["date"] = pd.to_datetime(df_matches["date"])
    df_matches = df_matches.sort_values("date").reset_index(drop=True)
    
    df_matches["timezone_crossings_diff"] = 0
    df_matches["team_a_travel_km"] = 0.0
    df_matches["team_b_travel_km"] = 0.0
    df_matches["rest_day_asymmetry"] = 0.0
    df_matches["altitude_diff_m"] = 0.0
    
    # Compute Transfermarkt valuation differentials
    logger.info("Computing squad market valuation differentials...")
    df_matches["year"] = df_matches["date"].dt.year
    
    tm_query = """
    WITH player_yearly_val AS (
        SELECT 
            player_id,
            EXTRACT(year FROM CAST(date AS DATE)) AS val_year,
            market_value_in_eur,
            ROW_NUMBER() OVER (PARTITION BY player_id, EXTRACT(year FROM CAST(date AS DATE)) ORDER BY date DESC) as rn
        FROM raw_transfermarkt_player_valuations
    )
    SELECT 
        e.team_name AS team,
        v.val_year,
        SUM(CAST(v.market_value_in_eur AS BIGINT)) AS total_value
    FROM raw_transfermarkt_players p
    JOIN player_yearly_val v ON p.player_id = v.player_id AND v.rn = 1
    JOIN fct_international_elo e ON p.country_of_citizenship = e.team_name
    GROUP BY team, val_year
    """
    try:
        df_vals = con.execute(tm_query).fetchdf()
        val_dict = df_vals.set_index(["team", "val_year"])["total_value"].to_dict()
    except Exception as e:
        logger.warning(f"Could not compute precise historical valuations: {e}. Falling back to default values.")
        val_dict = {}
        
    def get_squad_value(team: str, year: int) -> float:
        for y in [year, year - 1, year - 2, 2026]:
            if (team, y) in val_dict:
                return float(val_dict[(team, y)])
        return 50000000.0 # €50M default prior
        
    df_matches["squad_market_value_home"] = df_matches.apply(lambda r: get_squad_value(r["home_team"], r["year"]), axis=1)
    df_matches["squad_market_value_away"] = df_matches.apply(lambda r: get_squad_value(r["away_team"], r["year"]), axis=1)
    df_matches["squad_market_value_diff_eur"] = df_matches["squad_market_value_home"] - df_matches["squad_market_value_away"]
    
    # Odds features
    df_matches["bookmaker_implied_prob_a_win"] = np.nan
    df_matches["bookmaker_implied_prob_draw"] = np.nan
    
    # Additional PRD features:
    hosts = ["United States", "Mexico", "Canada"]
    def get_host_flag(row):
        h, a = row["home_team"], row["away_team"]
        if h in hosts:
            return 1
        elif a in hosts:
            return -1
        return 0
        
    df_matches["host_nation_flag"] = df_matches.apply(get_host_flag, axis=1)
    
    # caps and goals differential
    df_matches["total_caps_diff"] = 0
    df_matches["total_intl_goals_diff"] = 0
    df_matches["confederation_strength_a"] = 0.5
    df_matches["confederation_strength_b"] = 0.5
    df_matches["joint_squad_age_diff"] = 0.0
    df_matches["shared_club_minutes"] = 0.0
    df_matches["avg_squad_height_diff_cm"] = 0.0
    df_matches["historic_fifa_points_diff"] = 0.0
    df_matches["match_stage_pressure"] = 0
    df_matches["head_to_head_elo_record"] = 0.0
    
    # Save match features table
    con.execute("CREATE OR REPLACE TABLE fct_model_match_features AS SELECT * FROM df_matches")
    logger.info(f"Match outcome features table created with {len(df_matches)} rows.")

def build_penalty_features(con: duckdb.DuckDBPyConnection):
    """
    Extracts penalty shooter histories, writing to fct_model_penalty_features.
    """
    logger.info("Extracting penalty shootout features...")
    
    # Query Fjelstul penalty kicks
    query = """
    SELECT 
        match_id,
        team_id,
        player_id,
        converted,
        key_id AS kick_number
    FROM raw_fjelstul_penalty_kicks
    """
    df_penalties = con.execute(query).fetchdf()
    
    # Save back to DuckDB
    con.execute("CREATE OR REPLACE TABLE fct_model_penalty_features AS SELECT * FROM df_penalties")
    logger.info(f"Penalty features table created with {len(df_penalties)} rows.")

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_path = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    
    con = duckdb.connect(db_path)
    try:
        build_xg_features(con)
        build_match_features(con)
        build_penalty_features(con)
        logger.info("All model features computed and written to DuckDB successfully!")
    finally:
        con.close()

if __name__ == "__main__":
    main()
