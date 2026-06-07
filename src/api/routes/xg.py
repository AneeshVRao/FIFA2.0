import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException, Request
from src.api.schemas import XGRequest, XGResponse, DerivedSpatialMetrics, SHAPContribution
from src.transformation.features import compute_distance, compute_angle

router = APIRouter(prefix="/predictions", tags=["xg"])

@router.post("/xg", response_model=XGResponse)
async def predict_xg(req: XGRequest, request: Request):
    """
    Evaluates shot quality by calculating distance/angle and running the
    calibrated XGBoost xG model. Computes local SHAP attributions.
    """
    # Verify loaded model
    xg_model = getattr(request.app.state, "xg_model", None)
    if xg_model is None:
        raise HTTPException(status_code=500, detail="XGBoost xG model is not loaded on server.")

    # 1. Compute spatial metrics (distance & angle)
    distance = compute_distance(req.shot_x, req.shot_y)
    angle = compute_angle(req.shot_x, req.shot_y)
    
    # 2. Prepare inputs for prediction
    # Feature columns in order:
    # ["distance_to_goal_m", "angle_to_goal_deg", "defenders_in_cone", "defensive_pressure_m", "goalkeeper_distance"]
    gk_dist = 5.0  # default goalkeeper distance fallback
    
    input_df = pd.DataFrame([{
        "distance_to_goal_m": distance,
        "angle_to_goal_deg": angle,
        "defenders_in_cone": float(req.defenders_in_cone),
        "defensive_pressure_m": float(req.defensive_pressure_m),
        "goalkeeper_distance": gk_dist
    }])
    
    try:
        # Run calibrated model prediction
        prob = float(xg_model.predict_probability(input_df)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model execution failed: {str(e)}")

    # Danger classification
    if prob < 0.05:
        danger = "low"
    elif prob < 0.15:
        danger = "medium"
    elif prob < 0.35:
        danger = "high"
    else:
        danger = "extreme"

    # 3. Local SHAP Attribution Approximation (Omission Method from baseline)
    # Baseline represents a standard shot: 12.0m distance, 30.0 deg angle, 0 defenders, 5.0m pressure, 5.0m gk_dist
    baseline = {
        "distance_to_goal_m": 12.0,
        "angle_to_goal_deg": 30.0,
        "defenders_in_cone": 0.0,
        "defensive_pressure_m": 5.0,
        "goalkeeper_distance": 5.0
    }
    
    baseline_df = pd.DataFrame([baseline])
    p_base = float(xg_model.predict_probability(baseline_df)[0])
    
    features_list = [
        "distance_to_goal_m",
        "angle_to_goal_deg",
        "defenders_in_cone",
        "defensive_pressure_m"
    ]
    
    raw_shaps = {}
    for feat in features_list:
        # Create a hybrid state: replace current feature with baseline value
        hybrid = {
            "distance_to_goal_m": distance,
            "angle_to_goal_deg": angle,
            "defenders_in_cone": float(req.defenders_in_cone),
            "defensive_pressure_m": float(req.defensive_pressure_m),
            "goalkeeper_distance": gk_dist
        }
        hybrid[feat] = baseline[feat]
        hybrid_df = pd.DataFrame([hybrid])
        p_hybrid = float(xg_model.predict_probability(hybrid_df)[0])
        # SHAP contribution of feature is actual - state_without_feature
        raw_shaps[feat] = prob - p_hybrid

    # Normalize contributions so they sum to total deviation from baseline
    total_dev = prob - p_base
    sum_shaps = sum(raw_shaps.values())
    
    shap_attribs = []
    for feat, val in raw_shaps.items():
        # Distribute residual evenly if sum of shaps is non-zero
        adjusted_val = val
        if sum_shaps != 0:
            adjusted_val = val * (total_dev / sum_shaps)
        shap_attribs.append(SHAPContribution(feature=feat, shap_value=float(adjusted_val)))
        
    derived = DerivedSpatialMetrics(
        distance_to_goal_m=distance,
        angle_to_goal_deg=angle
    )
    
    return XGResponse(
        xg_value=prob,
        shot_danger_class=danger,
        derived_metrics=derived,
        feature_shap_attribution=shap_attribs
    )
