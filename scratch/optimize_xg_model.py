import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
from xgboost import XGBClassifier

con = duckdb.connect("data/fifa_world_cup.duckdb")
df = con.execute("SELECT * FROM fct_model_xg_features").fetchdf()
con.close()

df_train = df[df["season_id"] == 3].copy()
df_val = df[df["season_id"] == 106].copy()

features = [
    "distance_to_goal_m", 
    "angle_to_goal_deg", 
    "defenders_in_cone", 
    "defensive_pressure_m",
    "goalkeeper_distance"
]

X_train = df_train[features]
y_train = df_train["is_goal"]
X_val = df_val[features]
y_val = df_val["is_goal"]

imp = SimpleImputer(strategy="median")
scaler = RobustScaler()
X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
X_val_proc = scaler.transform(imp.transform(X_val))

# Try different models
models = {
    "xgb_default": XGBClassifier(n_estimators=500, max_depth=5, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8, gamma=1.0, random_state=42),
    "xgb_simple": XGBClassifier(n_estimators=50, max_depth=2, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_lambda=10.0, random_state=42),
    "xgb_very_simple": XGBClassifier(n_estimators=20, max_depth=1, learning_rate=0.05, reg_lambda=50.0, random_state=42),
    "logistic": LogisticRegression(C=0.1, random_state=42),
    "logistic_l1": LogisticRegression(C=0.05, penalty="l1", solver="liblinear", random_state=42)
}

for name, model in models.items():
    try:
        # Fit calibrated classifier
        cal = CalibratedClassifierCV(estimator=model, method="sigmoid", cv=5)
        cal.fit(X_train_proc, y_train)
        
        probs = cal.predict_proba(X_val_proc)[:, 1]
        
        auc = roc_auc_score(y_val, probs)
        loss = log_loss(y_val, probs)
        brier = brier_score_loss(y_val, probs)
        
        print(f"Model: {name:15} | AUC: {auc:.4f} | Log Loss: {loss:.4f} (Gate: <= 0.28) | Brier: {brier:.4f} (Gate: <= 0.07)")
    except Exception as e:
        print(f"Error {name}: {e}")
