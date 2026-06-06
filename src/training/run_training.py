import os
import logging
from src.transformation.features import main as run_feature_engineering
from src.training.xg_model import train_xg_model
from src.training.penalty_model import train_penalty_model
from src.training.match_model import train_match_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("training_orchestrator")

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db_path = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    models_dir = os.path.join(base_dir, "models")
    
    logger.info("========================================")
    logger.info("Phase 2: Starting Model Training Pipeline")
    logger.info("========================================")
    
    # 1. Run Feature Engineering
    logger.info("Step 1/4: Running Feature Engineering Pipeline...")
    try:
        run_feature_engineering()
    except Exception as e:
        logger.error(f"Feature Engineering Failed: {e}")
        return
        
    # 2. Train xG model
    logger.info("Step 2/4: Training Expected Goals (xG) Model...")
    if not train_xg_model(db_path, models_dir):
        logger.error("xG Model Training Failed!")
        return
        
    # 3. Train Penalty Shootout model
    logger.info("Step 3/4: Training Bayesian Penalty Shootout model...")
    if not train_penalty_model(db_path, models_dir):
        logger.error("Penalty Shootout Model Training Failed!")
        return
        
    # 4. Train Match Outcome model
    logger.info("Step 4/4: Training Match Outcome model...")
    if not train_match_model(db_path, models_dir):
        logger.error("Match Outcome Model Training Failed!")
        return
        
    logger.info("========================================")
    logger.info("Phase 2: Model Training Successfully Completed!")
    logger.info("========================================")

if __name__ == "__main__":
    main()
