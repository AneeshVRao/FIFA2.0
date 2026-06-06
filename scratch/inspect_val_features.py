import duckdb
import pandas as pd
import numpy as np

con = duckdb.connect("data/fifa_world_cup.duckdb")
df = con.execute("SELECT * FROM fct_model_match_features").fetchdf()
con.close()

df["date"] = pd.to_datetime(df["date"])
df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()

features = [
    "elo_rating_diff",
    "squad_market_value_diff_eur",
    "host_nation_flag",
    "timezone_crossings_diff",
    "team_a_travel_km",
    "team_b_travel_km",
    "rest_day_asymmetry",
    "altitude_diff_m",
    "total_caps_diff",
    "total_intl_goals_diff",
    "confederation_strength_a",
    "confederation_strength_b",
    "joint_squad_age_diff",
    "avg_squad_height_diff_cm",
    "historic_fifa_points_diff",
    "match_stage_pressure",
    "head_to_head_elo_record"
]

print("=== Feature Null Counts and Summary in 2022 WC Validation Set ===")
for f in features:
    nulls = df_val[f].isna().sum()
    mean = df_val[f].mean()
    std = df_val[f].std()
    min_val = df_val[f].min()
    max_val = df_val[f].max()
    print(f"{f:30} | Nulls: {nulls:2} | Mean: {mean:10.2f} | Std: {std:10.2f} | Min: {min_val:10.2f} | Max: {max_val:10.2f}")

print("\n=== Sample of First 5 Rows of Validation Set ===")
print(df_val[["home_team", "away_team", "outcome", "elo_rating_diff", "squad_market_value_diff_eur"]].head())
