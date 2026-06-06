import os
import logging
from src.ingestion.utils import download_file

logger = logging.getLogger("ingestion_footballdata")

# URLs for international results and historical tournament odds
RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
SHOOTOUTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/shootouts.csv"
ODDS_2022_URL = "https://raw.githubusercontent.com/stefan-stein/world-cup-2022/main/First%20round%20odds.csv"

def ingest_footballdata(raw_dir: str) -> bool:
    """
    Downloads international results, shootouts, and 2022 tournament odds.
    """
    fd_dir = os.path.join(raw_dir, "footballdata")
    os.makedirs(fd_dir, exist_ok=True)
    
    success_res = download_file(RESULTS_URL, os.path.join(fd_dir, "results.csv"))
    success_sht = download_file(SHOOTOUTS_URL, os.path.join(fd_dir, "shootouts.csv"))
    success_ods = download_file(ODDS_2022_URL, os.path.join(fd_dir, "odds_2022.csv"))
    
    return success_res and success_sht and success_ods

if __name__ == "__main__":
    import sys
    raw_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
    success = ingest_footballdata(raw_directory)
    sys.exit(0 if success else 1)
