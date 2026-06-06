import os
import logging
from src.ingestion.utils import download_file

logger = logging.getLogger("ingestion_fjelstul")

BASE_URL = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv"
FILES = {
    "matches": "matches.csv",
    "penalty_kicks": "penalty_kicks.csv",
    "group_standings": "group_standings.csv",
    "squads": "squads.csv",
    "players": "players.csv"
}

def ingest_fjelstul(raw_dir: str) -> bool:
    """
    Downloads historical World Cup datasets from Joshua Fjelstul's GitHub repository.
    """
    fjelstul_dir = os.path.join(raw_dir, "fjelstul")
    os.makedirs(fjelstul_dir, exist_ok=True)
    all_success = True
    
    for key, filename in FILES.items():
        url = f"{BASE_URL}/{filename}"
        dest = os.path.join(fjelstul_dir, filename)
        success = download_file(url, dest)
        if not success:
            logger.error(f"Fjelstul Ingestion: Failed to download {filename}")
            all_success = False
            
    return all_success

if __name__ == "__main__":
    import sys
    raw_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
    success = ingest_fjelstul(raw_directory)
    sys.exit(0 if success else 1)
