import duckdb
import pandas as pd

con = duckdb.connect("data/fifa_world_cup.duckdb")
df = con.execute("""
    SELECT outcome, count(*) as cnt 
    FROM fct_model_match_features 
    WHERE date >= '2022-11-20' AND date <= '2022-12-18' AND tournament = 'FIFA World Cup' 
    GROUP BY outcome
""").fetchdf()
print("Outcomes:")
print(df)

df_all = con.execute("SELECT count(*) as total FROM fct_model_match_features").fetchdf()
print("Total matches in table:", df_all.iloc[0]["total"])
con.close()
