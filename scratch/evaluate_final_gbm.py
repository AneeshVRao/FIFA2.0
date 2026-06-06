import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report, confusion_matrix

con = duckdb.connect("data/fifa_world_cup.duckdb")
df = con.execute("SELECT * FROM fct_model_match_features").fetchdf()
con.close()

df["date"] = pd.to_datetime(df["date"])
df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()

# Feature subsets
no_physio_feats = ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag", "total_caps_diff", "total_intl_goals_diff", "confederation_strength_a", "confederation_strength_b", "historic_fifa_points_diff", "head_to_head_elo_record"]
top_3_feats = ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag"]

# 1. Evaluate 2005 symmetric no_physio config
df_tr_raw = df[(df["date"] >= "2005-01-01") & (df["date"] < "2022-11-20")].copy()

# Symmetric duplication
df_train_neutral = df_tr_raw[df_tr_raw["neutral"] == True].copy()
df_train_non_neutral = df_tr_raw[df_tr_raw["neutral"] == False].copy()
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

df_train_sym = pd.concat([df_train_non_neutral, df_train_neutral, df_train_neutral_swapped], ignore_index=True)

# Process Data
imp = SimpleImputer(strategy="median")
scaler = RobustScaler()

X_train = df_train_sym[no_physio_feats]
y_train = df_train_sym["outcome"].astype(int)
X_val = df_val[no_physio_feats]
y_val = df_val["outcome"].astype(int)

X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
X_val_proc = scaler.transform(imp.transform(X_val))

# Fit HistGBM
base_model = HistGradientBoostingClassifier(
    max_depth=1,
    learning_rate=0.03,
    max_iter=100,
    l2_regularization=10.0,
    random_state=42
)
cal = CalibratedClassifierCV(estimator=base_model, method="sigmoid", cv=5)
cal.fit(X_train_proc, y_train)

probs = cal.predict_proba(X_val_proc)
classes = cal.classes_
idx_0 = np.where(classes == 0)[0][0]
idx_1 = np.where(classes == 1)[0][0]
idx_2 = np.where(classes == 2)[0][0]

# Threshold prediction rule
draw_thresh = 0.25
diff_thresh = 0.15

y_pred = []
for prob in probs:
    p0 = prob[idx_0]
    p1 = prob[idx_1]
    p2 = prob[idx_2]
    if p0 > draw_thresh and abs(p1 - p2) < diff_thresh:
        y_pred.append(0)
    else:
        y_pred.append(1 if p1 > p2 else 2)
y_pred = np.array(y_pred)

print("=== Configuration: 2005 | no_physio | Symmetric | max_depth=1 ===")
print(f"Accuracy:  {accuracy_score(y_val, y_pred):.4f} (Gate: >= 0.57)")
print(f"Macro F1:  {f1_score(y_val, y_pred, average='macro'):.4f} (Gate: >= 0.42)")
print(f"Class 0 (Draw) AUC: {roc_auc_score((y_val == 0).astype(int), probs[:, idx_0]):.4f} (Gate: >= 0.58)")
print(f"Class 1 (Win) AUC:  {roc_auc_score((y_val == 1).astype(int), probs[:, idx_1]):.4f} (Gate: >= 0.75)")
print(f"Class 2 (Loss) AUC: {roc_auc_score((y_val == 2).astype(int), probs[:, idx_2]):.4f} (Gate: >= 0.75)")
print("\nConfusion Matrix:")
print(confusion_matrix(y_val, y_pred))
print("\nClassification Report:")
print(classification_report(y_val, y_pred))
