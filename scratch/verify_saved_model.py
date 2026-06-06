import joblib
import pandas as pd
import numpy as np

model_path = "models/match_outcome_v1.pkl"
print("Loading model...")
model = joblib.load(model_path)
print("Loaded successfully!")
print("Wrapper class:", model.__class__.__name__)

# Create dummy input data with same features
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
X_dummy = pd.DataFrame([{
    "elo_rating_diff": 100.0,
    "squad_market_value_diff_eur": 500000000.0,
    "host_nation_flag": 0,
    "total_caps_diff": 100,
    "total_intl_goals_diff": 20,
    "confederation_strength_a": 0.60,
    "confederation_strength_b": 0.60,
    "historic_fifa_points_diff": 100.0,
    "head_to_head_elo_record": 0.1
}])

print("\nFeatures:", features)
print("Running predict_proba...")
probs = model.predict_proba(X_dummy)
print("Probabilities:", probs)
print("Probability sum:", np.sum(probs))

print("\nRunning predict...")
pred = model.predict(X_dummy)
print("Predicted outcome:", pred)
