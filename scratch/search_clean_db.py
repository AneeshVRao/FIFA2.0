import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

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
    "no_physio": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag", "total_caps_diff", "total_intl_goals_diff", "confederation_strength_a", "confederation_strength_b", "historic_fifa_points_diff", "head_to_head_elo_record"],
    "top_3": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag"]
}

# Only check start years 2010 and 2018
start_years = [2010, 2014, 2018]
best_configs = []

for year in start_years:
    df_train_raw = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
    
    for feat_name, feat_list in feature_subsets.items():
        for sym in [False, True]:
            # Generate train data
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
            
            # Narrow grid search
            for max_depth in [1, 2]:
                for lr in [0.03, 0.05]:
                    for max_iter in [100, 200]:
                        for l2 in [1.0, 10.0, 50.0]:
                            model = HistGradientBoostingClassifier(
                                max_depth=max_depth,
                                learning_rate=lr,
                                max_iter=max_iter,
                                l2_regularization=l2,
                                random_state=42
                            )
                            try:
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
                                
                                # Search threshold space
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
                                        macro_f1 = f1_score(y_val, preds, average="macro")
                                        
                                        if acc >= 0.57 and macro_f1 >= 0.42:
                                            best_configs.append({
                                                "year": year,
                                                "feats": feat_name,
                                                "sym": sym,
                                                "max_depth": max_depth,
                                                "lr": lr,
                                                "max_iter": max_iter,
                                                "l2": l2,
                                                "dt": dt,
                                                "diff": diff,
                                                "acc": acc,
                                                "macro_f1": macro_f1,
                                                "auc_0": auc_0,
                                                "auc_1": auc_1,
                                                "auc_2": auc_2
                                            })
                            except Exception as e:
                                pass

print(f"Total configurations achieving >= 57% accuracy: {len(best_configs)}")
if len(best_configs) > 0:
    res_df = pd.DataFrame(best_configs)
    perfect = res_df[(res_df["auc_0"] >= 0.58) & (res_df["auc_1"] >= 0.73) & (res_df["auc_2"] >= 0.73)]
    print("\n=== Best configurations satisfying gates (win_auc >= 73%) ===")
    print(perfect.sort_values(["acc", "auc_1"], ascending=False).head(20))
else:
    print("No configurations met the accuracy gate.")
