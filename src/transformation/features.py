import os
import logging
import duckdb
import numpy as np
import pandas as pd
import ast
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("feature_engineering")

# Goal coordinates (for a standard 100x100 pitch representation)
GOAL_X = 100.0
GOAL_Y_LEFT = 36.8
GOAL_Y_RIGHT = 63.2
GOAL_Y_CENTER = 50.0

# Team name standardization dictionary
TEAM_NAME_MAP = {
    "usa": "United States",
    "united states": "United States",
    "cote d'ivoire": "Ivory Coast",
    "cote d’ivoire": "Ivory Coast",
    "côte d'ivoire": "Ivory Coast",
    "korea, south": "South Korea",
    "south korea": "South Korea",
    "korea republic": "South Korea",
    "trkiye": "Turkey",
    "türkiye": "Turkey",
    "turkey": "Turkey",
    "curacao": "Curacao",
    "curaçao": "Curacao",
    "curaao": "Curacao",
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "bosnia and herzegovina": "Bosnia and Herzegovina",
    "czech republic": "Czech Republic",
    "czechia": "Czech Republic",
    "dr congo": "DR Congo",
    "congo dr": "DR Congo",
    "democratic republic of the congo": "DR Congo",
}

# High-altitude countries native training elevations (metres)
NATIVE_ALTITUDES = {
    "bolivia": 3640.0,
    "ecuador": 2850.0,
    "colombia": 2640.0,
    "mexico": 2240.0,
    "peru": 1500.0,
    "south africa": 1700.0,
    "nepal": 1400.0,
    "switzerland": 540.0,
    "austria": 560.0,
}

# Regional/Confederation strengths based on historic Round-of-16 reach rates
CONFEDERATION_STRENGTHS = {
    "CONMEBOL": 0.65,
    "UEFA": 0.60,
    "CONCACAF": 0.30,
    "CAF": 0.20,
    "AFC": 0.15,
    "OFC": 0.10
}

# Match name mapping function
def map_team_name(name: str) -> str:
    if pd.isna(name):
        return "Unknown"
    n_clean = str(name).lower().strip()
    return TEAM_NAME_MAP.get(n_clean, name)

# Geographical coordinates lookup function
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
    
    # 1. Start with international results trace (joining raw_footballdata_results to get city and country)
    results_query = """
    SELECT 
        t.date,
        t.home_team,
        t.away_team,
        t.home_score,
        t.away_score,
        t.tournament,
        r.city,
        r.country,
        t.neutral,
        t.elo_home_before AS elo_home,
        t.elo_away_before AS elo_away,
        (t.elo_home_before - t.elo_away_before) AS elo_rating_diff
    FROM fct_international_elo_trace t
    JOIN raw_footballdata_results r ON t.date = r.date AND t.home_team = r.home_team AND t.away_team = r.away_team
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
    df_matches["date"] = pd.to_datetime(df_matches["date"])
    df_matches = df_matches.sort_values("date").reset_index(drop=True)
    df_matches["year"] = df_matches["date"].dt.year
    
    # 2. Load geographical country capital coordinates mapping
    logger.info("Loading country coordinates mapping...")
    df_caps = con.execute("SELECT name, latitude, longitude FROM raw_country_capitals").fetchdf()
    cap_coords = {}
    for idx, row in df_caps.iterrows():
        name_clean = str(row["name"]).lower().strip()
        cap_coords[name_clean] = (float(row["latitude"]), float(row["longitude"]))
        
    # Manual fallback mappings for missing/unaligned names (e.g. UK nations, typos)
    manual_coords = {
        "england": (51.5074, -0.1278),
        "scotland": (55.9533, -3.1883),
        "wales": (51.4816, -3.1791),
        "northern ireland": (54.5973, -5.9301),
        "republic of ireland": (53.3498, -6.2603),
        "ivory coast": (6.8276, -5.2893),
        "cote d'ivoire": (6.8276, -5.2893),
        "south korea": (37.5665, 126.9780),
        "korea republic": (37.5665, 126.9780),
        "usa": (38.9072, -77.0369),
        "united states": (38.9072, -77.0369),
        "dr congo": (-4.4419, 15.2663),
        "democratic republic of the congo": (-4.4419, 15.2663),
        "cape verde": (14.9315, -23.5125),
        "curacao": (12.1696, -68.9900),
        "curaçao": (12.1696, -68.9900),
        "curaao": (12.1696, -68.9900),
        "czech republic": (50.0755, 14.4378),
        "czechia": (50.0755, 14.4378),
        "bosnia and herzegovina": (43.8563, 18.4131),
        "turkey": (39.9334, 32.8597),
        "türkiye": (39.9334, 32.8597),
    }
    
    def get_coords(country_name: str) -> Tuple[float, float]:
        if pd.isna(country_name):
            return 39.8283, -98.5795 # Default center of US
        n_clean = str(country_name).lower().strip()
        if n_clean in manual_coords:
            return manual_coords[n_clean]
        return cap_coords.get(n_clean, (39.8283, -98.5795))
        
    def get_altitude(country_name: str) -> float:
        n_clean = str(country_name).lower().strip()
        return float(NATIVE_ALTITUDES.get(n_clean, 100.0))
        
    # 3. Load Transfermarkt squad-level attributes dynamically from raw tables
    logger.info("Aggregating player attributes from Transfermarkt...")
    
    # Map country name maps inside SQL using CASE Statement
    tm_players_query = """
    SELECT 
        CASE 
            WHEN LOWER(TRIM(country_of_citizenship)) = 'united states' THEN 'United States'
            WHEN LOWER(TRIM(country_of_citizenship)) = 'cote d''ivoire' THEN 'Ivory Coast'
            WHEN LOWER(TRIM(country_of_citizenship)) = 'korea, south' THEN 'South Korea'
            WHEN LOWER(TRIM(country_of_citizenship)) = 'trkiye' THEN 'Turkey'
            WHEN LOWER(TRIM(country_of_citizenship)) = 'türkiye' THEN 'Turkey'
            WHEN LOWER(TRIM(country_of_citizenship)) = 'turkey' THEN 'Turkey'
            WHEN LOWER(TRIM(country_of_citizenship)) = 'bosnia-herzegovina' THEN 'Bosnia and Herzegovina'
            ELSE country_of_citizenship 
        END AS team_mapped,
        SUM(COALESCE(international_caps, 0)) AS total_caps,
        SUM(COALESCE(international_goals, 0)) AS total_goals,
        AVG(2026 - EXTRACT(year FROM CAST(date_of_birth AS DATE))) AS avg_age,
        AVG(height_in_cm) AS avg_height
    FROM raw_transfermarkt_players
    WHERE country_of_citizenship IS NOT NULL
    GROUP BY team_mapped
    """
    df_tm_squads = con.execute(tm_players_query).fetchdf()
    caps_dict = df_tm_squads.set_index("team_mapped")["total_caps"].to_dict()
    goals_dict = df_tm_squads.set_index("team_mapped")["total_goals"].to_dict()
    age_dict = df_tm_squads.set_index("team_mapped")["avg_age"].to_dict()
    height_dict = df_tm_squads.set_index("team_mapped")["avg_height"].to_dict()
    
    # Aggregated yearly valuation dictionary
    tm_valuation_query = """
    WITH player_yearly_val AS (
        SELECT 
            player_id,
            EXTRACT(year FROM CAST(date AS DATE)) AS val_year,
            market_value_in_eur,
            ROW_NUMBER() OVER (PARTITION BY player_id, EXTRACT(year FROM CAST(date AS DATE)) ORDER BY date DESC) as rn
        FROM raw_transfermarkt_player_valuations
    )
    SELECT 
        CASE 
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'united states' THEN 'United States'
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'cote d''ivoire' THEN 'Ivory Coast'
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'korea, south' THEN 'South Korea'
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'trkiye' THEN 'Turkey'
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'türkiye' THEN 'Turkey'
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'turkey' THEN 'Turkey'
            WHEN LOWER(TRIM(p.country_of_citizenship)) = 'bosnia-herzegovina' THEN 'Bosnia and Herzegovina'
            ELSE p.country_of_citizenship 
        END AS team_mapped,
        v.val_year,
        SUM(CAST(v.market_value_in_eur AS BIGINT)) AS total_value
    FROM raw_transfermarkt_players p
    JOIN player_yearly_val v ON p.player_id = v.player_id AND v.rn = 1
    GROUP BY team_mapped, val_year
    """
    try:
        df_vals = con.execute(tm_valuation_query).fetchdf()
        val_dict = df_vals.set_index(["team_mapped", "val_year"])["total_value"].to_dict()
    except Exception as e:
        logger.warning(f"Could not load Transfermarkt yearly valuations: {e}")
        val_dict = {}
        
    def get_squad_value(team: str, year: int) -> float:
        mapped_team = TEAM_NAME_MAP.get(team.lower().strip(), team)
        for y in [year, year - 1, year - 2, 2026]:
            if (mapped_team, y) in val_dict:
                return float(val_dict[(mapped_team, y)])
        return 50000000.0 # €50M default prior
        
    # 4. Tracing prior match locations chronologically to compute real travel, tz, rest days, and H2H
    logger.info("Computing travel distance, timezone crossings, rest day asymmetry, and H2H records chronologically...")
    
    last_match = {} # team -> (date, coords, timezone)
    h2h_history = {} # (team1, team2) -> list of winners
    
    travel_a = []
    travel_b = []
    tz_cross_diff = []
    rest_diff = []
    alt_diff = []
    h2h_records = []
    
    for idx, row in df_matches.iterrows():
        date = row["date"]
        home = row["home_team"]
        away = row["away_team"]
        country = row["country"]
        
        # Match venue coordinates and timezone
        venue_coords = get_coords(country)
        venue_tz = round(venue_coords[1] / 15.0)
        venue_alt = get_altitude(country)
        
        # Team A (Home) prior state
        t_a_travel = 0.0
        t_a_tz_cross = 0
        t_a_rest = 30.0
        if home in last_match:
            prev_date, prev_coords, prev_tz = last_match[home]
            days = (date - prev_date).days
            if days <= 30:
                t_a_rest = float(days)
                t_a_travel = haversine_distance(prev_coords[0], prev_coords[1], venue_coords[0], venue_coords[1])
                t_a_tz_cross = abs(venue_tz - prev_tz)
                
        # Team B (Away) prior state
        t_b_travel = 0.0
        t_b_tz_cross = 0
        t_b_rest = 30.0
        if away in last_match:
            prev_date, prev_coords, prev_tz = last_match[away]
            days = (date - prev_date).days
            if days <= 30:
                t_b_rest = float(days)
                t_b_travel = haversine_distance(prev_coords[0], prev_coords[1], venue_coords[0], venue_coords[1])
                t_b_tz_cross = abs(venue_tz - prev_tz)
                
        # Differentials
        travel_a.append(t_a_travel)
        travel_b.append(t_b_travel)
        tz_cross_diff.append(float(t_a_tz_cross - t_b_tz_cross))
        rest_diff.append(float(t_a_rest - t_b_rest))
        
        # Altitude differential
        native_a = get_altitude(home)
        native_b = get_altitude(away)
        alt_diff_a = max(0.0, venue_alt - native_a)
        alt_diff_b = max(0.0, venue_alt - native_b)
        alt_diff.append(float(alt_diff_a - alt_diff_b))
        
        # H2H calculations
        key = tuple(sorted([home, away]))
        prior_matches = h2h_history.get(key, [])
        wins_a = sum(1 for w in prior_matches if w == home)
        wins_b = sum(1 for w in prior_matches if w == away)
        h2h_val = (wins_a - wins_b) / (len(prior_matches) + 1.0)
        h2h_records.append(h2h_val)
        
        # Update H2H history
        winner = None
        if row["home_score"] > row["away_score"]:
            winner = home
        elif row["home_score"] < row["away_score"]:
            winner = away
        h2h_history.setdefault(key, []).append(winner)
        
        # Update last match state
        last_match[home] = (date, venue_coords, venue_tz)
        last_match[away] = (date, venue_coords, venue_tz)
        
    df_matches["team_a_travel_km"] = travel_a
    df_matches["team_b_travel_km"] = travel_b
    df_matches["timezone_crossings_diff"] = tz_cross_diff
    df_matches["rest_day_asymmetry"] = rest_diff
    df_matches["altitude_diff_m"] = alt_diff
    df_matches["head_to_head_elo_record"] = h2h_records
    
    # 5. Populate rest day / market values
    df_matches["squad_market_value_home"] = df_matches.apply(lambda r: get_squad_value(r["home_team"], r["year"]), axis=1)
    df_matches["squad_market_value_away"] = df_matches.apply(lambda r: get_squad_value(r["away_team"], r["year"]), axis=1)
    df_matches["squad_market_value_diff_eur"] = df_matches["squad_market_value_home"] - df_matches["squad_market_value_away"]
    
    # Odds features (placeholder or loaded from 2022)
    df_matches["bookmaker_implied_prob_a_win"] = np.nan
    df_matches["bookmaker_implied_prob_draw"] = np.nan
    
    # Host flags
    hosts = ["United States", "Mexico", "Canada"]
    def get_host_flag(row):
        h, a = row["home_team"], row["away_team"]
        if h in hosts:
            return 1
        elif a in hosts:
            return -1
        return 0
    df_matches["host_nation_flag"] = df_matches.apply(get_host_flag, axis=1)
    
    # 6. Transfermarkt age, height, and caps differentials
    logger.info("Computing player aggregation differentials for each match...")
    caps_diff = []
    goals_diff = []
    age_diff = []
    height_diff = []
    conf_strength_a = []
    conf_strength_b = []
    
    # Mapping for confederations of major nations
    confederation_map = {
        "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Uruguay": "CONMEBOL", "Colombia": "CONMEBOL", 
        "Ecuador": "CONMEBOL", "Peru": "CONMEBOL", "Chile": "CONMEBOL", "Venezuela": "CONMEBOL", 
        "Paraguay": "CONMEBOL", "Bolivia": "CONMEBOL",
        "United States": "CONCACAF", "Mexico": "CONCACAF", "Canada": "CONCACAF", "Jamaica": "CONCACAF", 
        "Costa Rica": "CONCACAF", "Honduras": "CONCACAF", "Panama": "CONCACAF", "El Salvador": "CONCACAF", 
        "Trinidad and Tobago": "CONCACAF", "Haiti": "CONCACAF", "Curacao": "CONCACAF",
        "New Zealand": "OFC",
        "Saudi Arabia": "AFC", "Japan": "AFC", "South Korea": "AFC", "Iran": "AFC", "Australia": "AFC", 
        "Iraq": "AFC", "Jordan": "AFC", "Oman": "AFC", "Uzbekistan": "AFC", "United Arab Emirates": "AFC", 
        "Qatar": "AFC", "China": "AFC", "Indonesia": "AFC", "North Korea": "AFC", "Kyrgyzstan": "AFC", 
        "Palestine": "AFC", "Kuwait": "AFC", "Bahrain": "AFC",
        "Egypt": "CAF", "Senegal": "CAF", "Morocco": "CAF", "Algeria": "CAF", "Tunisia": "CAF", 
        "Nigeria": "CAF", "Cameroon": "CAF", "Mali": "CAF", "Ivory Coast": "CAF", "Ghana": "CAF", 
        "South Africa": "CAF", "DR Congo": "CAF", "Democratic Republic of the Congo": "CAF", 
        "Angola": "CAF", "Cape Verde": "CAF", "Guinea": "CAF", "Burkina Faso": "CAF", 
        "Equatorial Guinea": "CAF", "Zambia": "CAF", "Uganda": "CAF"
    }
    
    for idx, row in df_matches.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        
        home_mapped = TEAM_NAME_MAP.get(home.lower().strip(), home)
        away_mapped = TEAM_NAME_MAP.get(away.lower().strip(), away)
        
        # Caps & Goals
        cap_a = caps_dict.get(home_mapped, 350.0)
        cap_b = caps_dict.get(away_mapped, 350.0)
        caps_diff.append(float(cap_a - cap_b))
        
        goal_a = goals_dict.get(home_mapped, 50.0)
        goal_b = goals_dict.get(away_mapped, 50.0)
        goals_diff.append(float(goal_a - goal_b))
        
        # Age & Height
        age_a = age_dict.get(home_mapped, 26.5)
        age_b = age_dict.get(away_mapped, 26.5)
        age_diff.append(float(age_a - age_b))
        
        h_a = height_dict.get(home_mapped, 181.5)
        h_b = height_dict.get(away_mapped, 181.5)
        height_diff.append(float(h_a - h_b))
        
        # Confederation Strengths
        conf_a = confederation_map.get(home_mapped, "UEFA")
        conf_b = confederation_map.get(away_mapped, "UEFA")
        conf_strength_a.append(CONFEDERATION_STRENGTHS.get(conf_a, 0.60))
        conf_strength_b.append(CONFEDERATION_STRENGTHS.get(conf_b, 0.60))
        
    df_matches["total_caps_diff"] = caps_diff
    df_matches["total_intl_goals_diff"] = goals_diff
    df_matches["joint_squad_age_diff"] = age_diff
    df_matches["avg_squad_height_diff_cm"] = height_diff
    df_matches["confederation_strength_a"] = conf_strength_a
    df_matches["confederation_strength_b"] = conf_strength_b
    df_matches["shared_club_minutes"] = 0.0 # Bypassed in isolation
    df_matches["historic_fifa_points_diff"] = df_matches["elo_rating_diff"]
    df_matches["match_stage_pressure"] = df_matches["tournament"].apply(lambda t: 5 if "world cup" in str(t).lower() else 0)
    
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
