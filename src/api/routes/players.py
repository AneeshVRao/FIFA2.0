from fastapi import APIRouter, HTTPException, Query
from src.api.schemas import GoldenBootResponse, GoldenBootCandidate
from src.api.database import get_db_connection

router = APIRouter(prefix="/players", tags=["players"])

@router.get("/golden-boot", response_model=GoldenBootResponse)
async def get_golden_boot_leaderboard(limit: int = Query(20, ge=1, le=100)):
    """
    Returns the simulated Golden Boot ranking leaderboard.
    """
    with get_db_connection() as conn:
        query = """
            SELECT 
                g.reep_player_id,
                p.player_name_canonical AS player_name,
                t.team_name_canonical AS team_name,
                p.position AS position,
                p.international_caps AS caps,
                p.bayesian_penalty_conversion AS bayesian_penalty_conversion,
                g.mean_goals,
                g.p10_goals,
                g.p50_goals,
                g.p90_goals,
                g.p_golden_boot,
                g.expected_minutes
            FROM golden_boot_distribution g
            JOIN dim_players p ON g.reep_player_id = p.reep_player_id
            JOIN dim_teams t ON p.reep_team_id = t.reep_team_id
            ORDER BY g.p_golden_boot DESC
            LIMIT ?
        """
        try:
            df = conn.execute(query, [limit]).fetchdf()
            candidates = [GoldenBootCandidate(**row) for row in df.to_dict(orient="records")]
            return GoldenBootResponse(leaderboard=candidates)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
