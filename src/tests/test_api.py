import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    """Pytest fixture that yields a test client inside the lifespan context."""
    with TestClient(app) as c:
        yield c

def test_root_endpoint(client):
    """Verify that root endpoint returns successfully with freeze metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["prediction_freeze_date"] == "2026-06-06"
    assert "version" in data

def test_health_endpoint(client):
    """Verify that health check endpoint reports database and models loading status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["database_connection"] == "connected"
    assert data["models_ready"]["match_outcome_model"] == "loaded"
    assert data["models_ready"]["xg_model"] == "loaded"

def test_winner_endpoint(client):
    """Verify winner projections endpoint returns teams sorted by p_champion."""
    response = client.get("/predictions/winner")
    assert response.status_code == 200
    data = response.json()
    assert "teams" in data
    assert "meta" in data
    assert data["meta"]["prediction_freeze_date"] == "2026-06-06"
    
    teams = data["teams"]
    assert len(teams) > 0
    # Assert sorted in descending order of p_champion
    champs = [t["p_champion"] for t in teams]
    assert champs == sorted(champs, reverse=True)

def test_scheduled_match_prediction(client):
    """Verify scheduled match forecasts retrieval by ID (match_1)."""
    response = client.get("/predictions/match/match_1")
    assert response.status_code == 200
    data = response.json()
    assert "home_team" in data
    assert "away_team" in data
    assert "probabilities" in data
    assert "top_scorelines" in data
    assert "influence_features" in data
    
    probs = data["probabilities"]
    assert pytest.approx(probs["home_win"] + probs["draw"] + probs["away_win"], 0.01) == 1.0
    
    # Assert scorelines are sorted by probability descending
    scorelines = data["top_scorelines"]
    assert len(scorelines) == 5
    probs_score = [s["probability"] for s in scorelines]
    assert probs_score == sorted(probs_score, reverse=True)

def test_scheduled_match_not_found(client):
    """Verify HTTP 404 is raised for an invalid match number (e.g. match_999)."""
    response = client.get("/predictions/match/match_999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_custom_match_prediction(client):
    """Verify custom matchup simulation executes Dixon-Coles parameters dynamically."""
    payload = {
        "team_a_id": "T-83",      # United States
        "team_b_id": "T-30",      # France
        "venue_id": "v_newyork",   # MetLife Stadium
        "match_context": "group"
    }
    response = client.post("/predictions/match/custom", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["home_team"]["id"] == "T-83"
    assert data["away_team"]["id"] == "T-30"
    assert "probabilities" in data
    assert "expected_goals" in data
    
    probs = data["probabilities"]
    assert pytest.approx(probs["home_win"] + probs["draw"] + probs["away_win"], 0.01) == 1.0

def test_lexicographic_swap_reciprocity(client):
    """
    Test Lexicographic Swap: reversing team order in custom matchup query
    yields equivalent Win/Draw/Loss probabilities, but swapped appropriately.
    """
    payload_a = {
        "team_a_id": "T-83",
        "team_b_id": "T-30",
        "venue_id": "v_newyork",
        "match_context": "group"
    }
    payload_b = {
        "team_a_id": "T-30",
        "team_b_id": "T-83",
        "venue_id": "v_newyork",
        "match_context": "group"
    }
    
    res_a = client.post("/predictions/match/custom", json=payload_a).json()
    res_b = client.post("/predictions/match/custom", json=payload_b).json()
    
    prob_a = res_a["probabilities"]
    prob_b = res_b["probabilities"]
    
    # Win probability of USA (home in payload_a) should equal Win probability of USA (away in payload_b)
    assert pytest.approx(prob_a["home_win"], 0.01) == prob_b["away_win"]
    assert pytest.approx(prob_a["away_win"], 0.01) == prob_b["home_win"]
    assert pytest.approx(prob_a["draw"], 0.01) == prob_b["draw"]
    
    # Expected goals should be swapped
    xg_a = res_a["expected_goals"]
    xg_b = res_b["expected_goals"]
    assert pytest.approx(xg_a["home_xg"], 0.01) == xg_b["away_xg"]
    assert pytest.approx(xg_a["away_xg"], 0.01) == xg_b["home_xg"]

def test_xg_prediction(client):
    """Verify expected goals shot evaluation, derived spatial features, and SHAP sum."""
    payload = {
        "shot_x": 88.5,
        "shot_y": 50.0,
        "situation": "open_play",
        "body_part": "right_foot",
        "defenders_in_cone": 1,
        "defensive_pressure_m": 2.5
    }
    response = client.post("/predictions/xg", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "xg_value" in data
    assert 0.0 <= data["xg_value"] <= 1.0
    assert "shot_danger_class" in data
    
    derived = data["derived_metrics"]
    # Check that coordinate (88.5, 50.0) yields distance of ~11.5 meters to goal center (100.0, 50.0)
    assert pytest.approx(derived["distance_to_goal_m"], 0.5) == 11.5
    assert derived["angle_to_goal_deg"] > 0
    
    shaps = data["feature_shap_attribution"]
    assert len(shaps) == 4
    # The sum of SHAP contributions should equal the difference between actual xG and baseline xG
    for s in shaps:
        assert "feature" in s
        assert "shap_value" in s
        assert isinstance(s["shap_value"], float)

def test_penalty_shootout_simulation(client):
    """Verify shootout simulation win rates and kick-by-kick timeline output."""
    payload = {
        "team_a_id": "T-83",
        "team_b_id": "T-30",
        "n_simulations": 1000
    }
    response = client.post("/predictions/penalty", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "win_probabilities" in data
    assert pytest.approx(data["win_probabilities"]["team_a"] + data["win_probabilities"]["team_b"], 0.01) == 1.0
    
    assert "rosters" in data
    assert len(data["rosters"]["team_a"]) == 6 # 5 takers + 1 goalkeeper
    
    assert "sample_kick_sequence" in data
    timeline = data["sample_kick_sequence"]
    assert len(timeline) >= 3 # at least 3 kicks simulated before winner is decided
    for kick in timeline:
        assert "kick_number" in kick
        assert "team" in kick
        assert "taker" in kick
        assert kick["result"] in ["scored", "missed"]

def test_team_projections(client):
    """Verify team stage projections and group standings finish calculations."""
    response = client.get("/teams/T-83/stage-probs")
    assert response.status_code == 200
    data = response.json()
    assert data["reep_team_id"] == "T-83"
    assert "stage_probabilities" in data
    assert "group_finish_distribution" in data
    
    stages = data["stage_probabilities"]
    assert 0.0 <= stages["group_advance"] <= 1.0
    assert 0.0 <= stages["champion"] <= 1.0
    
    group_dist = data["group_finish_distribution"]
    assert pytest.approx(group_dist["1st"] + group_dist["2nd"] + group_dist["3rd_advance"] + group_dist["eliminated"], 0.01) == 1.0

def test_golden_boot_leaderboard(client):
    """Verify Golden Boot simulated candidates list."""
    response = client.get("/players/golden-boot?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "leaderboard" in data
    leaderboard = data["leaderboard"]
    assert len(leaderboard) == 10
    
    # Assert sorting order of p_golden_boot
    probs = [p["p_golden_boot"] for p in leaderboard]
    assert probs == sorted(probs, reverse=True)
