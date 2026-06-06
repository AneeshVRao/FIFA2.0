import duckdb

db = duckdb.connect('data/fifa_world_cup.duckdb')
print("raw_fjelstul_players:")
print(db.execute("DESCRIBE raw_fjelstul_players").fetchall())
print("\nraw_fjelstul_squads:")
print(db.execute("DESCRIBE raw_fjelstul_squads").fetchall())
print("\nraw_transfermarkt_players:")
print(db.execute("DESCRIBE raw_transfermarkt_players").fetchall())
