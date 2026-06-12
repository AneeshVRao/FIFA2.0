import os
import duckdb

db_path = os.path.join("data", "fifa_world_cup.duckdb")
print("Connecting to:", db_path)
if not os.path.exists(db_path):
    print("Database does not exist!")
    exit(1)

conn = duckdb.connect(db_path)
print("\nTables:")
tables = conn.execute("SHOW TABLES").fetchall()
for t in tables:
    print(t[0])

print("\n--- fct_matches schema ---")
try:
    print(conn.execute("DESCRIBE fct_matches").fetchdf())
    row_count = conn.execute("SELECT COUNT(*) FROM fct_matches").fetchone()[0]
    print(f"Row count: {row_count}")
    if row_count > 0:
        print("Sample data:")
        print(conn.execute("SELECT * FROM fct_matches LIMIT 5").fetchdf())
except Exception as e:
    print("Error describing fct_matches:", e)

print("\n--- team_stage_probabilities schema ---")
try:
    print(conn.execute("DESCRIBE team_stage_probabilities").fetchdf())
except Exception as e:
    print("Error describing team_stage_probabilities:", e)

print("\n--- matchup_forecasts schema ---")
try:
    print(conn.execute("DESCRIBE matchup_forecasts").fetchdf())
    print(f"Row count: {conn.execute('SELECT COUNT(*) FROM matchup_forecasts').fetchone()[0]}")
except Exception as e:
    print("Error describing matchup_forecasts:", e)

print("\n--- check if any other matches tables exist ---")
try:
    print(conn.execute("SELECT * FROM information_schema.tables WHERE table_name LIKE '%match%'").fetchdf())
except Exception as e:
    print(e)

conn.close()
