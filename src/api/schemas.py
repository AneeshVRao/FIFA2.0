from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List, Dict, Optional

class ResponseMetadata(BaseModel):
    model_version: str = "1.0.0"
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    prediction_freeze_date: str = "2026-06-06"
    warning_disclaimer: str = (
        "📊 PRE-TOURNAMENT FORECAST: ALL FILED MATCHES AND PROBABILITIES "
        "ARE FIXED BEFORE THE OPENER."
    )

class BaseResponseModel(BaseModel):
    meta: ResponseMetadata = ResponseMetadata()

# 1. Winner Endpoint Schemas
class TeamStageProbability(BaseModel):
    reep_team_id: str
    team_name: str
    confederation: str
    p_group_advance: float
    p_r32: float
    p_r16: float
    p_qf: float
    p_sf: float
    p_final: float
    p_champion: float

class WinnerResponse(BaseResponseModel):
    teams: List[TeamStageProbability]

# 2. Match Prediction Schemas
class TeamRef(BaseModel):
    id: str
    name: str

class VenueRef(BaseModel):
    id: str
    name: str
    altitude_m: float

class MatchProbabilities(BaseModel):
    home_win: float
    draw: float
    away_win: float

class ExpectedGoals(BaseModel):
    home_xg: float
    away_xg: float

class ScorelineProb(BaseModel):
    scoreline: str
    probability: float

class InfluenceFeatures(BaseModel):
    elo_differential: float
    squad_value_diff_eur: float
    altitude_m: float
    travel_distance_km: float = 0.0
    host_advantage_applied: bool

class MatchPredictionResponse(BaseResponseModel):
    match_id: Optional[str] = None
    stage: str
    home_team: TeamRef
    away_team: TeamRef
    venue: VenueRef
    probabilities: MatchProbabilities
    expected_goals: ExpectedGoals
    top_scorelines: List[ScorelineProb]
    influence_features: InfluenceFeatures

# 3. Custom Match Request Schema
class CustomMatchRequest(BaseModel):
    team_a_id: str
    team_b_id: str
    venue_id: str
    match_context: str = "group"  # e.g., group, r32, r16, qf, sf, final

# 4. xG Prediction Schemas
class XGRequest(BaseModel):
    shot_x: float = Field(..., ge=0.0, le=100.0)
    shot_y: float = Field(..., ge=0.0, le=100.0)
    situation: str = "open_play"  # open_play, free_kick, corner, penalty
    body_part: str = "right_foot"  # right_foot, left_foot, head
    defenders_in_cone: Optional[int] = 0
    defensive_pressure_m: Optional[float] = 3.0

class DerivedSpatialMetrics(BaseModel):
    distance_to_goal_m: float
    angle_to_goal_deg: float

class SHAPContribution(BaseModel):
    feature: str
    shap_value: float

class XGResponse(BaseResponseModel):
    xg_value: float
    shot_danger_class: str  # low, medium, high, extreme
    derived_metrics: DerivedSpatialMetrics
    feature_shap_attribution: List[SHAPContribution]

# 5. Penalty Shootout Schemas
class PenaltyRequest(BaseModel):
    team_a_id: str
    team_b_id: str
    n_simulations: int = Field(10000, ge=100, le=100000)

class PlayerPenaltyPrior(BaseModel):
    player_name: str
    pos: str
    conversion_prior: float

class PenaltyRosters(BaseModel):
    team_a: List[PlayerPenaltyPrior]
    team_b: List[PlayerPenaltyPrior]

class PenaltyKickOutcome(BaseModel):
    kick_number: int
    team: str
    taker: str
    result: str  # scored, saved, missed

class PenaltyResponse(BaseResponseModel):
    win_probabilities: Dict[str, float]
    rosters: PenaltyRosters
    sample_kick_sequence: List[PenaltyKickOutcome]

# 6. Golden Boot Schemas
class GoldenBootCandidate(BaseModel):
    reep_player_id: str
    player_name: str
    team_name: str
    position: str = "Unknown"
    caps: int = 0
    bayesian_penalty_conversion: float = 0.0
    mean_goals: float
    p50_goals: float
    p90_goals: float
    p_golden_boot: float
    expected_minutes: float

class GoldenBootResponse(BaseResponseModel):
    leaderboard: List[GoldenBootCandidate]

# 7. Team Projections Schemas
class StageProjections(BaseModel):
    group_advance: float
    r32: float
    r16: float
    quarterfinal: float
    semifinal: float
    final: float
    champion: float

class GroupStandingsDistribution(BaseModel):
    first: float = Field(..., alias="1st")
    second: float = Field(..., alias="2nd")
    third_advance: float = Field(..., alias="3rd_advance")
    eliminated: float = Field(..., alias="eliminated")

    model_config = ConfigDict(populate_by_name=True)

class TeamStageProbsResponse(BaseResponseModel):
    reep_team_id: str
    team_name: str
    stage_probabilities: StageProjections
    group_finish_distribution: GroupStandingsDistribution

# 8. Health Status Schemas
class ModelLoadingStatus(BaseModel):
    match_outcome_model: str
    xg_model: str
    penalty_shootout_model: str

class HealthResponse(BaseModel):
    status: str
    database_connection: str
    models_ready: ModelLoadingStatus
    simulation_status: str
    prediction_freeze_date: str = "2026-06-06"

# 9. List Data Schemas
class TeamListItem(BaseModel):
    reep_team_id: str
    team_name_canonical: str
    group_code: Optional[str]
    is_host_nation: bool
    pretournament_elo: float
    squad_market_value_eur: float
    confederation: str

class TeamsListResponse(BaseResponseModel):
    teams: List[TeamListItem]

class VenueListItem(BaseModel):
    venue_id: str
    stadium_name: str
    city: str
    host_nation: str
    latitude: float
    longitude: float
    altitude_m: float
    capacity: int

class VenuesListResponse(BaseResponseModel):
    venues: List[VenueListItem]

class MatchListItem(BaseModel):
    match_id: str
    stage: str
    group_code: Optional[str] = None
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    venue_id: str
    venue_name: str
    altitude_m: float
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    went_to_extra_time: Optional[bool] = None
    went_to_penalties: Optional[bool] = None
    penalty_winner: Optional[str] = None

class MatchesListResponse(BaseResponseModel):
    matches: List[MatchListItem]

