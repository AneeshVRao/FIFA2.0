import duckdb
import pandas as pd

con = duckdb.connect("data/fifa_world_cup.duckdb")

tables = [
    "team_stage_probabilities",
    "golden_boot_distribution",
    "matchup_forecasts",
    "group_table_distributions",
    "bracket_path_frequencies"
]

print("=== VERIFYING SIMULATION OUTPUTS IN DUCKDB ===")
for t in tables:
    try:
        df = con.execute(f"SELECT * FROM {t}").fetchdf()
        print(f"\nTable: {t}")
        print(f"  Row count: {len(df)}")
        print(f"  Null counts:")
        null_counts = df.isna().sum()
        for col, count in null_counts.items():
            print(f"    {col}: {count}")
            
        print("  Sample row:")
        print(df.head(1).to_dict(orient="records"))
    except Exception as e:
        print(f"Error querying table {t}: {e}")

con.close()
