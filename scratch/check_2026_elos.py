import json, duckdb

db = duckdb.connect('data/fifa_world_cup.duckdb')
data = json.load(open('data/wc_2026_teams.json'))

# Get all elo team names and ratings
elos = dict(db.execute("SELECT team_name, elo_rating FROM fct_international_elo").fetchall())

# Standard name mapping function
def clean_name(name):
    if name == 'USA': return 'United States'
    if 'Cura' in name: return 'Curaao' # match the raw database spelling
    return name

missing = []
for group, teams in data['groups'].items():
    for team in teams:
        name = clean_name(team['name'])
        if name in elos:
            print(f"{team['name']} -> {name}: Elo = {elos[name]}")
        else:
            missing.append((team['name'], name))

print("\nMissing Elos:", missing)
