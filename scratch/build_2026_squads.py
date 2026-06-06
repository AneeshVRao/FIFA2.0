import json, duckdb, pandas as pd

db = duckdb.connect('data/fifa_world_cup.duckdb')
data = json.load(open('data/wc_2026_teams.json'))

# Get all elo team names and ratings
elos = dict(db.execute("SELECT team_name, elo_rating FROM fct_international_elo").fetchall())

# Let's inspect unique citizenships in Transfermarkt
all_citizenships = [r[0] for r in db.execute("SELECT DISTINCT country_of_citizenship FROM raw_transfermarkt_players").fetchall() if r[0]]

def get_closest_citizenship(name):
    if name == 'USA': return 'United States'
    if name == 'Curaçao': return 'Curacao'
    if name == 'South Korea':
        return 'Korea, South'
    # Try case-insensitive matching
    for c in all_citizenships:
        if c.lower() == name.lower():
            return c
    return name

rows = []
for group, teams in data['groups'].items():
    for team in teams:
        name = team['name']
        c_name = get_closest_citizenship(name)
        
        # Look up Elo
        elo_name = name
        if name == 'USA': elo_name = 'United States'
        elo = elos.get(elo_name, 1500.0)
        
        # Query Transfermarkt players for this citizenship
        tm_query = f"""
        SELECT 
            SUM(market_value_in_eur) AS total_val,
            SUM(international_caps) AS total_caps,
            SUM(international_goals) AS total_goals,
            AVG(2026 - EXTRACT(year FROM CAST(date_of_birth AS DATE))) AS avg_age,
            AVG(height_in_cm) AS avg_height,
            COUNT(*) AS player_count
        FROM raw_transfermarkt_players
        WHERE country_of_citizenship = '{c_name}'
        """
        tm_res = db.execute(tm_query).fetchone()
        
        val = tm_res[0] if tm_res[0] is not None else 50000000.0 # €50M default
        caps = tm_res[1] if tm_res[1] is not None else 350
        goals = tm_res[2] if tm_res[2] is not None else 20
        age = tm_res[3] if tm_res[3] is not None else 26.5
        height = tm_res[4] if tm_res[4] is not None else 181.5
        p_count = tm_res[5]
        
        rows.append({
            "group": group,
            "team_name": name,
            "c_name": c_name,
            "elo": elo,
            "squad_val": val,
            "total_caps": caps,
            "total_goals": goals,
            "avg_age": age,
            "avg_height": height,
            "player_count": p_count
        })

df = pd.DataFrame(rows)
print(df.to_string())
