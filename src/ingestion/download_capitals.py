import os
import logging
import requests
import duckdb
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("download_capitals")

CAPITALS_URL = "https://raw.githubusercontent.com/google/dspl/master/samples/google/canonical/countries.csv"

# 16 official host venues for the 2026 World Cup (altitudes, capacities, and coordinates)
VENUES = [
    {"venue_id": "v_atlanta", "stadium_name": "Mercedes-Benz Stadium", "city": "Atlanta", "host_nation": "USA", "latitude": 33.7556, "longitude": -84.4008, "altitude_m": 308, "capacity": 71000},
    {"venue_id": "v_boston", "stadium_name": "Gillette Stadium", "city": "Boston", "host_nation": "USA", "latitude": 42.0909, "longitude": -71.2643, "altitude_m": 81, "capacity": 65878},
    {"venue_id": "v_dallas", "stadium_name": "AT&T Stadium", "city": "Dallas", "host_nation": "USA", "latitude": 32.7473, "longitude": -97.0945, "altitude_m": 185, "capacity": 80000},
    {"venue_id": "v_guadalajara", "stadium_name": "Estadio Akron", "city": "Guadalajara", "host_nation": "Mexico", "latitude": 20.6819, "longitude": -103.4628, "altitude_m": 1566, "capacity": 48071},
    {"venue_id": "v_houston", "stadium_name": "NRG Stadium", "city": "Houston", "host_nation": "USA", "latitude": 29.6847, "longitude": -95.4107, "altitude_m": 12, "capacity": 72220},
    {"venue_id": "v_kansascity", "stadium_name": "Arrowhead Stadium", "city": "Kansas City", "host_nation": "USA", "latitude": 39.0489, "longitude": -94.4839, "altitude_m": 269, "capacity": 76416},
    {"venue_id": "v_losangeles", "stadium_name": "SoFi Stadium", "city": "Los Angeles", "host_nation": "USA", "latitude": 33.9535, "longitude": -118.3390, "altitude_m": 43, "capacity": 70240},
    {"venue_id": "v_mexicocity", "stadium_name": "Estadio Azteca", "city": "Mexico City", "host_nation": "Mexico", "latitude": 19.3029, "longitude": -99.1506, "altitude_m": 2200, "capacity": 87523},
    {"venue_id": "v_miami", "stadium_name": "Hard Rock Stadium", "city": "Miami", "host_nation": "USA", "latitude": 25.9580, "longitude": -80.2389, "altitude_m": 3, "capacity": 64767},
    {"venue_id": "v_monterrey", "stadium_name": "Estadio BBVA", "city": "Monterrey", "host_nation": "Mexico", "latitude": 25.6698, "longitude": -100.2442, "altitude_m": 538, "capacity": 53500},
    {"venue_id": "v_newyork", "stadium_name": "MetLife Stadium", "city": "New York/New Jersey", "host_nation": "USA", "latitude": 40.8135, "longitude": -74.0743, "altitude_m": 7, "capacity": 82500},
    {"venue_id": "v_philadelphia", "stadium_name": "Lincoln Financial Field", "city": "Philadelphia", "host_nation": "USA", "latitude": 39.9008, "longitude": -75.1675, "altitude_m": 3, "capacity": 69796},
    {"venue_id": "v_sanfrancisco", "stadium_name": "Levi's Stadium", "city": "San Francisco", "host_nation": "USA", "latitude": 37.4032, "longitude": -121.9698, "altitude_m": 15, "capacity": 68500},
    {"venue_id": "v_seattle", "stadium_name": "Lumen Field", "city": "Seattle", "host_nation": "USA", "latitude": 47.5952, "longitude": -122.3316, "altitude_m": 3, "capacity": 69000},
    {"venue_id": "v_toronto", "stadium_name": "BMO Field", "city": "Toronto", "host_nation": "Canada", "latitude": 43.6328, "longitude": -79.4186, "altitude_m": 76, "capacity": 45000},
    {"venue_id": "v_vancouver", "stadium_name": "BC Place", "city": "Vancouver", "host_nation": "Canada", "latitude": 49.2767, "longitude": -123.1120, "altitude_m": 5, "capacity": 54500}
]

def run_ingestion(db_path: str, raw_dir: str):
    logger.info("Starting country coordinates and venues setup...")
    
    # 1. Download capitals CSV
    dest_path = os.path.join(raw_dir, "footballdata", "country-capitals.csv")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    try:
        logger.info(f"Downloading country coordinates from {CAPITALS_URL}...")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(CAPITALS_URL, headers=headers, timeout=30)
        r.raise_for_status()
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        logger.info(f"Successfully saved country coordinates CSV to {dest_path}")
    except Exception as e:
        logger.error(f"Failed to download country coordinates CSV: {e}")
        return False
        
    # 2. Connect to DuckDB
    logger.info(f"Connecting to DuckDB at {db_path}...")
    con = duckdb.connect(db_path)
    
    try:
        # Load raw_country_capitals
        logger.info("Loading raw_country_capitals table...")
        con.execute(f"CREATE OR REPLACE TABLE raw_country_capitals AS SELECT * FROM read_csv_auto('{dest_path}')")
        
        # Verify row count
        count = con.execute("SELECT COUNT(*) FROM raw_country_capitals").fetchone()[0]
        logger.info(f"Loaded {count} country coordinate records.")
        
        # Load dim_venues
        logger.info("Creating and populating dim_venues table...")
        df_venues = pd.DataFrame(VENUES)
        con.execute("CREATE OR REPLACE TABLE dim_venues AS SELECT * FROM df_venues")
        
        # Verify dim_venues row count
        v_count = con.execute("SELECT COUNT(*) FROM dim_venues").fetchone()[0]
        logger.info(f"Loaded {v_count} venues into dim_venues (Expected: 16).")
        
        if v_count == 16:
            logger.info("Venues verification PASSED!")
            return True
        else:
            logger.error(f"Venues count mismatch: {v_count} != 16")
            return False
            
    except Exception as e:
        logger.error(f"Error during DuckDB database updates: {e}")
        return False
    finally:
        con.close()

if __name__ == "__main__":
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    db = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    raw = os.path.join(base_dir, "data", "raw")
    run_ingestion(db, raw)
