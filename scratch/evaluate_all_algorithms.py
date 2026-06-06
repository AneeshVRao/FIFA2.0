import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
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

algorithms = {
    "random_forest": RandomForestClassifier(n_estimators=300, max_depth=4, random_state=42),
    "logistic": LogisticRegression(C=0.1, random_state=42),
    "xgboost": xgb.XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.03, random_state=42)
}

start_years = [2010, 2018]

for year in start_years:
    df_train = df[(df["date"] >= f"{year}-01-01") & (df["date"] < "2022-11-20")].copy()
    X_train = df_train[features]
    y_train = df_train["outcome"].astype(int)
    X_val = df_val[features]
    y_val = df_val["outcome"].astype(int)
    
    imp = SimpleImputer(strategy="median")
    scaler = RobustScaler()
    X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
    X_val_proc = scaler.transform(imp.transform(X_val))
    
    for alg_name, model in algorithms.items():
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
            
            # Draw threshold sweep to find best acc/f1
            best_acc = 0.0
            best_f1 = 0.0
            for dt in np.linspace(0.20, 0.35, 16):
                for diff in np.linspace(0.05, 0.30, 26):
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
                    if acc > best_acc:
                        best_acc = acc
                        best_f1 = f1
            print(f"Year: {year} | Alg: {alg_name} | AUCs: [Draw: {auc_0:.4f}, Win: {auc_1:.4f}, Loss: {auc_2:.4f}] | Best possible Acc: {best_acc:.4f}, F1: {best_f1:.4f}")
        except Exception as e:
            print(f"Error {alg_name}: {e}")
