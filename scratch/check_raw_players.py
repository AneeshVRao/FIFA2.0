import duckdb

db = duckdb.connect('data/fifa_world_cup.duckdb')
for team in ['Jordan', 'Uzbekistan', 'Cape Verde', 'Curacao', 'Cura']:
    # Let's count in Transfermarkt players
    c1 = db.execute(f"SELECT count(*) FROM raw_transfermarkt_players WHERE LOWER(country_of_citizenship) = '{team.lower()}'").fetchone()[0]
    c2 = db.execute(f"SELECT count(*) FROM raw_fjelstul_players WHERE LOWER(family_name) LIKE '%{team.lower()}%'").fetchone()[0]
    print(f"{team}: Transfermarkt count = {c1}, Fjelstul count = {c2}")

# Let's list some unique citizenships in Transfermarkt to see if they exist
print("\nUnique citizenships in Transfermarkt matching:")
all_citizenships = [r[0] for r in db.execute("SELECT DISTINCT country_of_citizenship FROM raw_transfermarkt_players").fetchall() if r[0]]
for target in ['jordan', 'uzbekistan', 'cape', 'curacao', 'cura', 'congo']:
    matches = [c for c in all_citizenships if target in c.lower()]
    print(f"Target '{target}': {matches}")
