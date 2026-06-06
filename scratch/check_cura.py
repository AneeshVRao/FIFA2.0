import duckdb
db = duckdb.connect('data/fifa_world_cup.duckdb')
rows = db.execute("SELECT DISTINCT team_name FROM fct_international_elo").fetchall()
for r in rows:
    name = r[0]
    if 'cura' in name.lower() or 'c\u00fcr' in name.lower() or 'c\u00e5r' in name.lower():
        print(f"Name: {name}, Repr: {repr(name)}, Bytes: {name.encode('utf-8', errors='replace')}")
