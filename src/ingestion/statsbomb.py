import os
import logging
import pandas as pd
from statsbombpy import sb

logger = logging.getLogger("ingestion_statsbomb")

# World Cup Competition and Season IDs
WC_COMPETITION_ID = 43
WC_SEASONS = [3, 106]  # 2018, 2022

def ingest_statsbomb_shots(raw_dir: str) -> bool:
    """
    Ingests event-level shot logs for the 2018 and 2022 Men's World Cups.
    Compiles all shots and freeze-frames into a single CSV.
    Skips if compiled shots.csv already exists.
    """
    sb_dir = os.path.join(raw_dir, "statsbomb")
    dest_file = os.path.join(sb_dir, "shots.csv")
    if os.path.exists(dest_file) and os.path.getsize(dest_file) > 0:
        logger.info(f"StatsBomb compiled file {dest_file} already exists. Skipping API query.")
        return True
        
    os.makedirs(sb_dir, exist_ok=True)
    all_shots = []
    
    try:
        for season_id in WC_SEASONS:
            logger.info(f"StatsBomb Ingestion: Fetching matches for World Cup (Season {season_id})...")
            matches = sb.matches(competition_id=WC_COMPETITION_ID, season_id=season_id)
            match_ids = matches["match_id"].tolist()
            logger.info(f"Found {len(match_ids)} matches for Season {season_id}")
            
            for idx, match_id in enumerate(match_ids, 1):
                try:
                    logger.info(f"Fetching events for match {match_id} ({idx}/{len(match_ids)})...")
                    events = sb.events(match_id=match_id)
                    if "type" in events.columns:
                        match_shots = events[events["type"] == "Shot"].copy()
                        match_shots["match_id"] = match_id
                        match_shots["season_id"] = season_id
                        all_shots.append(match_shots)
                except Exception as e:
                    logger.warning(f"Error fetching events for match {match_id}: {e}")
                    
        if all_shots:
            # Concatenate all shot dataframes. Since columns might vary slightly, use outer join
            logger.info("Compiling all shot events...")
            compiled_df = pd.concat(all_shots, axis=0, ignore_index=True)
            
            # Save to CSV
            dest_file = os.path.join(sb_dir, "shots.csv")
            compiled_df.to_csv(dest_file, index=False)
            logger.info(f"Successfully compiled {len(compiled_df)} shot events to {dest_file}")
            return True
        else:
            logger.error("No shots were found/downloaded from StatsBomb.")
            return False
            
    except Exception as e:
        logger.error(f"Failed to ingest StatsBomb data: {e}")
        return False

if __name__ == "__main__":
    import sys
    raw_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
    success = ingest_statsbomb_shots(raw_directory)
    sys.exit(0 if success else 1)
