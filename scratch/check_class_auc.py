import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score

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

# Config 1: Start Year 2010, HistGBM, all features
df_tr_1 = df[(df["date"] >= "2010-01-01") & (df["date"] < "2022-11-20")].copy()
X_tr_1 = df_tr_1[features]
y_tr_1 = df_tr_1["outcome"].astype(int)
X_val = df_val[features]
y_val = df_val["outcome"].astype(int)

imp = SimpleImputer(strategy="median")
scaler = RobustScaler()
X_tr_1_proc = scaler.fit_transform(imp.fit_transform(X_tr_1))
X_val_proc = scaler.transform(imp.transform(X_val))

base_1 = HistGradientBoostingClassifier(
    max_depth=3,
    learning_rate=0.03,
    max_iter=200,
    l2_regularization=0.5,
    random_state=42
)
cal_1 = CalibratedClassifierCV(estimator=base_1, method="sigmoid", cv=5)
cal_1.fit(X_tr_1_proc, y_tr_1)
probs_1 = cal_1.predict_proba(X_val_proc)

print("=== 2010 HistGBM (all features) ===")
classes = cal_1.classes_
for i, c in enumerate(classes):
    y_true_c = (y_val == c).astype(int)
    auc_c = roc_auc_score(y_true_c, probs_1[:, i])
    print(f"Class {c} AUC-ROC: {auc_c:.4f}")

# Config 2: Start Year 2018, HistGBM, all features
df_tr_2 = df[(df["date"] >= "2018-01-01") & (df["date"] < "2022-11-20")].copy()
X_tr_2 = df_tr_2[features]
y_tr_2 = df_tr_2["outcome"].astype(int)

X_tr_2_proc = scaler.fit_transform(imp.fit_transform(X_tr_2))
X_val_proc = scaler.transform(imp.transform(X_val))

base_2 = HistGradientBoostingClassifier(
    max_depth=3,
    learning_rate=0.03,
    max_iter=200,
    l2_regularization=0.5,
    random_state=42
)
cal_2 = CalibratedClassifierCV(estimator=base_2, method="sigmoid", cv=5)
cal_2.fit(X_tr_2_proc, y_tr_2)
probs_2 = cal_2.predict_proba(X_val_proc)

print("\n=== 2018 HistGBM (all features) ===")
for i, c in enumerate(classes):
    y_true_c = (y_val == c).astype(int)
    auc_c = roc_auc_score(y_true_c, probs_2[:, i])
    print(f"Class {c} AUC-ROC: {auc_c:.4f}")
