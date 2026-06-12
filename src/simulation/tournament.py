import random
import numpy as np
import itertools
from typing import Dict, List, Tuple, Any
from src.simulation.dixon_coles import get_match_xg, sample_scoreline, get_native_altitude
from src.simulation.shootout_sim import simulate_shootout, get_shootout_roster

# Allowed third-place groups per group winner in Round of 32 (based on FIFA's bracket spec)
ALLOWED_3RD = {
    '1A': {'C', 'E', 'F', 'H', 'I'},
    '1B': {'E', 'F', 'G', 'I', 'J'},
    '1D': {'B', 'E', 'F', 'I', 'J'},
    '1E': {'A', 'B', 'C', 'D', 'F'},
    '1G': {'A', 'E', 'H', 'I', 'J'},
    '1I': {'C', 'D', 'F', 'G', 'H'},
    '1K': {'D', 'E', 'I', 'J', 'L'},
    '1L': {'E', 'H', 'I', 'J', 'K'}
}

# Mapping of Round of 32 matches
# Winners of these advance to the Round of 16 slots (Matches 89 to 96)
R32_MATCH_MAP = [
    # (MatchNum, TeamA_Label, TeamB_Label)
    (73, '2A', '2B'),
    (74, '1E', '3RD_placeholder_1'), # plays 3rd place
    (75, '1F', '2C'),
    (76, '1C', '2F'),
    (77, '1I', '3RD_placeholder_2'), # plays 3rd place
    (78, '2E', '2I'),
    (79, '1A', '3RD_placeholder_3'), # plays 3rd place
    (80, '1L', '3RD_placeholder_4'), # plays 3rd place
    (81, '1D', '3RD_placeholder_5'), # plays 3rd place
    (82, '1G', '3RD_placeholder_6'), # plays 3rd place
    (83, '2K', '2L'),
    (84, '1H', '2J'),
    (85, '1B', '3RD_placeholder_7'), # plays 3rd place
    (86, '1J', '2H'),
    (87, '1K', '3RD_placeholder_8'), # plays 3rd place
    (88, '2D', '2G')
]

def simulate_group_stage(
    group_assignments: Dict[str, List[Dict[str, Any]]],
    venues: List[Dict[str, Any]],
    actual_matches: Dict[str, Dict[str, int]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Simulates all 72 group stage matches across the 12 groups.
    Updates dynamic Elo ratings and computes travel distance & rest days chronologically.
    Returns:
      match_results: list of simulated matches with details
      final_team_states: dict of team states at the end of the group stage
    """
    # Initialize team states: Elo, native altitude, last match date, last venue position
    team_states = {}
    for group_code, teams in group_assignments.items():
        for team in teams:
            team_states[team["team_name_canonical"]] = {
                "team_id": team["reep_team_id"],
                "team_name": team["team_name_canonical"],
                "confederation": team["confederation"],
                "group_code": group_code,
                "dynamic_elo": team["pretournament_elo"],
                "pretournament_elo": team["pretournament_elo"],
                "native_altitude": get_native_altitude(team["team_name_canonical"]),
                "last_date": None,
                "last_coords": None,
                "last_tz": None
            }
            
    match_results = []
    
    # 2026 World Cup venues lookup
    venue_dict = {v["venue_id"]: v for v in venues}
    # Standard group stage schedule (we can assign a random or fixed order for the 6 matches per group)
    # We will simulate groups A to L sequentially. For each group, we simulate matches chronologically.
    # Group match pairings order: (0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)
    # Let's say group stage spans days 1 to 12. Each group's matches are spaced out by 4 days.
    # Day 1: T0 vs T1, T2 vs T3. Day 5: T0 vs T2, T1 vs T3. Day 9: T0 vs T3, T1 vs T2.
    # We will assign venues to group stage matches. We can cycle through the 16 venues.
    venue_ids = list(venue_dict.keys())
    venue_index = 0
    group_match_idx = 1
    
    for group_code, teams in group_assignments.items():
        team_names = [t["team_name_canonical"] for t in teams]
        pairings = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
        
        for match_idx, (idx_a, idx_b) in enumerate(pairings):
            team_a_name = team_names[idx_a]
            team_b_name = team_names[idx_b]
            
            state_a = team_states[team_a_name]
            state_b = team_states[team_b_name]
            
            # Select venue for the match
            vid = venue_ids[venue_index % len(venue_ids)]
            venue_index += 1
            venue = venue_dict[vid]
            
            venue_coords = (venue["latitude"], venue["longitude"])
            venue_tz = round(venue["longitude"] / 15.0)
            venue_alt = venue["altitude_m"]
            
            # Compute travel & rest for Team A
            travel_a = 0.0
            rest_a = 30.0
            if state_a["last_date"] is not None:
                rest_a = 4.0 # 4 days gap standard in schedule
                prev_coords = state_a["last_coords"]
                travel_a = haversine_distance(prev_coords[0], prev_coords[1], venue_coords[0], venue_coords[1])
                
            # Compute travel & rest for Team B
            travel_b = 0.0
            rest_b = 30.0
            if state_b["last_date"] is not None:
                rest_b = 4.0
                prev_coords = state_b["last_coords"]
                travel_b = haversine_distance(prev_coords[0], prev_coords[1], venue_coords[0], venue_coords[1])
                
            # Get expected goals
            lam, mu = get_match_xg(
                elo_a=state_a["dynamic_elo"],
                elo_b=state_b["dynamic_elo"],
                is_host_a=team_a_name in ["United States", "Mexico", "Canada"],
                is_host_b=team_b_name in ["United States", "Mexico", "Canada"],
                venue_alt=venue_alt,
                native_alt_a=state_a["native_altitude"],
                native_alt_b=state_b["native_altitude"],
                travel_a_km=travel_a,
                travel_b_km=travel_b,
                rest_a=rest_a,
                rest_b=rest_b
            )
            
            # Check if this match has actual results locked in
            match_id_str = f"match_{group_match_idx}"
            group_match_idx += 1
            
            if actual_matches and match_id_str in actual_matches:
                goals_a = actual_matches[match_id_str]["goals_a"]
                goals_b = actual_matches[match_id_str]["goals_b"]
            else:
                # Sample scoreline
                goals_a, goals_b = sample_scoreline(lam, mu)
            
            # Record result
            match_results.append({
                "stage": "group",
                "group_code": group_code,
                "team_a": team_a_name,
                "team_b": team_b_name,
                "goals_a": goals_a,
                "goals_b": goals_b,
                "venue_id": vid,
                "lam": lam,
                "mu": mu
            })
            
            # Update dynamic Elo ratings
            expected_a = 1.0 / (1.0 + 10.0 ** ((state_b["dynamic_elo"] - state_a["dynamic_elo"]) / 400.0))
            expected_b = 1.0 - expected_a
            
            if goals_a > goals_b:
                actual_a, actual_b = 1.0, 0.0
            elif goals_a < goals_b:
                actual_a, actual_b = 0.0, 1.0
            else:
                actual_a, actual_b = 0.5, 0.5
                
            # Margin of victory multiplier M
            gd = abs(goals_a - goals_b)
            if gd <= 1:
                M = 1.0
            elif gd == 2:
                M = 1.5
            else:
                M = (11.0 + gd) / 8.0
                
            K = 60.0
            delta_elo_a = K * M * (actual_a - expected_a)
            delta_elo_b = K * M * (actual_b - expected_b)
            
            # Update and apply mean reversion
            gamma = 0.15 # 15% reversion rate
            state_a["dynamic_elo"] += delta_elo_a
            state_a["dynamic_elo"] = state_a["dynamic_elo"] + gamma * (state_a["pretournament_elo"] - state_a["dynamic_elo"])
            
            state_b["dynamic_elo"] += delta_elo_b
            state_b["dynamic_elo"] = state_b["dynamic_elo"] + gamma * (state_b["pretournament_elo"] - state_b["dynamic_elo"])
            
            # Update prior states
            state_a["last_date"] = match_idx
            state_a["last_coords"] = venue_coords
            state_a["last_tz"] = venue_tz
            
            state_b["last_date"] = match_idx
            state_b["last_coords"] = venue_coords
            state_b["last_tz"] = venue_tz
            
    return match_results, team_states

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes Haversine distance in km between two GPS coordinates."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2.0) ** 2 + 
         np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0) ** 2)
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(R * c)

def calculate_standings(
    match_results: List[Dict[str, Any]],
    team_states: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculates standings and ranks teams within each group by Points -> GD -> GF -> H2H -> Pre-tournament Elo.
    Returns:
      standings: dict mapping group_code -> ranked list of team stats dicts
    """
    # Initialize stats for all teams
    group_stats = {}
    for tname, state in team_states.items():
        gcode = state["group_code"]
        group_stats.setdefault(gcode, {})[tname] = {
            "team_name": tname,
            "team_id": state["team_id"],
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_diff": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "pretournament_elo": state["pretournament_elo"]
        }
        
    # Aggregate match outcomes
    h2h_matches = {} # (team1, team2) -> list of results (goals1, goals2)
    
    for match in match_results:
        ta, tb = match["team_a"], match["team_b"]
        ga, gb = match["goals_a"], match["goals_b"]
        gcode = match["group_code"]
        
        stats_a = group_stats[gcode][ta]
        stats_b = group_stats[gcode][tb]
        
        stats_a["goals_for"] += ga
        stats_a["goals_against"] += gb
        stats_b["goals_for"] += gb
        stats_b["goals_against"] += ga
        
        if ga > gb:
            stats_a["points"] += 3
            stats_a["wins"] += 1
            stats_b["losses"] += 1
        elif ga < gb:
            stats_b["points"] += 3
            stats_b["wins"] += 1
            stats_a["losses"] += 1
        else:
            stats_a["points"] += 1
            stats_b["points"] += 1
            stats_a["draws"] += 1
            stats_b["draws"] += 1
            
        # Record H2H details
        h2h_matches[(ta, tb)] = (ga, gb)
        h2h_matches[(tb, ta)] = (gb, ga)
        
    # Compute goal diffs
    for gcode, teams in group_stats.items():
        for tname, stats in teams.items():
            stats["goal_diff"] = stats["goals_for"] - stats["goals_against"]
            
    # Rank groups
    ranked_standings = {}
    for gcode, teams in group_stats.items():
        team_list = list(teams.values())
        
        # We sort using a custom comparison function that incorporates tiebreakers
        # A simple sort first by Points, GD, GF
        team_list.sort(key=lambda x: (x["points"], x["goal_diff"], x["goals_for"]), reverse=True)
        
        # Apply head-to-head tiebreaker for teams tied on Points, GD, GF
        # Group size is 4, so ties can be pairs or triples.
        i = 0
        while i < len(team_list) - 1:
            j = i + 1
            while j < len(team_list) and \
                  team_list[i]["points"] == team_list[j]["points"] and \
                  team_list[i]["goal_diff"] == team_list[j]["goal_diff"] and \
                  team_list[i]["goals_for"] == team_list[j]["goals_for"]:
                j += 1
                
            tied_count = j - i
            if tied_count > 1:
                tied_teams = team_list[i:j]
                
                # Resolve H2H among tied teams
                h2h_resolved = resolve_h2h_tiebreaker(tied_teams, h2h_matches)
                team_list[i:j] = h2h_resolved
                
            i = j
            
        ranked_standings[gcode] = team_list
        
    return ranked_standings

def resolve_h2h_tiebreaker(tied_teams: List[Dict[str, Any]], h2h_matches: Dict[Tuple[str, str], Tuple[int, int]]) -> List[Dict[str, Any]]:
    """Resolves a tiebreaker among a subset of teams in a group based on head-to-head records."""
    tied_names = {t["team_name"] for t in tied_teams}
    
    # Calculate mini-table stats
    mini_table = {name: {"name": name, "points": 0, "gd": 0, "gf": 0, "elo": 0} for name in tied_names}
    for t in tied_teams:
        mini_table[t["team_name"]]["elo"] = t["pretournament_elo"]
        
    # Query matches involving only these teams
    for (t1, t2), (g1, g2) in h2h_matches.items():
        if t1 in tied_names and t2 in tied_names and t1 < t2:
            # Match counts in H2H table
            mini_table[t1]["gf"] += g1
            mini_table[t1]["gd"] += (g1 - g2)
            mini_table[t2]["gf"] += g2
            mini_table[t2]["gd"] += (g2 - g1)
            
            if g1 > g2:
                mini_table[t1]["points"] += 3
            elif g1 < g2:
                mini_table[t2]["points"] += 3
            else:
                mini_table[t1]["points"] += 1
                mini_table[t2]["points"] += 1
                
    # Sort tied teams based on mini-table Points -> mini-table GD -> mini-table GF -> Pre-tournament Elo
    def h2h_sort_key(team_dict):
        name = team_dict["team_name"]
        stats = mini_table[name]
        return (stats["points"], stats["gd"], stats["gf"], stats["elo"])
        
    tied_teams_sorted = list(tied_teams)
    tied_teams_sorted.sort(key=h2h_sort_key, reverse=True)
    return tied_teams_sorted

def advance_third_place_teams(standings: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Collects all 12 third-place teams, ranks them, and returns:
      advancing_3rd: list of the top 8 advancing third-place team stats dicts (labeled with group_code)
      eliminated_3rd: list of the 4 eliminated third-place teams
    """
    third_place_list = []
    for gcode, team_list in standings.items():
        t = dict(team_list[2]) # copy 3rd place team stats
        t["group_code"] = gcode
        third_place_list.append(t)
        
    # Rank by Points -> GD -> GF -> Pre-tournament Elo
    third_place_list.sort(key=lambda x: (x["points"], x["goal_diff"], x["goals_for"], x["pretournament_elo"]), reverse=True)
    
    return third_place_list[:8], third_place_list[8:]

def assign_r32_pairings(
    standings: Dict[str, List[Dict[str, Any]]],
    advancing_3rd: List[Dict[str, Any]]
) -> List[Tuple[int, Dict[str, Any], Dict[str, Any]]]:
    """
    Resolves the 32 advancing teams into the 16 Round of 32 matches.
    Determines third-place allocation dynamically using a permutation search to satisfy
    group constraints and same-group exclusions.
    """
    # 1. Map winners and runners-up
    winners = {gcode: standings[gcode][0] for gcode in standings}
    runners_up = {gcode: standings[gcode][1] for gcode in standings}
    
    # 3rd place qualifiers by group
    third_place_by_group = {t["group_code"]: t for t in advancing_3rd}
    third_place_groups = set(third_place_by_group.keys())
    
    # We need to assign these 8 third-place teams to the 8 group winners: 1E, 1I, 1A, 1L, 1D, 1G, 1B, 1K.
    winners_3rd_slots = ['1E', '1I', '1A', '1L', '1D', '1G', '1B', '1K']
    
    # Permute the 8 qualified third-place groups to match the 8 winners slot list
    # Because there are only 8! = 40,320 permutations, we can quickly search for a valid matching.
    t_groups_list = list(third_place_groups)
    
    assigned_groups = None
    for perm in itertools.permutations(t_groups_list):
        valid = True
        for winner_slot, g_code in zip(winners_3rd_slots, perm):
            # Check if this group winner is allowed to play this third-place group
            if g_code not in ALLOWED_3RD[winner_slot]:
                valid = False
                break
            # Same group exclusion check: winner's group code cannot match the third-place group code
            w_group_code = winner_slot[1]
            if w_group_code == g_code:
                valid = False
                break
        if valid:
            assigned_groups = perm
            break
            
    # Fallback to simple same-group exclusion greedy matching if no strict permutation is valid
    if assigned_groups is None:
        assigned_groups = []
        available = list(t_groups_list)
        for winner_slot in winners_3rd_slots:
            w_group_code = winner_slot[1]
            # Find first available third-place group not equal to winner's group
            chosen = None
            for g in available:
                if g != w_group_code:
                    chosen = g
                    break
            if chosen is None:
                # If stuck, just take the first one
                chosen = available[0]
            assigned_groups.append(chosen)
            available.remove(chosen)
            
    # Create mapping of placeholder to assigned third-place team
    slot_mapping = {}
    slot_to_placeholder = {
        '1E': '3RD_placeholder_1',
        '1I': '3RD_placeholder_2',
        '1A': '3RD_placeholder_3',
        '1L': '3RD_placeholder_4',
        '1D': '3RD_placeholder_5',
        '1G': '3RD_placeholder_6',
        '1B': '3RD_placeholder_7',
        '1K': '3RD_placeholder_8'
    }
    for winner_slot, g_code in zip(winners_3rd_slots, assigned_groups):
        placeholder = slot_to_placeholder[winner_slot]
        slot_mapping[placeholder] = third_place_by_group[g_code]
        
    # 2. Build the 16 Round of 32 matches
    r32_matches = []
    for match_num, label_a, label_b in R32_MATCH_MAP:
        # Resolve Team A
        if label_a.startswith('1'):
            team_a = winners[label_a[1]]
        elif label_a.startswith('2'):
            team_a = runners_up[label_a[1]]
        else:
            team_a = slot_mapping[label_a]
            
        # Resolve Team B
        if label_b.startswith('1'):
            team_b = winners[label_b[1]]
        elif label_b.startswith('2'):
            team_b = runners_up[label_b[1]]
        else:
            team_b = slot_mapping[label_b]
            
        r32_matches.append((match_num, team_a, team_b))
        
    return r32_matches

def simulate_knockout_stage(
    r32_matches: List[Tuple[int, Dict[str, Any], Dict[str, Any]]],
    player_dict: Dict[str, List[Dict[str, Any]]],
    con
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Simulates the knockout stage down to the Final and Third-Place match.
    Returns:
      bracket_runs: dict containing the winner of each match, final rankings, etc.
      match_results: list of simulated matches with details
    """
    results = []
    
    # Store match outcomes: match_num -> winning_team_dict, losing_team_dict
    match_winners = {}
    
    # Helper to simulate a single knockout match
    def play_knockout_match(match_num: int, team_a: Dict[str, Any], team_b: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # Get Elo ratings
        elo_a = team_a["pretournament_elo"] # use pre-tournament Elo in knockout to represent team base strength
        elo_b = team_b["pretournament_elo"]
        
        # Knockout matches are played at neutral venues, no host advantage unless playing in home country
        is_host_a = team_a["team_name"] in ["United States", "Mexico", "Canada"]
        is_host_b = team_b["team_name"] in ["United States", "Mexico", "Canada"]
        
        # Expectation in 90 minutes
        lam, mu = get_match_xg(
            elo_a=elo_a,
            elo_b=elo_b,
            is_host_a=is_host_a,
            is_host_b=is_host_b,
            venue_alt=0.0, # assume standard sea level for knockout backtests/averages
            native_alt_a=get_native_altitude(team_a["team_name"]),
            native_alt_b=get_native_altitude(team_b["team_name"]),
            travel_a_km=0.0,
            travel_b_km=0.0,
            rest_a=5.0,
            rest_b=5.0
        )
        
        goals_a, goals_b = sample_scoreline(lam, mu)
        went_to_extra_time = False
        went_to_penalties = False
        pen_winner = None
        shootout_log = []
        
        # If level after 90 mins, play extra time (30 minutes)
        if goals_a == goals_b:
            went_to_extra_time = True
            # Extra time expected goals is scaled by 1/3 (30 mins vs 90 mins)
            lam_et = lam / 3.0
            mu_et = mu / 3.0
            et_a, et_b = sample_scoreline(lam_et, mu_et)
            goals_a += et_a
            goals_b += et_b
            
            # If still level, trigger penalty shootout
            if goals_a == goals_b:
                went_to_penalties = True
                # Roster extraction
                players_a = player_dict.get(team_a["team_name"], [])
                players_b = player_dict.get(team_b["team_name"], [])
                roster_a = get_shootout_roster(players_a)
                roster_b = get_shootout_roster(players_b)
                
                pen_winner, shootout_log = simulate_shootout(team_a["team_name"], team_b["team_name"], roster_a, roster_b)
                
        winner = None
        loser = None
        if goals_a > goals_b:
            winner, loser = team_a, team_b
        elif goals_a < goals_b:
            winner, loser = team_b, team_a
        else:
            # Decided by penalties
            if pen_winner == team_a["team_name"]:
                winner, loser = team_a, team_b
            else:
                winner, loser = team_b, team_a
                
        # Record match results
        results.append({
            "stage": "knockout",
            "match_num": match_num,
            "team_a": team_a["team_name"],
            "team_b": team_b["team_name"],
            "goals_a": goals_a,
            "goals_b": goals_b,
            "went_to_extra_time": went_to_extra_time,
            "went_to_penalties": went_to_penalties,
            "penalty_winner": pen_winner,
            "shootout_log": shootout_log,
            "winner": winner["team_name"],
            "loser": loser["team_name"]
        })
        
        return winner, loser

    # 1. Round of 32 (Matches 73–88)
    for match_num, team_a, team_b in r32_matches:
        win, lose = play_knockout_match(match_num, team_a, team_b)
        match_winners[match_num] = (win, lose)
        
    # 2. Round of 16 (Matches 89–96)
    r16_pairings = [
        (89, 74, 77),
        (90, 73, 75),
        (91, 76, 78),
        (92, 79, 80),
        (93, 83, 84),
        (94, 81, 82),
        (95, 86, 88),
        (96, 85, 87)
    ]
    for r16_num, m1, m2 in r16_pairings:
        win, lose = play_knockout_match(r16_num, match_winners[m1][0], match_winners[m2][0])
        match_winners[r16_num] = (win, lose)
        
    # 3. Quarter-finals (Matches 97–100)
    qf_pairings = [
        (97, 89, 90),
        (98, 93, 94),
        (99, 91, 92),
        (100, 95, 96)
    ]
    for qf_num, m1, m2 in qf_pairings:
        win, lose = play_knockout_match(qf_num, match_winners[m1][0], match_winners[m2][0])
        match_winners[qf_num] = (win, lose)
        
    # 4. Semi-finals (Matches 101–102)
    sf_pairings = [
        (101, 97, 98),
        (102, 99, 100)
    ]
    for sf_num, m1, m2 in sf_pairings:
        win, lose = play_knockout_match(sf_num, match_winners[m1][0], match_winners[m2][0])
        match_winners[sf_num] = (win, lose)
        
    # 5. Third-place match (Match 103) & Final (Match 104)
    # Losers of 101 & 102 play for third place
    third_winner, third_loser = play_knockout_match(103, match_winners[101][1], match_winners[102][1])
    
    # Winners of 101 & 102 play for the title
    champion, runner_up = play_knockout_match(104, match_winners[101][0], match_winners[102][0])
    
    bracket_runs = {
        "champion": champion["team_name"],
        "runner_up": runner_up["team_name"],
        "third_place": third_winner["team_name"],
        "fourth_place": third_loser["team_name"]
    }
    
    return bracket_runs, results
