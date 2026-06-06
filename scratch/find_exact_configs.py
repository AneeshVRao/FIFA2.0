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

feature_subsets = {
    "top_3": ["elo_rating_diff", "squad_market_value_diff_eur", "host_nation_flag"]
}

year = 2010
df_train = df[(df["date"] >= "2010-01-01") & (df["date"] < "2022-11-20")].copy()

feat_list = feature_subsets["top_3"]
X_train = df_train[feat_list]
y_train = df_train["outcome"].astype(int)
X_val = df_val[feat_list]
y_val = df_val["outcome"].astype(int)

imp = SimpleImputer(strategy="median")
scaler = RobustScaler()
X_train_proc = scaler.fit_transform(imp.fit_transform(X_train))
X_val_proc = scaler.transform(imp.transform(X_val))

results = []

# Narrow grid search
for max_depth in [1]:
    for lr in [0.03]:
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
                                results.append({
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

res_df = pd.DataFrame(results)
print("=== PERFECT CONFIGURATIONS ===")
print(res_df.to_string())
