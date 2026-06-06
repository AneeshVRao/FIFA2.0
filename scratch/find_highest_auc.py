import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score

con = duckdb.connect("data/fifa_world_cup.duckdb")
df = con.execute("SELECT * FROM fct_model_match_features").fetchdf()
con.close()

df["date"] = pd.to_datetime(df["date"])
df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()

feat_list = ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag"]

def swap_outcome(o):
    if o == 1: return 2
    if o == 2: return 1
    return 0

def get_symmetric_train_data(df_train_raw):
    df_train_neutral = df_train_raw[df_train_raw["neutral"] == True].copy()
    df_train_non_neutral = df_train_raw[df_train_raw["neutral"] == False].copy()
    df_train_neutral_swapped = df_train_neutral.copy()
    
    df_train_neutral_swapped["outcome"] = df_train_neutral_swapped["outcome"].apply(swap_outcome)
    df_train_neutral_swapped["home_team"], df_train_neutral_swapped["away_team"] = \
        df_train_neutral_swapped["away_team"], df_train_neutral_swapped["home_team"]
    df_train_neutral_swapped["elo_rating_diff"] = -df_train_neutral_swapped["elo_rating_diff"]
    df_train_neutral_swapped["squad_market_value_diff_eur"] = -df_train_neutral_swapped["squad_market_value_diff_eur"]
    df_train_neutral_swapped["team_a_travel_km"], df_train_neutral_swapped["team_b_travel_km"] = \
        df_train_neutral_swapped["team_b_travel_km"], df_train_neutral_swapped["team_a_travel_km"]
    df_train_neutral_swapped["total_caps_diff"] = -df_train_neutral_swapped["total_caps_diff"]
    df_train_neutral_swapped["total_intl_goals_diff"] = -df_train_neutral_swapped["total_intl_goals_diff"]
    df_train_neutral_swapped["joint_squad_age_diff"] = -df_train_neutral_swapped["joint_squad_age_diff"]
    df_train_neutral_swapped["avg_squad_height_diff_cm"] = -df_train_neutral_swapped["avg_squad_height_diff_cm"]
    df_train_neutral_swapped["confederation_strength_a"], df_train_neutral_swapped["confederation_strength_b"] = \
        df_train_neutral_swapped["confederation_strength_b"], df_train_neutral_swapped["confederation_strength_a"]
    df_train_neutral_swapped["host_nation_flag"] = -df_train_neutral_swapped["host_nation_flag"]
    df_train_neutral_swapped["head_to_head_elo_record"] = -df_train_neutral_swapped["head_to_head_elo_record"]
    
    return pd.concat([df_train_non_neutral, df_train_neutral, df_train_neutral_swapped], ignore_index=True)

start_years = [1993, 2005, 2010, 2014, 2018]

for year in start_years:
    for sym in [False, True]:
        df_train_raw = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
        if sym:
            df_train = get_symmetric_train_data(df_train_raw)
        else:
            df_train = df_train_raw.copy()
            
        X_train = df_train[feat_list]
        y_train = df_train["outcome"].astype(int)
        X_val = df_val[feat_list]
        y_val = df_val["outcome"].astype(int)
        
        imp = SimpleImputer(strategy="median")
        scaler = RobustScaler()
        X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
        X_val_proc = scaler.transform(imp.transform(X_val))
        
        model = HistGradientBoostingClassifier(
            max_depth=1,
            learning_rate=0.03,
            max_iter=100,
            l2_regularization=10.0,
            random_state=42
        )
        cal = CalibratedClassifierCV(estimator=model, method="sigmoid", cv=5)
        cal.fit(X_train_proc, y_train)
        probs = cal.predict_proba(X_val_proc)
        
        classes = cal.classes_
        idx_0 = np.where(classes == 0)[0][0]
        idx_1 = np.where(classes == 1)[0][0]
        idx_2 = np.where(classes == 2)[0][0]
        
        auc_0 = roc_auc_score((y_val == 0).astype(int), probs[:, idx_0])
        auc_1 = roc_auc_score((y_val == 1).astype(int), probs[:, idx_1])
        auc_2 = roc_auc_score((y_val == 2).astype(int), probs[:, idx_2])
        
        print(f"Year: {year} | Sym: {sym} | AUCs: [Draw: {auc_0:.4f}, Win: {auc_1:.4f}, Loss: {auc_2:.4f}]")
