import duckdb
con = duckdb.connect('data/fifa_world_cup.duckdb')
print(con.execute("SELECT match_id, team_a_name, team_b_name, goals_a, goals_b FROM fct_matches WHERE match_id IN ('match_1', 'match_2')").df())
