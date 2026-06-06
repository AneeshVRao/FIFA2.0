import json, duckdb, pandas as pd, numpy as np

db = duckdb.connect('data/fifa_world_cup.duckdb')
data = json.load(open('data/wc_2026_teams.json'))

# 1. Map 2026 teams to their historical Fjelstul IDs or generate new ones
fjelstul_team_mapping = {
    "Algeria": "T-01", "Angola": "T-02", "Argentina": "T-03", "Australia": "T-04", "Austria": "T-05",
    "Belgium": "T-06", "Bolivia": "T-07", "Bosnia and Herzegovina": "T-08", "Brazil": "T-09",
    "Bulgaria": "T-10", "Cameroon": "T-11", "Canada": "T-12", "Chile": "T-13", "China": "T-14",
    "Colombia": "T-16", "Costa Rica": "T-17", "Croatia": "T-18", "Cuba": "T-19", "Czech Republic": "T-20",
    "Denmark": "T-22", "Ecuador": "T-25", "Egypt": "T-26", "El Salvador": "T-27", "England": "T-28",
    "France": "T-30", "Germany": "T-31", "Ghana": "T-32", "Haiti": "T-34", "Honduras": "T-35",
    "Hungary": "T-36", "Iran": "T-38", "Iraq": "T-39", "Italy": "T-41", "Ivory Coast": "T-42",
    "Jamaica": "T-43", "Japan": "T-44", "Mexico": "T-46", "Morocco": "T-47", "Netherlands": "T-48",
    "New Zealand": "T-49", "Nigeria": "T-50", "North Korea": "T-51", "Norway": "T-53", "Panama": "T-54",
    "Paraguay": "T-55", "Peru": "T-56", "Poland": "T-57", "Portugal": "T-58", "Qatar": "T-59",
    "Saudi Arabia": "T-63", "Scotland": "T-64", "Senegal": "T-65", "Serbia": "T-66", "South Africa": "T-70",
    "South Korea": "T-71", "Spain": "T-73", "Sweden": "T-74", "Switzerland": "T-75", "Tunisia": "T-79",
    "Turkey": "T-80", "Ukraine": "T-81", "United States": "T-83", "Uruguay": "T-84", "Wales": "T-85"
}

# New IDs for non-historical teams
new_team_mapping = {
    "Cape Verde": "T-89",
    "Curaçao": "T-90",
    "DR Congo": "T-91",
    "Jordan": "T-92",
    "Uzbekistan": "T-93"
}

def get_team_id(name):
    if name == 'USA': return 'T-83'
    if name in fjelstul_team_mapping:
        return fjelstul_team_mapping[name]
    if name in new_team_mapping:
        return new_team_mapping[name]
    return f"T-GEN-{name.upper()[:3]}"

# Transfermarkt country mapping
all_citizenships = [r[0] for r in db.execute("SELECT DISTINCT country_of_citizenship FROM raw_transfermarkt_players").fetchall() if r[0]]
def get_tm_citizenship(name):
    if name == 'USA': return 'United States'
    if name == 'Curaçao': return 'Curacao'
    if name == 'South Korea': return 'Korea, South'
    if name == 'Bosnia and Herzegovina': return 'Bosnia-Herzegovina'
    if name == 'Ivory Coast': return "Cote d'Ivoire"
    for c in all_citizenships:
        if c.lower() == name.lower():
            return c
    return name

elos = dict(db.execute("SELECT team_name, elo_rating FROM fct_international_elo").fetchall())

# Rebuild dim_teams
print("Building dim_teams...")
teams_rows = []
for group, teams in data['groups'].items():
    for team in teams:
        name = team['name']
        tid = get_team_id(name)
        c_name = get_tm_citizenship(name)
        
        elo_name = name
        if name == 'USA': elo_name = 'United States'
        elo = elos.get(elo_name, 1500.0)
        
        # Query Transfermarkt aggregates using parameterization
        tm_query = """
        SELECT 
            SUM(market_value_in_eur) AS total_val,
            SUM(international_caps) AS total_caps,
            SUM(international_goals) AS total_goals,
            AVG(2026 - EXTRACT(year FROM CAST(date_of_birth AS DATE))) AS avg_age,
            AVG(height_in_cm) AS avg_height,
            COUNT(*) AS player_count
        FROM raw_transfermarkt_players
        WHERE country_of_citizenship = ?
        """
        tm_res = db.execute(tm_query, (c_name,)).fetchone()
        val = tm_res[0] if tm_res[0] is not None else 50000000.0
        caps = tm_res[1] if tm_res[1] is not None else 350
        goals = tm_res[2] if tm_res[2] is not None else 20
        age = tm_res[3] if tm_res[3] is not None else 26.5
        height = tm_res[4] if tm_res[4] is not None else 181.5
        
        teams_rows.append({
            "reep_team_id": tid,
            "team_name_canonical": 'United States' if name == 'USA' else name,
            "group_code": group,
            "is_host_nation": team['host'],
            "pretournament_elo": elo,
            "squad_market_value_eur": int(val),
            "avg_squad_age": float(age),
            "avg_squad_height_cm": float(height),
            "total_caps": int(caps),
            "historic_fifa_points": float(elo), 
            "tm_team_id": tid,
            "fbref_team_id": tid,
            "confederation": team['confederation']
        })

df_teams = pd.DataFrame(teams_rows)
db.execute("CREATE OR REPLACE TABLE dim_teams AS SELECT * FROM df_teams")
print(f"Created dim_teams with {len(df_teams)} rows.")

# Rebuild dim_players
print("\nBuilding dim_players...")
# Load Bayesian estimates
bayesian_estimates = {}
try:
    rows = db.execute("SELECT player_id, bayesian_conversion_rate, bayesian_conversion_sd FROM int_penalty_bayesian_estimates").fetchall()
    for r in rows:
        bayesian_estimates[r[0]] = (r[1], r[2])
except Exception as e:
    print("Warning, could not load Bayesian penalty estimates:", e)

players_rows = []
for group, teams in data['groups'].items():
    for team in teams:
        name = team['name']
        tid = get_team_id(name)
        c_name = get_tm_citizenship(name)
        
        # Load players for this country from Transfermarkt using parameters
        tm_players_query = """
        SELECT 
            player_id,
            name,
            position,
            2026 - EXTRACT(year FROM CAST(date_of_birth AS DATE)) AS age,
            height_in_cm,
            market_value_in_eur,
            international_caps,
            international_goals
        FROM raw_transfermarkt_players
        WHERE country_of_citizenship = ?
        """
        df_p = db.execute(tm_players_query, (c_name,)).fetchdf()
        if len(df_p) == 0:
            print(f"Warning: No players found in Transfermarkt for {name} ({c_name})")
            # Create a mock player squad for teams with zero players
            for i in range(26):
                pos = "Goalkeeper" if i < 3 else ("Defender" if i < 11 else ("Midfielder" if i < 19 else "Forward"))
                players_rows.append({
                    "reep_player_id": f"P-MOCK-{tid}-{i}",
                    "reep_team_id": tid,
                    "player_name_canonical": f"{name} Player {i}",
                    "position": pos,
                    "age": 26,
                    "height_cm": 182,
                    "market_value_eur": 1000000,
                    "international_caps": 15,
                    "international_goals": 2 if pos == "Forward" else 0,
                    "bayesian_penalty_conversion": 0.80 if pos == "Forward" else (0.75 if pos == "Midfielder" else (0.65 if pos == "Defender" else 0.60)),
                    "bayesian_penalty_conversion_sd": 0.15,
                    "bayesian_gk_save_rate": 0.17 if pos == "Goalkeeper" else 0.0
                })
            continue
            
        # Select 26 players: 3 Goalkeepers + 23 outfield players
        df_p["market_value_in_eur"] = df_p["market_value_in_eur"].fillna(500000).astype(int)
        df_p["international_caps"] = df_p["international_caps"].fillna(5).astype(int)
        df_p["international_goals"] = df_p["international_goals"].fillna(0).astype(int)
        df_p["height_in_cm"] = df_p["height_in_cm"].fillna(181).astype(int)
        df_p["age"] = df_p["age"].fillna(26).astype(int)
        
        gks = df_p[df_p["position"] == "Goalkeeper"].sort_values(by="market_value_in_eur", ascending=False).head(3)
        outfield = df_p[df_p["position"] != "Goalkeeper"].sort_values(by="market_value_in_eur", ascending=False).head(23)
        
        # Ensure we have at least 3 GKs
        if len(gks) < 3:
            needed = 3 - len(gks)
            extra_gks = df_p[df_p["position"] == "Goalkeeper"].sort_values(by="market_value_in_eur", ascending=False)
            if len(extra_gks) >= 3:
                gks = extra_gks.head(3)
            else:
                # generate mock GK
                mock_gks = pd.DataFrame([{
                    "player_id": 999000 + i,
                    "name": f"GK Backup {i}",
                    "position": "Goalkeeper",
                    "age": 27,
                    "height_in_cm": 188,
                    "market_value_in_eur": 500000,
                    "international_caps": 5,
                    "international_goals": 0
                } for i in range(needed)])
                gks = pd.concat([gks, mock_gks], ignore_index=True)
                
        squad = pd.concat([gks, outfield], ignore_index=True)
        
        for idx, p_row in squad.iterrows():
            pos = p_row["position"]
            if pos == "Attack": pos = "Forward"
            elif pos not in ["Goalkeeper", "Defender", "Midfielder", "Forward"]:
                pos = "Forward" # fallback
                
            pid = f"P-{p_row['player_id']}"
            
            # Lookup Bayesian conversion rate
            est = bayesian_estimates.get(str(p_row['player_id']), None)
            if est is not None:
                conv, sd = est[0], est[1]
            else:
                # Default positional priors
                sd = 0.15
                if pos == "Forward": conv = 0.80
                elif pos == "Midfielder": conv = 0.75
                elif pos == "Defender": conv = 0.65
                else: conv = 0.60
                
            players_rows.append({
                "reep_player_id": pid,
                "reep_team_id": tid,
                "player_name_canonical": p_row["name"],
                "position": pos,
                "age": int(p_row["age"]),
                "height_cm": int(p_row["height_in_cm"]),
                "market_value_eur": int(p_row["market_value_in_eur"]),
                "international_caps": int(p_row["international_caps"]),
                "international_goals": int(p_row["international_goals"]),
                "bayesian_penalty_conversion": float(conv),
                "bayesian_penalty_conversion_sd": float(sd),
                "bayesian_gk_save_rate": 0.17 if pos == "Goalkeeper" else 0.0
            })

df_players = pd.DataFrame(players_rows)
db.execute("CREATE OR REPLACE TABLE dim_players AS SELECT * FROM df_players")
print(f"Created dim_players with {len(df_players)} rows.")
print("Verifying GK count per team:")
print(db.execute("SELECT reep_team_id, COUNT(*) FILTER(WHERE position='Goalkeeper') AS gk_count, COUNT(*) AS total_count FROM dim_players GROUP BY reep_team_id").fetchdf().to_string())
