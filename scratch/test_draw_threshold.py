import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, confusion_matrix

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

# We will test symmetric duplication
def get_symmetric_train_data(df_train, feats):
    df_train_neutral = df_train[df_train["neutral"] == True].copy()
    df_train_non_neutral = df_train[df_train["neutral"] == False].copy()
    
    df_train_neutral_swapped = df_train_neutral.copy()
    
    def swap_outcome(o):
        if o == 1: return 2
        if o == 2: return 1
        return 0
    df_train_neutral_swapped["outcome"] = df_train_neutral_swapped["outcome"].apply(swap_outcome)
    df_train_neutral_swapped["home_team"], df_train_neutral_swapped["away_team"] = \
        df_train_neutral_swapped["away_team"], df_train_neutral_swapped["home_team"]
        
    df_train_neutral_swapped["elo_home"], df_train_neutral_swapped["elo_away"] = \
        df_train_neutral_swapped["elo_away"], df_train_neutral_swapped["elo_home"]
    df_train_neutral_swapped["elo_rating_diff"] = -df_train_neutral_swapped["elo_rating_diff"]
    
    df_train_neutral_swapped["squad_market_value_home"], df_train_neutral_swapped["squad_market_value_away"] = \
        df_train_neutral_swapped["squad_market_value_away"], df_train_neutral_swapped["squad_market_value_home"]
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
    
    df_train_augmented = pd.concat([df_train_non_neutral, df_train_neutral, df_train_neutral_swapped], ignore_index=True)
    return df_train_augmented

start_years = [1993, 2005, 2010, 2014, 2018]
feature_subsets = {
    "all": features,
    "top_5": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag", "head_to_head_elo_record", "total_caps_diff"],
    "top_3": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag"],
    "elo_only": ["elo_rating_diff"]
}

best_acc = 0.0
best_cfg = None

# Grid search with custom thresholding
for year in start_years:
    df_train_raw = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
    
    for feat_name, feat_list in feature_subsets.items():
        for sym in [False, True]:
            if sym:
                df_train = get_symmetric_train_data(df_train_raw, feat_list)
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
            
            base_model = HistGradientBoostingClassifier(
                max_depth=3,
                learning_rate=0.03,
                max_iter=200,
                l2_regularization=0.5,
                random_state=42
            )
            calibrated_model = CalibratedClassifierCV(
                estimator=base_model,
                method="sigmoid",
                cv=5
            )
            calibrated_model.fit(X_train_proc, y_train)
            
            y_probs = calibrated_model.predict_proba(X_val_proc)
            
            # Experiment with draw thresholds
            # y_probs order is usually: [P_0, P_1, P_2] (since classes are sorted: 0, 1, 2)
            # Let's verify class order
            classes = calibrated_model.classes_
            idx_0 = np.where(classes == 0)[0][0]
            idx_1 = np.where(classes == 1)[0][0]
            idx_2 = np.where(classes == 2)[0][0]
            
            # Predict draw if P_0 > threshold, else argmax(P_1, P_2)
            # Or if |P_1 - P_2| < diff_threshold and P_0 > min_draw_p
            for draw_thresh in np.linspace(0.2, 0.4, 21):
                for diff_thresh in np.linspace(0.05, 0.25, 21):
                    y_pred = []
                    for prob in y_probs:
                        p0 = prob[idx_0]
                        p1 = prob[idx_1]
                        p2 = prob[idx_2]
                        
                        if p0 > draw_thresh and abs(p1 - p2) < diff_thresh:
                            y_pred.append(0)
                        else:
                            y_pred.append(1 if p1 > p2 else 2)
                            
                    y_pred = np.array(y_pred)
                    acc = accuracy_score(y_val, y_pred)
                    
                    if acc > best_acc:
                        best_acc = acc
                        best_cfg = {
                            "year": year,
                            "feats": feat_name,
                            "sym": sym,
                            "draw_thresh": draw_thresh,
                            "diff_thresh": diff_thresh,
                            "acc": acc,
                            "preds": pd.Series(y_pred).value_counts().to_dict(),
                            "conf": confusion_matrix(y_val, y_pred)
                        }

print("=== Best Configuration ===")
for k, v in best_cfg.items():
    print(f"{k}: {v}")
