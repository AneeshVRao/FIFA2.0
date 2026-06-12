import duckdb
con = duckdb.connect('data/fifa_world_cup.duckdb')
con.execute("UPDATE fct_matches SET goals_a = 2, goals_b = 0 WHERE match_id = 'match_1'")
con.execute("UPDATE fct_matches SET goals_a = 2, goals_b = 1 WHERE match_id = 'match_2'")
con.execute("UPDATE fct_matches SET goals_a = NULL, goals_b = NULL WHERE match_id NOT IN ('match_1', 'match_2')")
print('Database updated successfully.')
