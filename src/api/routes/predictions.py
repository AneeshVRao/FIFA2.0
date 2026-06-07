import os
import json
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from src.api.schemas import (
    WinnerResponse, TeamStageProbability,
    MatchPredictionResponse, TeamRef, VenueRef, MatchProbabilities,
    ExpectedGoals, ScorelineProb, InfluenceFeatures, CustomMatchRequest,
    TeamsListResponse, TeamListItem, VenuesListResponse, VenueListItem,
    MatchesListResponse, MatchListItem
)
from src.api.database import get_db_connection
from src.simulation.dixon_coles import get_match_xg, build_scoreline_grid

router = APIRouter(prefix="/predictions", tags=["predictions"])

# Helper: Load groups and venues once to construct the static schedule
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TEAMS_JSON_PATH = os.path.join(BASE_DIR, "data", "wc_2026_teams.json")

def load_static_schedule() -> Dict[str, Dict[str, Any]]:
    """
    Constructs the exact 72 group stage matches dynamically in a deterministic order.
    Matches are indexed from 1 to 72.
    """
    schedule = {}
    if not os.path.exists(TEAMS_JSON_PATH):
        return schedule
    
    with open(TEAMS_JSON_PATH, "r") as f:
        teams_data = json.load(f)
        
    with get_db_connection() as conn:
        df_venues = conn.execute("SELECT * FROM dim_venues ORDER BY venue_id").fetchdf()
        venues = df_venues.to_dict(orient="records")
        
        df_teams = conn.execute("SELECT reep_team_id, team_name_canonical FROM dim_teams").fetchdf()
        team_id_map = {}
        for t in df_teams.to_dict(orient="records"):
            name = t["team_name_canonical"]
            tid = t["reep_team_id"]
            team_id_map[name] = tid
            if name.startswith("Cura"):
                team_id_map["Curaçao"] = tid
                team_id_map["Curacao"] = tid
                team_id_map["Curaao"] = tid
        # Special mapping overrides for team names
        team_id_map["USA"] = team_id_map.get("United States")

    venue_ids = [v["venue_id"] for v in venues]
    venue_map = {v["venue_id"]: v for v in venues}
    
    pairings = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
    match_num = 1
    venue_index = 0
    
    for gcode in sorted(teams_data["groups"].keys()):
        group_teams = teams_data["groups"][gcode]
        for idx_a, idx_b in pairings:
            team_a_data = group_teams[idx_a]
            team_b_data = group_teams[idx_b]
            
            t_a_name = team_a_data["name"]
            t_b_name = team_b_data["name"]
            
            # Map standard names
            t_a_canonical = "United States" if t_a_name == "USA" else ("Curaçao" if t_a_name in ["Curaçao", "Curacao", "Curaao"] else t_a_name)
            t_b_canonical = "United States" if t_b_name == "USA" else ("Curaçao" if t_b_name in ["Curaçao", "Curacao", "Curaao"] else t_b_name)
            
            t_a_id = team_id_map.get(t_a_canonical, f"tm_{t_a_canonical[:3].lower()}")
            t_b_id = team_id_map.get(t_b_canonical, f"tm_{t_b_canonical[:3].lower()}")
            
            vid = venue_ids[venue_index % len(venue_ids)]
            venue_index += 1
            
            schedule[str(match_num)] = {
                "match_id": f"match_{match_num}",
                "stage": "group",
                "group_code": gcode,
                "team_a_id": t_a_id,
                "team_a_name": t_a_canonical,
                "team_b_id": t_b_id,
                "team_b_name": t_b_canonical,
                "venue_id": vid,
                "venue_name": venue_map[vid]["stadium_name"],
                "altitude_m": float(venue_map[vid]["altitude_m"])
            }
            match_num += 1
            
    # Add knockout placeholders (73 - 104)
    knockout_stages = [
        # (MatchNum, LabelA, LabelB, StageName)
        *[(i, f"Winner/Runner Up Slot {i}", f"Winner/Runner Up Slot {i}", "r32") for i in range(73, 89)],
        *[(i, f"R32 Winner Slot {i}", f"R32 Winner Slot {i}", "r16") for i in range(89, 97)],
        *[(i, f"R16 Winner Slot {i}", f"R16 Winner Slot {i}", "quarterfinal") for i in range(97, 101)],
        *[(i, f"QF Winner Slot {i}", f"QF Winner Slot {i}", "semifinal") for i in range(101, 103)],
        (103, "SF 101 Loser", "SF 102 Loser", "third_place"),
        (104, "SF 101 Winner", "SF 102 Winner", "final")
    ]
    
    # We assign default venues dynamically to keep it structured
    for match_num, label_a, label_b, stage in knockout_stages:
        vid = venue_ids[venue_index % len(venue_ids)]
        venue_index += 1
        schedule[str(match_num)] = {
            "match_id": f"match_{match_num}",
            "stage": stage,
            "group_code": None,
            "team_a_id": f"slot_{match_num}_a",
            "team_a_name": label_a,
            "team_b_id": f"slot_{match_num}_b",
            "team_b_name": label_b,
            "venue_id": vid,
            "venue_name": venue_map[vid]["stadium_name"],
            "altitude_m": float(venue_map[vid]["altitude_m"])
        }
        
    return schedule

STATIC_SCHEDULE = load_static_schedule()

@router.get("/teams", response_model=TeamsListResponse)
async def get_teams():
    with get_db_connection() as conn:
        try:
            df = conn.execute("SELECT reep_team_id, team_name_canonical, group_code, is_host_nation, pretournament_elo, squad_market_value_eur, confederation FROM dim_teams ORDER BY team_name_canonical").fetchdf()
            teams = [TeamListItem(**row) for row in df.to_dict(orient="records")]
            return TeamsListResponse(teams=teams)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@router.get("/venues", response_model=VenuesListResponse)
async def get_venues():
    with get_db_connection() as conn:
        try:
            df = conn.execute("SELECT venue_id, stadium_name, city, host_nation, latitude, longitude, altitude_m, capacity FROM dim_venues ORDER BY stadium_name").fetchdf()
            venues = [VenueListItem(**row) for row in df.to_dict(orient="records")]
            return VenuesListResponse(venues=venues)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@router.get("/matches", response_model=MatchesListResponse)
async def get_matches():
    try:
        matches = []
        for m_num, m_info in sorted(STATIC_SCHEDULE.items(), key=lambda x: int(x[0])):
            matches.append(MatchListItem(
                match_id=m_info["match_id"],
                stage=m_info["stage"],
                group_code=m_info["group_code"],
                team_a_id=m_info["team_a_id"],
                team_a_name=m_info["team_a_name"],
                team_b_id=m_info["team_b_id"],
                team_b_name=m_info["team_b_name"],
                venue_id=m_info["venue_id"],
                venue_name=m_info["venue_name"],
                altitude_m=m_info["altitude_m"]
            ))
        return MatchesListResponse(matches=matches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate matches list: {str(e)}")

@router.get("/winner", response_model=WinnerResponse)
async def get_winner_probabilities():
    """
    Returns the simulated stage advancement probabilities for all teams,
    sorted by champion probability descending.
    """
    with get_db_connection() as conn:
        query = """
            SELECT 
                p.reep_team_id,
                t.team_name_canonical AS team_name,
                p.p_group_advance,
                p.p_r32,
                p.p_r16,
                p.p_qf,
                p.p_sf,
                p.p_final,
                p.p_champion
            FROM team_stage_probabilities p
            JOIN dim_teams t ON p.reep_team_id = t.reep_team_id
            ORDER BY p.p_champion DESC
        """
        try:
            df = conn.execute(query).fetchdf()
            teams_list = [TeamStageProbability(**row) for row in df.to_dict(orient="records")]
            return WinnerResponse(teams=teams_list)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@router.get("/match/{match_id}", response_model=MatchPredictionResponse)
async def get_match_prediction(match_id: str):
    """
    Fetches prediction info for a scheduled match.
    The match_id parameter should correspond to 'match_1' through 'match_104'.
    """
    match_num_str = match_id.replace("match_", "")
    if match_num_str not in STATIC_SCHEDULE:
        raise HTTPException(status_code=404, detail=f"Match ID '{match_id}' not found in schedule.")
        
    m_info = STATIC_SCHEDULE[match_num_str]
    team_a_id = m_info["team_a_id"]
    team_b_id = m_info["team_b_id"]
    
    # Check if matchup predictions are available in matchup_forecasts (based on team IDs)
    with get_db_connection() as conn:
        # Lexicographic swap check
        query = """
            SELECT * 
            FROM matchup_forecasts
            WHERE (team_a_id = ? AND team_b_id = ?) 
               OR (team_a_id = ? AND team_b_id = ?)
        """
        row = conn.execute(query, [team_a_id, team_b_id, team_b_id, team_a_id]).fetchone()
        
        # Resolve team details from dim_teams
        team_details = conn.execute(
            "SELECT reep_team_id, team_name_canonical, squad_market_value_eur FROM dim_teams WHERE reep_team_id IN (?, ?)",
            [team_a_id, team_b_id]
        ).fetchdf()
        
        team_map = {t["reep_team_id"]: t for t in team_details.to_dict(orient="records")}
        
        # Default features values
        elo_diff = 0.0
        val_diff = 0.0
        is_host_applied = team_a_id in ["T-83", "T-46", "T-12"]
        
        # Try to resolve Elo ratings
        elo_row = conn.execute(
            "SELECT reep_team_id, pretournament_elo FROM dim_teams WHERE reep_team_id IN (?, ?)",
            [team_a_id, team_b_id]
        ).fetchall()
        elo_map = {r[0]: r[1] for r in elo_row}
        
        if team_a_id in elo_map and team_b_id in elo_map:
            elo_diff = elo_map[team_a_id] - elo_map[team_b_id]
            
        if team_a_id in team_map and team_b_id in team_map:
            val_diff = float(team_map[team_a_id]["squad_market_value_eur"] - team_map[team_b_id]["squad_market_value_eur"])

        # Construct team references
        home_ref = TeamRef(id=team_a_id, name=m_info["team_a_name"])
        away_ref = TeamRef(id=team_b_id, name=m_info["team_b_name"])
        venue_ref = VenueRef(id=m_info["venue_id"], name=m_info["venue_name"], altitude_m=m_info["altitude_m"])
        
        influence = InfluenceFeatures(
            elo_differential=elo_diff,
            squad_value_diff_eur=val_diff,
            altitude_m=m_info["altitude_m"],
            host_advantage_applied=is_host_applied
        )

        if row:
            # Table columns: team_a_id, team_b_id, p_team_a_win, p_draw, p_team_b_win, team_a_xg, team_b_xg, most_likely_scorelines
            db_team_a, db_team_b, p_a, p_draw, p_b, xg_a, xg_b, scores_json, _ = row
            
            # Swapping check
            is_swapped = (db_team_a == team_b_id)
            
            p_home = p_b if is_swapped else p_a
            p_away = p_a if is_swapped else p_b
            xg_home = xg_b if is_swapped else xg_a
            xg_away = xg_a if is_swapped else xg_b
            
            scorelines_list = json.loads(scores_json)
            top_scorelines = []
            
            for s in scorelines_list:
                score = s["score"]
                if is_swapped:
                    # Invert scoreline e.g. '2-0' to '0-2'
                    parts = score.split("-")
                    score = f"{parts[1]}-{parts[0]}"
                top_scorelines.append(ScorelineProb(scoreline=score, probability=s["probability"]))
                
            return MatchPredictionResponse(
                match_id=match_id,
                stage=m_info["stage"],
                home_team=home_ref,
                away_team=away_ref,
                venue=venue_ref,
                probabilities=MatchProbabilities(home_win=p_home, draw=p_draw, away_win=p_away),
                expected_goals=ExpectedGoals(home_xg=xg_home, away_xg=xg_away),
                top_scorelines=top_scorelines,
                influence_features=influence
            )
        else:
            # If match predictions are not precomputed (e.g. custom matchups or empty slots)
            # compute standard Poisson/Dixon-Coles on the fly.
            # Default values:
            p_home, p_draw, p_away = 0.33, 0.34, 0.33
            xg_home, xg_away = 1.0, 1.0
            top_scorelines = [
                ScorelineProb(scoreline="1-1", probability=0.12),
                ScorelineProb(scoreline="1-0", probability=0.10),
                ScorelineProb(scoreline="0-1", probability=0.10)
            ]
            
            # If teams are actual valid team entities
            if team_a_id in elo_map and team_b_id in elo_map:
                lam, mu = get_match_xg(
                    elo_a=elo_map[team_a_id],
                    elo_b=elo_map[team_b_id],
                    is_host_a=team_a_id in ["T-83", "T-46", "T-12"],
                    is_host_b=team_b_id in ["T-83", "T-46", "T-12"],
                    venue_alt=m_info["altitude_m"],
                    native_alt_a=0.0, # fallback
                    native_alt_b=0.0,
                    travel_a_km=0.0,
                    travel_b_km=0.0,
                    rest_a=5.0,
                    rest_b=5.0
                )
                grid = build_scoreline_grid(lam, mu, rho=-0.13)
                xg_home, xg_away = lam, mu
                p_home = float(sum(grid[i, j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i > j))
                p_draw = float(sum(grid[i, i] for i in range(grid.shape[0])))
                p_away = float(sum(grid[i, j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i < j))
                
                # Fetch top scorelines
                scores_flat = []
                for i in range(grid.shape[0]):
                    for j in range(grid.shape[1]):
                        scores_flat.append((f"{i}-{j}", float(grid[i, j])))
                scores_flat.sort(key=lambda x: x[1], reverse=True)
                top_scorelines = [ScorelineProb(scoreline=s[0], probability=s[1]) for s in scores_flat[:5]]
                
            return MatchPredictionResponse(
                match_id=match_id,
                stage=m_info["stage"],
                home_team=home_ref,
                away_team=away_ref,
                venue=venue_ref,
                probabilities=MatchProbabilities(home_win=p_home, draw=p_draw, away_win=p_away),
                expected_goals=ExpectedGoals(home_xg=xg_home, away_xg=xg_away),
                top_scorelines=top_scorelines,
                influence_features=influence
            )

@router.post("/match/custom", response_model=MatchPredictionResponse)
async def generate_custom_prediction(req: CustomMatchRequest):
    """
    Generates a custom match prediction on the fly for any two team IDs
    at a selected venue. Executes Dixon-Coles parameters dynamically
    under a lexicographically sorted order for perfect swap symmetry.
    """
    # 1. Lexicographical sort to establish stable home/away baseline
    sorted_ids = sorted([req.team_a_id, req.team_b_id])
    sorted_a_id, sorted_b_id = sorted_ids[0], sorted_ids[1]
    is_swapped = (req.team_a_id != sorted_a_id)

    with get_db_connection() as conn:
        # Load team details in sorted order
        df_team_a = conn.execute("SELECT * FROM dim_teams WHERE reep_team_id = ?", [sorted_a_id]).fetchdf()
        df_team_b = conn.execute("SELECT * FROM dim_teams WHERE reep_team_id = ?", [sorted_b_id]).fetchdf()
        
        if df_team_a.empty or df_team_b.empty:
            raise HTTPException(status_code=404, detail="One or both team IDs could not be resolved.")
            
        team_a = df_team_a.to_dict(orient="records")[0]
        team_b = df_team_b.to_dict(orient="records")[0]
        
        # Load venue details
        df_venue = conn.execute("SELECT * FROM dim_venues WHERE venue_id = ?", [req.venue_id]).fetchdf()
        if df_venue.empty:
            raise HTTPException(status_code=404, detail="Selected venue ID not found.")
            
        venue = df_venue.to_dict(orient="records")[0]
        
        # Run Dixon-Coles expectations on the sorted baseline
        lam, mu = get_match_xg(
            elo_a=team_a["pretournament_elo"],
            elo_b=team_b["pretournament_elo"],
            is_host_a=team_a["reep_team_id"] in ["T-83", "T-46", "T-12"],
            is_host_b=team_b["reep_team_id"] in ["T-83", "T-46", "T-12"],
            venue_alt=float(venue["altitude_m"]),
            native_alt_a=0.0, # default
            native_alt_b=0.0,
            travel_a_km=0.0,
            travel_b_km=0.0,
            rest_a=5.0,
            rest_b=5.0
        )
        
        grid = build_scoreline_grid(lam, mu, rho=-0.13)
        p_home = float(sum(grid[i, j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i > j))
        p_draw = float(sum(grid[i, i] for i in range(grid.shape[0])))
        p_away = float(sum(grid[i, j] for i in range(grid.shape[0]) for j in range(grid.shape[1]) if i < j))
        
        scores_flat = []
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                scores_flat.append((f"{i}-{j}", float(grid[i, j])))
        scores_flat.sort(key=lambda x: x[1], reverse=True)
        top_scorelines = [ScorelineProb(scoreline=s[0], probability=s[1]) for s in scores_flat[:5]]
        
        # 2. Swap outputs if the queried order was different from sorted order
        if is_swapped:
            p_home, p_away = p_away, p_home
            lam, mu = mu, lam
            swapped_scorelines = []
            for s in top_scorelines:
                parts = s.scoreline.split("-")
                swapped_scorelines.append(ScorelineProb(
                    scoreline=f"{parts[1]}-{parts[0]}",
                    probability=s.probability
                ))
            top_scorelines = swapped_scorelines

        # Load queried home/away details for Response references
        df_queried_a = df_team_b if is_swapped else df_team_a
        df_queried_b = df_team_a if is_swapped else df_team_b
        q_a = df_queried_a.to_dict(orient="records")[0]
        q_b = df_queried_b.to_dict(orient="records")[0]

        elo_diff = q_a["pretournament_elo"] - q_b["pretournament_elo"]
        val_diff = float(q_a["squad_market_value_eur"] - q_b["squad_market_value_eur"])
        is_host_applied = q_a["reep_team_id"] in ["T-83", "T-46", "T-12"]
        
        home_ref = TeamRef(id=q_a["reep_team_id"], name=q_a["team_name_canonical"])
        away_ref = TeamRef(id=q_b["reep_team_id"], name=q_b["team_name_canonical"])
        venue_ref = VenueRef(id=venue["venue_id"], name=venue["stadium_name"], altitude_m=float(venue["altitude_m"]))
        
        influence = InfluenceFeatures(
            elo_differential=elo_diff,
            squad_value_diff_eur=val_diff,
            altitude_m=float(venue["altitude_m"]),
            host_advantage_applied=is_host_applied
        )
        
        return MatchPredictionResponse(
            match_id=None,
            stage=req.match_context,
            home_team=home_ref,
            away_team=away_ref,
            venue=venue_ref,
            probabilities=MatchProbabilities(home_win=p_home, draw=p_draw, away_win=p_away),
            expected_goals=ExpectedGoals(home_xg=lam, away_xg=mu),
            top_scorelines=top_scorelines,
            influence_features=influence
        )
