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
    
    df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()
    
    # Feature set with neutral flag
    features = [
        "elo_rating_diff",
        "squad_market_value_diff_eur",
        "host_nation_flag",
        "neutral",  # Added neutral flag
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
    
    start_years = [1993, 2005, 2010, 2014, 2018]
    
    for year in start_years:
        df_train = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
        
        X_train = df_train[features]
        y_train = df_train["outcome"].astype(int)
        X_val = df_val[features]
        y_val = df_val["outcome"].astype(int)
        
        base_model = HistGradientBoostingClassifier(
            max_depth=3,
            learning_rate=0.05,
            max_iter=300,
            l2_regularization=0.1,
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
        
        print(f"Start Year: {year} with Neutral -> Acc: {acc:.4f} | AUC: {auc:.4f}")

if __name__ == "__main__":
    test()
