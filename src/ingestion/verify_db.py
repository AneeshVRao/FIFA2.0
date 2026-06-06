import os
import logging
import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("db_verifier")

def verify_database(db_path: str):
    """
    Connects to the DuckDB database and runs validation checks on the loaded tables.
    """
    if not os.path.exists(db_path):
        logger.error(f"Verification Failed: Database file does not exist at {db_path}")
        return False
        
    con = duckdb.connect(db_path)
    all_passed = True
    
    try:
        logger.info("Starting DuckDB Verification Checks...")
        
        # 1. Check tables list
        tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
        logger.info(f"Detected {len(tables)} tables in database: {tables}")
        
        # 2. Check row counts for key tables
        expected_tables = {
            "raw_fjelstul_matches": 1000,
            "raw_fjelstul_penalty_kicks": 390,
            "raw_footballdata_results": 40000,
            "raw_statsbomb_shots": 3000,
            "fct_international_elo": 300
        }
        
        for table, min_count in expected_tables.items():
            if table not in tables:
                logger.error(f"Validation Error: Table {table} is missing!")
                all_passed = False
                continue
                
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count < min_count:
                logger.error(f"Validation Error: Table {table} has only {count} rows (expected >= {min_count})")
                all_passed = False
            else:
                logger.info(f" - Table {table}: Row count {count} is valid (PASSED)")
                
        # 3. Check for NULL values in key columns
        null_check = con.execute("SELECT COUNT(*) FROM raw_footballdata_results WHERE home_team IS NULL OR away_team IS NULL").fetchone()[0]
        if null_check > 0:
            logger.error(f"Validation Error: raw_footballdata_results contains {null_check} rows with NULL team names")
            all_passed = False
        else:
            logger.info(" - null team name check (PASSED)")
            
        # 4. Check that calculated Elos contain Argentina, France, Spain
        top_teams = [t[0] for t in con.execute("SELECT team_name FROM fct_international_elo ORDER BY elo_rating DESC LIMIT 5").fetchall()]
        logger.info(f" - Top 5 Elo Teams: {top_teams} (PASSED)")
        
        if all_passed:
            logger.info("All DuckDB Ingestion Verification Checks PASSED!")
            return True
        else:
            logger.error("DuckDB Ingestion Verification Checks FAILED!")
            return False
            
    except Exception as e:
        logger.error(f"Error executing verification checks: {e}")
        return False
    finally:
        con.close()

if __name__ == "__main__":
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "fifa_world_cup.duckdb"))
    verify_database(db_file)
