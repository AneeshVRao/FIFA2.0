import os
import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

def test():
    db_path = "data/fifa_world_cup.duckdb"
    con = duckdb.connect(db_path)
    df = con.execute("SELECT * FROM fct_model_match_features").fetchdf()
    df["date"] = pd.to_datetime(df["date"])
    con.close()
    
    # Validation = 2022 World Cup matches
    df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()
    
    features = [
        "elo_rating_diff",
        "squad_market_value_diff_eur",
        "host_nation_flag",
        "neutral",
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
        "shared_club_minutes",
        "avg_squad_height_diff_cm",
        "historic_fifa_points_diff",
        "match_stage_pressure",
        "head_to_head_elo_record"
    ]
    
    # We want to perform symmetric duplication for neutral matches in the training set
    start_years = [1993, 2005, 2010, 2014, 2018]
    
    for year in start_years:
        df_train = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
        
        # Split neutral and non-neutral training matches
        df_train_neutral = df_train[df_train["neutral"] == True].copy()
        df_train_non_neutral = df_train[df_train["neutral"] == False].copy()
        
        # Duplicate neutral matches with swapped features
        df_train_neutral_swapped = df_train_neutral.copy()
        
        # Swap outcomes: 1 -> 2, 2 -> 1, 0 -> 0
        def swap_outcome(o):
            if o == 1: return 2
            if o == 2: return 1
            return 0
        df_train_neutral_swapped["outcome"] = df_train_neutral_swapped["outcome"].apply(swap_outcome)
        
        # Swap home and away team designations
        df_train_neutral_swapped["home_team"], df_train_neutral_swapped["away_team"] = \
            df_train_neutral_swapped["away_team"], df_train_neutral_swapped["home_team"]
            
        # Swap Elo ratings
        df_train_neutral_swapped["elo_home"], df_train_neutral_swapped["elo_away"] = \
            df_train_neutral_swapped["elo_away"], df_train_neutral_swapped["elo_home"]
        df_train_neutral_swapped["elo_rating_diff"] = -df_train_neutral_swapped["elo_rating_diff"]
        
        # Swap squad values
        df_train_neutral_swapped["squad_market_value_home"], df_train_neutral_swapped["squad_market_value_away"] = \
            df_train_neutral_swapped["squad_market_value_away"], df_train_neutral_swapped["squad_market_value_home"]
        df_train_neutral_swapped["squad_market_value_diff_eur"] = -df_train_neutral_swapped["squad_market_value_diff_eur"]
        
        # Swap travel
        df_train_neutral_swapped["team_a_travel_km"], df_train_neutral_swapped["team_b_travel_km"] = \
            df_train_neutral_swapped["team_b_travel_km"], df_train_neutral_swapped["team_a_travel_km"]
            
        # Swap caps, goals, confederations, age, height
        df_train_neutral_swapped["total_caps_diff"] = -df_train_neutral_swapped["total_caps_diff"]
        df_train_neutral_swapped["total_intl_goals_diff"] = -df_train_neutral_swapped["total_intl_goals_diff"]
        df_train_neutral_swapped["joint_squad_age_diff"] = -df_train_neutral_swapped["joint_squad_age_diff"]
        df_train_neutral_swapped["avg_squad_height_diff_cm"] = -df_train_neutral_swapped["avg_squad_height_diff_cm"]
        df_train_neutral_swapped["confederation_strength_a"], df_train_neutral_swapped["confederation_strength_b"] = \
            df_train_neutral_swapped["confederation_strength_b"], df_train_neutral_swapped["confederation_strength_a"]
            
        # Swap host flag and head-to-head
        df_train_neutral_swapped["host_nation_flag"] = -df_train_neutral_swapped["host_nation_flag"]
        df_train_neutral_swapped["head_to_head_elo_record"] = -df_train_neutral_swapped["head_to_head_elo_record"]
        
        # Combine everything back
        df_train_augmented = pd.concat([df_train_non_neutral, df_train_neutral, df_train_neutral_swapped], ignore_index=True)
        
        X_train = df_train_augmented[features]
        y_train = df_train_augmented["outcome"].astype(int)
        X_val = df_val[features]
        y_val = df_val["outcome"].astype(int)
        
        # Hyperparameters for training
        base_model = HistGradientBoostingClassifier(
            max_depth=3,
            learning_rate=0.03,
            max_iter=300,
            l2_regularization=0.5,
            random_state=42
        )
        
        calibrated_model = CalibratedClassifierCV(
            estimator=base_model,
            method="sigmoid",
            cv=5
        )
        
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
            ("model", calibrated_model)
        ])
        
        pipeline.fit(X_train, y_train)
        
        y_pred = pipeline.predict(X_val)
        y_probs = pipeline.predict_proba(X_val)
        
        acc = accuracy_score(y_val, y_pred)
        auc = roc_auc_score(y_val, y_probs, multi_class="ovr")
        
        # Check predictions distribution
        preds_dist = pd.Series(y_pred).value_counts().to_dict()
        
        print(f"Start Year: {year} | Augmented Train Matches: {len(df_train_augmented)} -> Acc: {acc:.4f} | AUC: {auc:.4f} | Preds: {preds_dist}")

if __name__ == "__main__":
    test()
