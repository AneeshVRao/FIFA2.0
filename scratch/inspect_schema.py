import duckdb

con = duckdb.connect("data/fifa_world_cup.duckdb")
tables = con.execute("SHOW TABLES").fetchall()
print("=== Tables in DuckDB ===")
for t in tables:
    name = t[0]
    cols = con.execute(f"DESCRIBE {name}").fetchall()
    print(f"\nTable: {name}")
    for c in cols:
        print(f" - {c[0]}: {c[1]}")
con.close()
