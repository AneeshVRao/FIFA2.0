import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

con = duckdb.connect("data/fifa_world_cup.duckdb")
df = con.execute("SELECT * FROM fct_model_match_features").fetchdf()
con.close()

df["date"] = pd.to_datetime(df["date"])
df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()

# 1. Train data identical to match_model.py
df_train_raw = df[(df["date"] >= "2005-01-01") & (df["date"] < "2022-11-20")].copy()
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

features = [
    "elo_rating_diff",
    "squad_market_value_diff_eur",
    "host_nation_flag",
    "total_caps_diff",
    "total_intl_goals_diff",
    "confederation_strength_a",
    "confederation_strength_b",
    "historic_fifa_points_diff",
    "head_to_head_elo_record"
]

X_train = df_train[features]
y_train = df_train["outcome"].astype(int)
X_val = df_val[features]
y_val = df_val["outcome"].astype(int)

# Fit pipeline way (Method A)
base_model = HistGradientBoostingClassifier(
    max_depth=1,
    learning_rate=0.03,
    max_iter=200,
    l2_regularization=10.0,
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
probs_a = pipeline.predict_proba(X_val)

# Fit direct way (Method B)
imp = SimpleImputer(strategy="median")
scaler = RobustScaler()
X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
X_val_proc = scaler.transform(imp.transform(X_val))

base_model_b = HistGradientBoostingClassifier(
    max_depth=1,
    learning_rate=0.03,
    max_iter=200,
    l2_regularization=10.0,
    random_state=42
)
cal_b = CalibratedClassifierCV(estimator=base_model_b, method="sigmoid", cv=5)
cal_b.fit(X_train_proc, y_train)
probs_b = cal_b.predict_proba(X_val_proc)

print("Are probabilities identical?", np.allclose(probs_a, probs_b))

# Evaluate A
classes = pipeline.named_steps["model"].classes_
idx_0 = np.where(classes == 0)[0][0]
idx_1 = np.where(classes == 1)[0][0]
idx_2 = np.where(classes == 2)[0][0]

y_pred_a = []
for prob in probs_a:
    p0 = prob[idx_0]
    p1 = prob[idx_1]
    p2 = prob[idx_2]
    if p0 > 0.25 and abs(p1 - p2) < 0.15:
        y_pred_a.append(0)
    else:
        y_pred_a.append(1 if p1 > p2 else 2)
y_pred_a = np.array(y_pred_a)
print("Method A Accuracy:", accuracy_score(y_val, y_pred_a))

# Evaluate B
classes_b = cal_b.classes_
idx_0b = np.where(classes_b == 0)[0][0]
idx_1b = np.where(classes_b == 1)[0][0]
idx_2b = np.where(classes_b == 2)[0][0]

y_pred_b = []
for prob in probs_b:
    p0 = prob[idx_0b]
    p1 = prob[idx_1b]
    p2 = prob[idx_2b]
    if p0 > 0.25 and abs(p1 - p2) < 0.15:
        y_pred_b.append(0)
    else:
        y_pred_b.append(1 if p1 > p2 else 2)
y_pred_b = np.array(y_pred_b)
print("Method B Accuracy:", accuracy_score(y_val, y_pred_b))
