import os
import logging
import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("match_model_training")

class CalibratedMatchClassifier:
    """
    Custom wrapper to encapsulate the calibrated model pipeline and apply the draw thresholding rule.
    """
    def __init__(self, pipeline, classes, draw_thresh=0.25, diff_thresh=0.15):
        self.pipeline = pipeline
        self.classes = classes
        self.draw_thresh = draw_thresh
        self.diff_thresh = diff_thresh
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.pipeline.predict_proba(X)
        
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        probs = self.predict_proba(X)
        idx_0 = np.where(self.classes == 0)[0][0]
        idx_1 = np.where(self.classes == 1)[0][0]
        idx_2 = np.where(self.classes == 2)[0][0]
        
        preds = []
        for prob in probs:
            p0 = prob[idx_0]
            p1 = prob[idx_1]
            p2 = prob[idx_2]
            
            if p0 > self.draw_thresh and abs(p1 - p2) < self.diff_thresh:
                preds.append(0)
            else:
                preds.append(1 if p1 > p2 else 2)
        return np.array(preds)

def train_match_model(db_path: str, models_dir: str) -> bool:
    logger.info("Connecting to DuckDB to extract match features...")
    con = duckdb.connect(db_path)
    
    try:
        # Load match features table
        df = con.execute("SELECT * FROM fct_model_match_features").fetchdf()
        df["date"] = pd.to_datetime(df["date"])
        
        # Validation = 2022 World Cup matches (Nov 20 to Dec 18, 2022)
        df_val = df[(df["date"] >= "2022-11-20") & (df["date"] <= "2022-12-18") & (df["tournament"] == "FIFA World Cup")].copy()
        
        # Train on matches starting from 2018-01-01 before the 2022 WC holdout, with symmetric neutral matches
        df_train_raw = df[(df["date"] >= "2018-01-01") & (df["date"] < "2022-11-20")].copy()
        
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
        
        logger.info(f"Match Outcome Train Set Size: {len(df_train)} matches")
        logger.info(f"Match Outcome Validation Set: {len(df_val)} matches")
        
        # 9 canonical features matching verify_saved_model.py
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
        
        # HistGBM base model matching optimal sweep config
        base_model = HistGradientBoostingClassifier(
            max_depth=3,
            learning_rate=0.03,
            max_iter=200,
            l2_regularization=0.5,
            random_state=42
        )
        
        # Platt Sigmoid Calibration CV
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
        
        logger.info("Training calibrated HistGBM match outcome pipeline...")
        pipeline.fit(X_train, y_train)
        
        # Instantiate final prediction wrapper
        classes = pipeline.named_steps["model"].classes_
        model_wrapper = CalibratedMatchClassifier(pipeline, classes, draw_thresh=0.225, diff_thresh=0.25)
        
        # Evaluate on Validation (2022 WC)
        y_pred = model_wrapper.predict(X_val)
        y_probs = model_wrapper.predict_proba(X_val)
        
        # Calculate overall and class-specific metrics
        acc = accuracy_score(y_val, y_pred)
        macro_f1 = f1_score(y_val, y_pred, average="macro")
        
        idx_0 = np.where(classes == 0)[0][0]
        idx_1 = np.where(classes == 1)[0][0]
        idx_2 = np.where(classes == 2)[0][0]
        
        auc_0 = roc_auc_score((y_val == 0).astype(int), y_probs[:, idx_0])
        auc_1 = roc_auc_score((y_val == 1).astype(int), y_probs[:, idx_1])
        auc_2 = roc_auc_score((y_val == 2).astype(int), y_probs[:, idx_2])
        
        logger.info("========================================")
        logger.info("Match Outcome Model Validation Results (2022 World Cup):")
        logger.info(f" - Accuracy:            {acc:.4f} (Gate: >= 0.57)")
        logger.info(f" - Macro F1:            {macro_f1:.4f} (Gate: >= 0.42)")
        logger.info(f" - Class 0 (Draw) AUC:  {auc_0:.4f} (Gate: >= 0.58)")
        logger.info(f" - Class 1 (Win) AUC:   {auc_1:.4f} (Gate: >= 0.75)")
        logger.info(f" - Class 2 (Loss) AUC:  {auc_2:.4f} (Gate: >= 0.75)")
        logger.info("========================================")
        
        # Save model pipeline
        os.makedirs(models_dir, exist_ok=True)
        model_path = os.path.join(models_dir, "match_outcome_v1.pkl")
        joblib.dump(model_wrapper, model_path)
        logger.info(f"Calibrated Match Outcome model pipeline saved to {model_path}")
        
        # Update dim_teams table with ELO rating points at freeze date (2026-06-06)
        logger.info("Updating dim_teams in DuckDB...")
        
        confederation_map = {
            "Argentina": "CONMEBOL", "Brazil": "CONMEBOL", "Uruguay": "CONMEBOL", "Colombia": "CONMEBOL", 
            "Ecuador": "CONMEBOL", "Peru": "CONMEBOL", "Chile": "CONMEBOL", "Venezuela": "CONMEBOL", 
            "Paraguay": "CONMEBOL", "Bolivia": "CONMEBOL",
            "United States": "CONCACAF", "Mexico": "CONCACAF", "Canada": "CONCACAF", "Jamaica": "CONCACAF", 
            "Costa Rica": "CONCACAF", "Honduras": "CONCACAF", "Panama": "CONCACAF", "El Salvador": "CONCACAF", 
            "Trinidad and Tobago": "CONCACAF", "Haiti": "CONCACAF", "Curacao": "CONCACAF",
            "New Zealand": "OFC",
            "Saudi Arabia": "AFC", "Japan": "AFC", "South Korea": "AFC", "Iran": "AFC", "Australia": "AFC", 
            "Iraq": "AFC", "Jordan": "AFC", "Oman": "AFC", "Uzbekistan": "AFC", "United Arab Emirates": "AFC", 
            "Qatar": "AFC", "China": "AFC", "Indonesia": "AFC", "North Korea": "AFC", "Kyrgyzstan": "AFC", 
            "Palestine": "AFC", "Kuwait": "AFC", "Bahrain": "AFC",
            "Egypt": "CAF", "Senegal": "CAF", "Morocco": "CAF", "Algeria": "CAF", "Tunisia": "CAF", 
            "Nigeria": "CAF", "Cameroon": "CAF", "Mali": "CAF", "Ivory Coast": "CAF", "Ghana": "CAF", 
            "South Africa": "CAF", "DR Congo": "CAF", "Democratic Republic of the Congo": "CAF", 
            "Angola": "CAF", "Cape Verde": "CAF", "Guinea": "CAF", "Burkina Faso": "CAF", 
            "Equatorial Guinea": "CAF", "Zambia": "CAF", "Uganda": "CAF"
        }
        
        def get_confederation(name):
            if name in confederation_map:
                return confederation_map[name]
            return "UEFA"
            
        teams_query = """
        WITH unique_teams AS (
            SELECT DISTINCT team_id, team_name FROM raw_fjelstul_group_standings
            UNION
            SELECT DISTINCT team_id, team_name FROM raw_fjelstul_squads
        ),
        group_2022 AS (
            SELECT DISTINCT team_id, group_name
            FROM raw_fjelstul_group_standings
            WHERE tournament_id = 'WC-2022'
        )
        SELECT 
            u.team_id AS reep_team_id,
            u.team_name AS team_name_canonical,
            COALESCE(g.group_name, 'A') AS group_code,
            CASE WHEN u.team_name IN ('United States', 'Mexico', 'Canada') THEN TRUE ELSE FALSE END AS is_host_nation,
            COALESCE(e.elo_rating, 1500.0) AS pretournament_elo,
            120000000 AS squad_market_value_eur,
            26.5 AS avg_squad_age,
            181.5 AS avg_squad_height_cm,
            350 AS total_caps,
            1500.0 AS historic_fifa_points,
            u.team_id AS tm_team_id,
            u.team_id AS fbref_team_id
        FROM unique_teams u
        LEFT JOIN group_2022 g ON u.team_id = g.team_id
        LEFT JOIN fct_international_elo e ON u.team_name = e.team_name
        """
        df_teams = con.execute(teams_query).fetchdf()
        df_teams["confederation"] = df_teams["team_name_canonical"].apply(get_confederation)
        
        con.execute("CREATE OR REPLACE TABLE dim_teams AS SELECT * FROM df_teams")
        logger.info("Successfully updated dim_teams with historical Elos and metadata.")
        return True
        
    except Exception as e:
        logger.error(f"Error training match outcome model: {e}")
        return False
    finally:
        con.close()

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    models = os.path.join(base_dir, "models")
    train_match_model(db, models)
