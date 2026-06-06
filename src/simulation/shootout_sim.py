import numpy as np
from typing import Dict, List, Tuple, Any

def get_shootout_roster(players: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Selects the shootout roster from a team's squad:
    - 1 Goalkeeper: highest caps/market value
    - 10 Outfield Players: sorted by position (Forward -> Midfielder -> Defender) and market value descending
    """
    # Find goalkeepers
    gks = [p for p in players if p["position"] == "Goalkeeper"]
    if len(gks) == 0:
        # Fallback mock goalkeeper
        gk = {
            "reep_player_id": "P-MOCK-GK",
            "player_name_canonical": "Mock Goalkeeper",
            "position": "Goalkeeper",
            "bayesian_penalty_conversion": 0.60,
            "bayesian_gk_save_rate": 0.17
        }
    else:
        # Pick the goalkeeper with highest caps (or market value)
        gks.sort(key=lambda x: (x.get("international_caps", 0) or 0, x.get("market_value_eur", 0) or 0), reverse=True)
        gk = gks[0]
        
    # Outfield players
    outfield = [p for p in players if p["position"] != "Goalkeeper"]
    
    # Sort outfield players by: Forward first, Midfielder second, Defender third
    position_ranks = {"Forward": 0, "Midfielder": 1, "Defender": 2}
    
    def sort_key(p):
        pos_rank = position_ranks.get(p["position"], 2)
        val = p.get("market_value_eur", 0) or 0
        caps = p.get("international_caps", 0) or 0
        return (pos_rank, -val, -caps)
        
    outfield.sort(key=sort_key)
    
    takers = outfield[:10]
    
    # Fill with mock players if less than 10 outfield players
    while len(takers) < 10:
        idx = len(takers)
        pos = "Defender" if idx >= 8 else ("Midfielder" if idx >= 5 else "Forward")
        priors = {"Forward": 0.80, "Midfielder": 0.75, "Defender": 0.65}
        takers.append({
            "reep_player_id": f"P-MOCK-Taker-{idx}",
            "player_name_canonical": f"Mock Outfield {idx}",
            "position": pos,
            "bayesian_penalty_conversion": priors[pos],
            "bayesian_gk_save_rate": 0.0
        })
        
    return gk, takers

def simulate_shootout(
    team_a_name: str,
    team_b_name: str,
    roster_a: Tuple[Dict[str, Any], List[Dict[str, Any]]],
    roster_b: Tuple[Dict[str, Any], List[Dict[str, Any]]]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Simulates a kick-by-kick penalty shootout between Team A and Team B.
    Returns:
      winner: name of the winning team
      log: list of dicts describing each kick outcome
    """
    gk_a, takers_a = roster_a
    gk_b, takers_b = roster_b
    
    # Combine outfield takers and goalkeepers into 11-player shooting lists
    shooters_a = takers_a + [gk_a]
    shooters_b = takers_b + [gk_b]
    
    score_a = 0
    score_b = 0
    shots_a = 0
    shots_b = 0
    
    log = []
    
    # Track results of shots
    results_a = []
    results_b = []
    
    round_idx = 0
    
    # Phase 1: Best of 5 kicks
    while round_idx < 5:
        # Team A shoots
        taker_a = shooters_a[round_idx]
        p_conv_a = calculate_conversion_prob(taker_a, gk_b, round_idx + 1, score_a - score_b, 5 - shots_a, 5 - shots_b)
        goal_a = np.random.rand() < p_conv_a
        shots_a += 1
        if goal_a:
            score_a += 1
        results_a.append(goal_a)
        
        log.append({
            "round": round_idx + 1,
            "team": team_a_name,
            "taker": taker_a["player_name_canonical"],
            "position": taker_a["position"],
            "goalkeeper": gk_b["player_name_canonical"],
            "p_conversion": float(p_conv_a),
            "outcome": "goal" if goal_a else "miss/save"
        })
        
        # Check if Team B can still catch up
        if score_a > score_b + (5 - shots_b):
            # Team A wins, Team B cannot catch up even if they score all remaining
            return team_a_name, log
        if score_b > score_a + (5 - shots_a):
            # Team B wins, Team A cannot catch up
            return team_b_name, log
            
        # Team B shoots
        taker_b = shooters_b[round_idx]
        p_conv_b = calculate_conversion_prob(taker_b, gk_a, round_idx + 1, score_b - score_a, 5 - shots_b, 5 - shots_a)
        goal_b = np.random.rand() < p_conv_b
        shots_b += 1
        if goal_b:
            score_b += 1
        results_b.append(goal_b)
        
        log.append({
            "round": round_idx + 1,
            "team": team_b_name,
            "taker": taker_b["player_name_canonical"],
            "position": taker_b["position"],
            "goalkeeper": gk_a["player_name_canonical"],
            "p_conversion": float(p_conv_b),
            "outcome": "goal" if goal_b else "miss/save"
        })
        
        # Check if Team A can still catch up
        if score_a > score_b + (5 - shots_b):
            return team_a_name, log
        if score_b > score_a + (5 - shots_a):
            return team_b_name, log
            
        round_idx += 1
        
    # Phase 2: Sudden death (rounds 6+)
    while True:
        # Team A shoots
        taker_idx = round_idx % 11
        taker_a = shooters_a[taker_idx]
        p_conv_a = calculate_conversion_prob(taker_a, gk_b, round_idx + 1, score_a - score_b, 1, 1, sudden_death=True)
        goal_a = np.random.rand() < p_conv_a
        shots_a += 1
        if goal_a:
            score_a += 1
            
        log.append({
            "round": round_idx + 1,
            "team": team_a_name,
            "taker": taker_a["player_name_canonical"],
            "position": taker_a["position"],
            "goalkeeper": gk_b["player_name_canonical"],
            "p_conversion": float(p_conv_a),
            "outcome": "goal" if goal_a else "miss/save"
        })
        
        # Team B shoots
        taker_b = shooters_b[taker_idx]
        p_conv_b = calculate_conversion_prob(taker_b, gk_a, round_idx + 1, score_b - score_a, 1, 0, sudden_death=True, must_score=goal_a)
        goal_b = np.random.rand() < p_conv_b
        shots_b += 1
        if goal_b:
            score_b += 1
            
        log.append({
            "round": round_idx + 1,
            "team": team_b_name,
            "taker": taker_b["player_name_canonical"],
            "position": taker_b["position"],
            "goalkeeper": gk_a["player_name_canonical"],
            "p_conversion": float(p_conv_b),
            "outcome": "goal" if goal_b else "miss/save"
        })
        
        # Check sudden death result (after equal number of shots)
        if score_a > score_b:
            return team_a_name, log
        elif score_b > score_a:
            return team_b_name, log
            
        round_idx += 1

def calculate_conversion_prob(
    taker: Dict[str, Any],
    gk: Dict[str, Any],
    kick_num: int,
    score_diff: int,
    shots_left_us: int,
    shots_left_them: int,
    sudden_death: bool = False,
    must_score: bool = False
) -> float:
    """
    Computes the matchup conversion probability:
    p_conversion = taker_rate - (gk_save_rate - 0.17) + pressure_modifier
    """
    taker_rate = taker["bayesian_penalty_conversion"]
    gk_save_rate = gk["bayesian_gk_save_rate"]
    
    # GK save rate adjustment (default is 0.17, so if GK is better, it reduces conversion)
    gk_adjustment = gk_save_rate - 0.17
    
    # Calculate pressure modifier
    pressure_modifier = 0.0
    
    # 1. Round-based decay (psychological fatigue/pressure escalates as shootout progresses)
    # Starts at round 1 (no penalty), then -0.01 per kick round up to -0.10 max
    pressure_modifier += -0.01 * min(10, kick_num - 1)
    
    # 2. Score differential pressure (being behind increases pressure)
    if score_diff < 0:
        pressure_modifier += 0.02 * score_diff # e.g. -0.02 if behind by 1, -0.04 if behind by 2
        
    # 3. Elimination pressure (must score or they lose immediately)
    # Occurs if we are behind on the 5th kick or in sudden death when opponent already scored
    is_elimination_scenario = False
    if sudden_death and must_score:
        is_elimination_scenario = True
    elif not sudden_death and shots_left_us == 1 and score_diff < 0:
        # e.g. score is 3-4, we have 1 kick left, they have 0 left. If we miss, we lose.
        is_elimination_scenario = True
        
    if is_elimination_scenario:
        pressure_modifier += -0.05
        
    # Combine terms
    p_conversion = taker_rate - gk_adjustment + pressure_modifier
    
    # Clip probability between 0.05 and 0.99 per PRD
    return float(np.clip(p_conversion, 0.05, 0.99))
