import os
import logging
from src.ingestion.utils import download_file

logger = logging.getLogger("ingestion_transfermarkt")

# R2 bucket URLs for Transfermarkt prepared datasets
BASE_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
FILES = ["players.csv.gz", "player_valuations.csv.gz", "clubs.csv.gz"]

def ingest_transfermarkt(raw_dir: str) -> bool:
    """
    Downloads Transfermarkt prepared datasets from the project's public R2 bucket.
    """
    tm_dir = os.path.join(raw_dir, "transfermarkt")
    os.makedirs(tm_dir, exist_ok=True)
    all_success = True
    
    for filename in FILES:
        url = f"{BASE_URL}/{filename}"
        dest = os.path.join(tm_dir, filename)
        
        success = download_file(url, dest)
        if not success:
            logger.error(f"Transfermarkt Ingestion: Failed to download {filename} from {BASE_URL}")
            all_success = False
            
    return all_success

if __name__ == "__main__":
    import sys
    raw_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw"))
    success = ingest_transfermarkt(raw_directory)
    sys.exit(0 if success else 1)
