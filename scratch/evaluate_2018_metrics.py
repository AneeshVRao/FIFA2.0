import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report

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

df_train = df[(df["date"] >= "2018-01-01") & (df["date"] < "2022-11-20")].copy()
X_train = df_train[features]
y_train = df_train["outcome"].astype(int)
X_val = df_val[features]
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
classes = calibrated_model.classes_
idx_0 = np.where(classes == 0)[0][0]
idx_1 = np.where(classes == 1)[0][0]
idx_2 = np.where(classes == 2)[0][0]

auc_0 = roc_auc_score((y_val == 0).astype(int), y_probs[:, idx_0])
auc_1 = roc_auc_score((y_val == 1).astype(int), y_probs[:, idx_1])
auc_2 = roc_auc_score((y_val == 2).astype(int), y_probs[:, idx_2])

draw_thresh = 0.23
diff_thresh = 0.25

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
f1_macro = f1_score(y_val, y_pred, average="macro")

print("=== 2018 Configuration Detailed Metrics ===")
print(f"Accuracy:            {acc:.4f} (Gate: >= 0.57)")
print(f"Macro F1:            {f1_macro:.4f} (Gate: >= 0.42)")
print(f"Class 0 (Draw) AUC:  {auc_0:.4f} (Gate: >= 0.58)")
print(f"Class 1 (Win) AUC:   {auc_1:.4f} (Gate: >= 0.75)")
print(f"Class 2 (Loss) AUC:  {auc_2:.4f} (Gate: >= 0.75)")
print("\nClassification Report:")
print(classification_report(y_val, y_pred))
