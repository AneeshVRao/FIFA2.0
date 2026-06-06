import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, accuracy_score
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

df_train = df[(df["date"] >= "2018-01-01") & (df["date"] < "2022-11-20")].copy()

for feat_name, feat_list in feature_subsets.items():
    X_train = df_train[feat_list]
    y_train = df_train["outcome"].astype(int)
    X_val = df_val[feat_list]
    y_val = df_val["outcome"].astype(int)
    
    imp = SimpleImputer(strategy="median")
    scaler = RobustScaler()
    X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
    X_val_proc = scaler.transform(imp.transform(X_val))
    
    # HistGBM
    for max_depth in [2, 3]:
        for lr in [0.03, 0.05]:
            for max_iter in [100, 200]:
                for l2 in [0.5, 10.0]:
                    model = HistGradientBoostingClassifier(
                        max_depth=max_depth,
                        learning_rate=lr,
                        max_iter=max_iter,
                        l2_regularization=l2,
                        random_state=42
                    )
                    model.fit(X_train_proc, y_train)
                    probs = model.predict_proba(X_val_proc)
                    
                    classes = model.classes_
                    idx_0 = np.where(classes == 0)[0][0]
                    idx_1 = np.where(classes == 1)[0][0]
                    idx_2 = np.where(classes == 2)[0][0]
                    
                    auc_0 = roc_auc_score((y_val == 0).astype(int), probs[:, idx_0])
                    auc_1 = roc_auc_score((y_val == 1).astype(int), probs[:, idx_1])
                    auc_2 = roc_auc_score((y_val == 2).astype(int), probs[:, idx_2])
                    
                    if auc_1 >= 0.73:
                        print(f"HistGBM | feats: {feat_name} | depth: {max_depth} | lr: {lr} | iter: {max_iter} | l2: {l2} | AUCs: [Draw: {auc_0:.4f}, Win: {auc_1:.4f}, Loss: {auc_2:.4f}]")
                        
    # XGBoost
    for max_depth in [2, 3, 5]:
        for lr in [0.03, 0.05]:
            for n_est in [100, 200]:
                model = xgb.XGBClassifier(
                    max_depth=max_depth,
                    learning_rate=lr,
                    n_estimators=n_est,
                    random_state=42
                )
                model.fit(X_train_proc, y_train)
                probs = model.predict_proba(X_val_proc)
                
                classes = model.classes_
                idx_0 = np.where(classes == 0)[0][0]
                idx_1 = np.where(classes == 1)[0][0]
                idx_2 = np.where(classes == 2)[0][0]
                
                auc_0 = roc_auc_score((y_val == 0).astype(int), probs[:, idx_0])
                auc_1 = roc_auc_score((y_val == 1).astype(int), probs[:, idx_1])
                auc_2 = roc_auc_score((y_val == 2).astype(int), probs[:, idx_2])
                
                if auc_1 >= 0.73:
                    print(f"XGBoost | feats: {feat_name} | depth: {max_depth} | lr: {lr} | n_est: {n_est} | AUCs: [Draw: {auc_0:.4f}, Win: {auc_1:.4f}, Loss: {auc_2:.4f}]")
