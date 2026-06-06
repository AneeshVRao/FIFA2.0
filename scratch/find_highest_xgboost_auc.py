import duckdb
import pandas as pd
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score
import xgboost as xgb

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

feature_subsets = {
    "all": features,
    "no_physio": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag", "total_caps_diff", "total_intl_goals_diff", "confederation_strength_a", "confederation_strength_b", "historic_fifa_points_diff", "head_to_head_elo_record"],
    "top_3": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag"]
}

start_years = [2005, 2010, 2014, 2018]

for year in start_years:
    df_train_raw = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
    
    for feat_name, feat_list in feature_subsets.items():
        for sym in [False, True]:
            # Generate training data
            if sym:
                df_train_neutral = df_train_raw[df_train_raw["neutral"] == True].copy()
                df_train_non_neutral = df_train_raw[df_train_raw["neutral"] == False].copy()
                df_train_neutral_swapped = df_train_neutral.copy()
                
                def swap_outcome(o):
                    if o == 1: return 2
                    if o == 2: return 1
                    return 0
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
                
                df_train = pd.concat([df_train_non_neutral, df_train_neutral, df_train_neutral_swapped], ignore_index=True)
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
            
            for max_depth in [2, 3, 5]:
                for lr in [0.03, 0.05]:
                    for n_est in [100, 200]:
                        model = xgb.XGBClassifier(
                            max_depth=max_depth,
                            learning_rate=lr,
                            n_estimators=n_est,
                            random_state=42
                        )
                        try:
                            # Calibrate to get true probabilities
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
                            
                            # Custom thresholds
                            for dt in np.linspace(0.20, 0.35, 7):
                                for diff in np.linspace(0.05, 0.30, 11):
                                    preds = []
                                    for prob in probs:
                                        p0 = prob[idx_0]
                                        p1 = prob[idx_1]
                                        p2 = prob[idx_2]
                                        if p0 > dt and abs(p1 - p2) < diff:
                                            preds.append(0)
                                        else:
                                            preds.append(1 if p1 > p2 else 2)
                                    preds = np.array(preds)
                                    acc = accuracy_score(y_val, preds)
                                    f1 = f1_score(y_val, preds, average="macro")
                                    
                                    if acc >= 0.57 and f1 >= 0.42 and auc_0 >= 0.58 and auc_1 >= 0.75:
                                        print(f"XGBoost | year: {year} | feats: {feat_name} | sym: {sym} | depth: {max_depth} | lr: {lr} | n_est: {n_est} | dt: {dt:.2f} | diff: {diff:.2f} | Acc: {acc:.4f} | F1: {f1:.4f} | Draw AUC: {auc_0:.4f} | Win AUC: {auc_1:.4f} | Loss AUC: {auc_2:.4f}")
                        except Exception as e:
                            pass
