import os
import time
import logging
import requests

# Set up logging following python-pro standards
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ingestion_utils")

def download_file(url: str, dest_path: str, max_retries: int = 3, delay: int = 2) -> bool:
    """
    Downloads a file from a URL to a local destination path with retries and chunking.
    Mimics browser headers to avoid basic request blocking.
    Skips download if file already exists locally and is non-empty.
    """
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        logger.info(f"File {dest_path} already exists and is non-empty. Skipping download.")
        return True
        
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Downloading {url} to {dest_path} (Attempt {attempt}/{max_retries})...")
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Successfully downloaded to {dest_path}")
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed attempt {attempt} for {url}: {e}")
            if attempt < max_retries:
                time.sleep(delay * attempt)
            else:
                logger.error(f"Failed to download {url} after {max_retries} attempts.")
                
    return False
