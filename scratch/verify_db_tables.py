import duckdb

con = duckdb.connect("data/fifa_world_cup.duckdb")

print("=== Checking dim_teams ===")
df_teams = con.execute("SELECT * FROM dim_teams").fetchdf()
print(f"Row count: {len(df_teams)}")
print("\nColumns and Null Counts:")
print(df_teams.isna().sum())
print("\nSample Rows:")
print(df_teams[["reep_team_id", "team_name_canonical", "confederation", "pretournament_elo", "is_host_nation"]].head(10))

print("\n=== Checking dim_players ===")
df_players = con.execute("SELECT * FROM dim_players").fetchdf()
print(f"Row count: {len(df_players)}")
print("\nColumns and Null Counts:")
print(df_players.isna().sum())
print("\nSample Rows:")
print(df_players[["reep_player_id", "player_name_canonical", "position", "bayesian_penalty_conversion"]].head(10))

con.close()
