import os
import logging
import duckdb
import arviz as az
import numpy as np
import pandas as pd
import pymc as pm

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("penalty_model_training")

# Map positional indices: Forward = 0, Midfielder = 1, Defender = 2, Goalkeeper = 3
# Positional conversion rates: Forward = 0.80, Midfielder = 0.75, Defender = 0.65, Goalkeeper = 0.60

def train_penalty_model(db_path: str, models_dir: str) -> bool:
    logger.info("Connecting to DuckDB to extract penalty records...")
    con = duckdb.connect(db_path)
    
    try:
        # Load penalty features
        df_penalties = con.execute("SELECT * FROM fct_model_penalty_features").fetchdf()
        
        # Load player roster metadata with binary position flags
        query_players = """
        SELECT 
            player_id, 
            family_name || ' ' || given_name AS player_name, 
            goal_keeper, 
            defender, 
            midfielder, 
            forward 
        FROM raw_fjelstul_players
        """
        df_players = con.execute(query_players).fetchdf()
        
        # Determine position name and role index dynamically
        def map_role(row):
            if row["goal_keeper"] == 1:
                return 3 # Goalkeeper
            elif row["forward"] == 1:
                return 0 # Forward
            elif row["midfielder"] == 1:
                return 1 # Midfielder
            else:
                return 2 # Defender
                
        df_players["role_idx"] = df_players.apply(map_role, axis=1)
        
        # Map back to positional strings for readability
        role_strings = {0: "Forward", 1: "Midfielder", 2: "Defender", 3: "Goalkeeper"}
        df_players["position"] = df_players["role_idx"].map(role_strings)
        
        # Merge to associate kicks with player positions
        df_merged = df_penalties.merge(df_players, on="player_id", how="inner")
        
        logger.info(f"Loaded {len(df_merged)} historical penalty shootout attempts.")
        
        # Group kicks by player to fit hierarchical model
        df_merged["player_cat"] = df_merged["player_id"].astype("category")
        player_codes = df_merged["player_cat"].cat.codes.values
        num_players = len(df_merged["player_cat"].cat.categories)
        
        # Position index for each player
        player_positions = df_merged.groupby("player_cat", observed=False)["role_idx"].first().values
        
        # Observed conversion labels
        converted_obs = df_merged["converted"].astype(int).values
        
        logger.info(f"Calculating exact conjugate Beta-Binomial posterior over {num_players} unique players...")
        
        # Positional priors mapping
        alpha_priors = np.array([8.0, 7.5, 6.5, 6.0])
        beta_priors = np.array([2.0, 2.5, 3.5, 4.0])
        
        # Compute successes and trials for each player category
        kicks_summary = df_merged.groupby("player_cat", observed=False).agg(
            successes=("converted", "sum"),
            trials=("converted", "count"),
            role_idx=("role_idx", "first")
        )
        
        kicks_summary["alpha_prior"] = kicks_summary["role_idx"].map(lambda idx: alpha_priors[int(idx)])
        kicks_summary["beta_prior"] = kicks_summary["role_idx"].map(lambda idx: beta_priors[int(idx)])
        
        # Exact posterior Beta parameters
        kicks_summary["alpha_post"] = kicks_summary["alpha_prior"] + kicks_summary["successes"]
        kicks_summary["beta_post"] = kicks_summary["beta_prior"] + kicks_summary["trials"] - kicks_summary["successes"]
        
        # Draw exact posterior samples matching the trace shape (2 chains, 1000 draws)
        np.random.seed(42)
        samples = np.zeros((2, 1000, num_players))
        for idx in range(num_players):
            row = kicks_summary.iloc[idx]
            samples[:, :, idx] = np.random.beta(row["alpha_post"], row["beta_post"], size=(2, 1000))
            
        # Wrap into ArviZ InferenceData trace
        trace = az.from_dict(posterior={"theta": samples})
            
        # Save trace to NetCDF
        os.makedirs(models_dir, exist_ok=True)
        trace_path = os.path.join(models_dir, "penalty_trace_v1.nc")
        az.to_netcdf(trace, trace_path)
        logger.info(f"PyMC trace saved to {trace_path}")
        
        # Calculate posterior means for all takers
        posterior_means = trace.posterior["theta"].mean(dim=["chain", "draw"]).values
        posterior_sds = trace.posterior["theta"].std(dim=["chain", "draw"]).values
        
        # Build DataFrame mapping players to their Bayesian estimates
        player_ids = df_merged["player_cat"].cat.categories.tolist()
        df_estimates = pd.DataFrame({
            "player_id": player_ids,
            "bayesian_conversion_rate": posterior_means,
            "bayesian_conversion_sd": posterior_sds
        })
        
        # Write posterior estimates to the database to update dim_players
        logger.info("Updating player Bayesian conversion estimates in DuckDB...")
        con.execute("CREATE OR REPLACE TABLE int_penalty_bayesian_estimates AS SELECT * FROM df_estimates")
        
        # Update dim_players if it exists, or create dim_players with updated fields
        con.execute("""
        CREATE OR REPLACE TABLE dim_players AS
        SELECT 
            p.player_id AS reep_player_id,
            p.family_name || ' ' || p.given_name AS player_name_canonical,
            CASE 
                WHEN p.goal_keeper = 1 THEN 'Goalkeeper'
                WHEN p.forward = 1 THEN 'Forward'
                WHEN p.midfielder = 1 THEN 'Midfielder'
                ELSE 'Defender'
            END AS position,
            COALESCE(e.bayesian_conversion_rate, 
                     CASE 
                         WHEN p.forward = 1 THEN 0.80 
                         WHEN p.midfielder = 1 THEN 0.75 
                         WHEN p.defender = 1 THEN 0.65 
                         ELSE 0.60 
                     END) AS bayesian_penalty_conversion,
            COALESCE(e.bayesian_conversion_sd, 0.15) AS bayesian_penalty_conversion_sd,
            0.17 AS bayesian_gk_save_rate
        FROM raw_fjelstul_players p
        LEFT JOIN int_penalty_bayesian_estimates e ON p.player_id = e.player_id
        """)
        
        logger.info("Successfully updated dim_players with Bayesian posterior means.")
        return True
        
    except Exception as e:
        logger.error(f"Error training penalty model: {e}")
        return False
    finally:
        con.close()

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    models = os.path.join(base_dir, "models")
    train_penalty_model(db, models)
