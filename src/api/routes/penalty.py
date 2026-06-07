import numpy as np
from fastapi import APIRouter, HTTPException
from src.api.schemas import PenaltyRequest, PenaltyResponse, PenaltyRosters, PlayerPenaltyPrior, PenaltyKickOutcome
from src.api.database import get_db_connection
from src.simulation.shootout_sim import get_shootout_roster, simulate_shootout

router = APIRouter(prefix="/predictions", tags=["penalty"])

@router.post("/penalty", response_model=PenaltyResponse)
async def simulate_shootout_endpoint(req: PenaltyRequest):
    """
    Resolves team rosters from dim_players, runs a Monte Carlo simulation
    of shootout outcomes to estimate win percentages, and returns a sample timeline.
    """
    with get_db_connection() as conn:
        # Load players for Team A
        df_players_a = conn.execute(
            "SELECT * FROM dim_players WHERE reep_team_id = ?", [req.team_a_id]
        ).fetchdf()
        # Load players for Team B
        df_players_b = conn.execute(
            "SELECT * FROM dim_players WHERE reep_team_id = ?", [req.team_b_id]
        ).fetchdf()
        
        # Load team canonical names
        team_a_name = conn.execute(
            "SELECT team_name_canonical FROM dim_teams WHERE reep_team_id = ?", [req.team_a_id]
        ).fetchone()
        team_b_name = conn.execute(
            "SELECT team_name_canonical FROM dim_teams WHERE reep_team_id = ?", [req.team_b_id]
        ).fetchone()

    if df_players_a.empty or df_players_b.empty:
        raise HTTPException(status_code=404, detail="One or both team IDs could not be resolved.")
        
    t_a_name = team_a_name[0] if team_a_name else "Team A"
    t_b_name = team_b_name[0] if team_b_name else "Team B"

    # Format players as dictionary lists
    players_a = df_players_a.to_dict(orient="records")
    players_b = df_players_b.to_dict(orient="records")

    # Get shootout rosters
    gk_a, takers_a = get_shootout_roster(players_a)
    gk_b, takers_b = get_shootout_roster(players_b)

    roster_a_sim = (gk_a, takers_a)
    roster_b_sim = (gk_b, takers_b)

    # 1. Run Monte Carlo simulations for Win %
    wins_a = 0
    for _ in range(req.n_simulations):
        winner, _ = simulate_shootout(t_a_name, t_b_name, roster_a_sim, roster_b_sim)
        if winner == t_a_name:
            wins_a += 1
            
    p_win_a = float(wins_a / req.n_simulations)
    p_win_b = 1.0 - p_win_a

    # 2. Run a single shootout to retrieve a sample timeline
    _, log = simulate_shootout(t_a_name, t_b_name, roster_a_sim, roster_b_sim)
    
    sample_timeline = []
    for idx, kick in enumerate(log):
        sample_timeline.append(PenaltyKickOutcome(
            kick_number=kick["round"],
            team=kick["team"],
            taker=kick["taker"],
            result="scored" if kick["outcome"] == "goal" else "missed"
        ))

    # Format rosters response
    roster_resp_a = [PlayerPenaltyPrior(
        player_name=p["player_name_canonical"],
        pos=p["position"],
        conversion_prior=p["bayesian_penalty_conversion"]
    ) for p in takers_a[:5]]
    # include goalkeeper
    roster_resp_a.append(PlayerPenaltyPrior(
        player_name=gk_a["player_name_canonical"],
        pos=gk_a["position"],
        conversion_prior=gk_a["bayesian_penalty_conversion"]
    ))

    roster_resp_b = [PlayerPenaltyPrior(
        player_name=p["player_name_canonical"],
        pos=p["position"],
        conversion_prior=p["bayesian_penalty_conversion"]
    ) for p in takers_b[:5]]
    roster_resp_b.append(PlayerPenaltyPrior(
        player_name=gk_b["player_name_canonical"],
        pos=gk_b["position"],
        conversion_prior=gk_b["bayesian_penalty_conversion"]
    ))

    rosters = PenaltyRosters(team_a=roster_resp_a, team_b=roster_resp_b)

    return PenaltyResponse(
        win_probabilities={
            "team_a": p_win_a,
            "team_b": p_win_b
        },
        rosters=rosters,
        sample_kick_sequence=sample_timeline
    )
