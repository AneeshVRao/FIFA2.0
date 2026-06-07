from fastapi import APIRouter, HTTPException
from src.api.schemas import TeamStageProbsResponse, StageProjections, GroupStandingsDistribution
from src.api.database import get_db_connection

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("/{team_id}/stage-probs", response_model=TeamStageProbsResponse)
async def get_team_stage_probabilities(team_id: str):
    """
    Returns simulated stage probabilities and group standings finish distributions
    for a specific team.
    """
    with get_db_connection() as conn:
        # Query team_stage_probabilities
        query_stage = """
            SELECT 
                p.reep_team_id,
                t.team_name_canonical AS team_name,
                p.p_group_advance AS group_advance,
                p.p_r32 AS r32,
                p.p_r16 AS r16,
                p.p_qf AS quarterfinal,
                p.p_sf AS semifinal,
                p.p_final AS final,
                p.p_champion AS champion
            FROM team_stage_probabilities p
            JOIN dim_teams t ON p.reep_team_id = t.reep_team_id
            WHERE p.reep_team_id = ?
        """
        row_stage = conn.execute(query_stage, [team_id]).fetchone()
        
        # Query group_table_distributions
        query_group = """
            SELECT 
                p_1st,
                p_2nd,
                p_3rd_advance,
                p_4th,
                p_3rd
            FROM group_table_distributions
            WHERE reep_team_id = ?
        """
        row_group = conn.execute(query_group, [team_id]).fetchone()

    if not row_stage or not row_group:
        raise HTTPException(status_code=404, detail=f"Team ID '{team_id}' not found in predictions tables.")

    # Parse stage probabilities
    (
        reep_team_id,
        team_name,
        group_advance,
        r32,
        r16,
        qf,
        sf,
        final,
        champion
    ) = row_stage

    stages = StageProjections(
        group_advance=group_advance,
        r32=r32,
        r16=r16,
        quarterfinal=qf,
        semifinal=sf,
        final=final,
        champion=champion
    )

    # Parse group Standing probabilities
    p_1st, p_2nd, p_3rd_advance, p_4th, p_3rd = row_group
    eliminated = float(1.0 - (p_1st + p_2nd + p_3rd_advance))
    # Bound check
    eliminated = max(0.0, min(1.0, eliminated))

    # Pydantic populates aliases so we match exact 1st, 2nd, etc. keys
    group_dist = GroupStandingsDistribution(
        **{
            "1st": p_1st,
            "2nd": p_2nd,
            "3rd_advance": p_3rd_advance,
            "eliminated": eliminated
        }
    )

    return TeamStageProbsResponse(
        reep_team_id=reep_team_id,
        team_name=team_name,
        stage_probabilities=stages,
        group_finish_distribution=group_dist
    )
