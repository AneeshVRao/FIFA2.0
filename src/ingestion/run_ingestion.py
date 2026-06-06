import os
import logging
import duckdb
from src.ingestion.fjelstul import ingest_fjelstul
from src.ingestion.transfermarkt import ingest_transfermarkt
from src.ingestion.statsbomb import ingest_statsbomb_shots
from src.ingestion.footballdata import ingest_footballdata
from src.transformation.elo import compute_historical_elos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("ingestion_orchestrator")

def scaffold_and_load_duckdb(raw_dir: str, db_path: str) -> bool:
    """
    Connects to DuckDB, creates the target schema tables, and loads raw CSVs directly.
    """
    logger.info(f"Connecting to DuckDB database at {db_path}...")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = duckdb.connect(db_path)
    
    try:
        # Load Fjelstul tables
        fjel_dir = os.path.join(raw_dir, "fjelstul")
        logger.info("Loading Fjelstul tables into DuckDB...")
        con.execute(f"CREATE OR REPLACE TABLE raw_fjelstul_matches AS SELECT * FROM read_csv_auto('{os.path.join(fjel_dir, 'matches.csv')}')")
        con.execute(f"CREATE OR REPLACE TABLE raw_fjelstul_penalty_kicks AS SELECT * FROM read_csv_auto('{os.path.join(fjel_dir, 'penalty_kicks.csv')}')")
        con.execute(f"CREATE OR REPLACE TABLE raw_fjelstul_group_standings AS SELECT * FROM read_csv_auto('{os.path.join(fjel_dir, 'group_standings.csv')}')")
        con.execute(f"CREATE OR REPLACE TABLE raw_fjelstul_squads AS SELECT * FROM read_csv_auto('{os.path.join(fjel_dir, 'squads.csv')}')")
        con.execute(f"CREATE OR REPLACE TABLE raw_fjelstul_players AS SELECT * FROM read_csv_auto('{os.path.join(fjel_dir, 'players.csv')}')")
        
        # Load Transfermarkt tables (support both .csv and .csv.gz)
        tm_dir = os.path.join(raw_dir, "transfermarkt")
        logger.info("Loading Transfermarkt tables into DuckDB...")
        for table_name in ["players", "player_valuations", "clubs"]:
            file_path = os.path.join(tm_dir, table_name)
            if os.path.exists(file_path + ".csv.gz"):
                con.execute(f"CREATE OR REPLACE TABLE raw_transfermarkt_{table_name} AS SELECT * FROM read_csv_auto('{file_path}.csv.gz')")
            elif os.path.exists(file_path + ".csv"):
                con.execute(f"CREATE OR REPLACE TABLE raw_transfermarkt_{table_name} AS SELECT * FROM read_csv_auto('{file_path}.csv')")
            else:
                logger.error(f"Transfermarkt file {table_name} not found in {tm_dir}")
                return False
                
        # Load StatsBomb tables
        sb_dir = os.path.join(raw_dir, "statsbomb")
        logger.info("Loading StatsBomb tables into DuckDB...")
        con.execute(f"CREATE OR REPLACE TABLE raw_statsbomb_shots AS SELECT * FROM read_csv_auto('{os.path.join(sb_dir, 'shots.csv')}')")
        
        # Load FootballData results & odds
        fd_dir = os.path.join(raw_dir, "footballdata")
        logger.info("Loading FootballData results & odds into DuckDB...")
        con.execute(f"CREATE OR REPLACE TABLE raw_footballdata_results AS SELECT * FROM read_csv_auto('{os.path.join(fd_dir, 'results.csv')}', nullstr='NA')")
        con.execute(f"CREATE OR REPLACE TABLE raw_footballdata_shootouts AS SELECT * FROM read_csv_auto('{os.path.join(fd_dir, 'shootouts.csv')}')")
        con.execute(f"CREATE OR REPLACE TABLE raw_footballdata_odds AS SELECT * FROM read_csv_auto('{os.path.join(fd_dir, 'odds_2022.csv')}')")
        
        # Load Computed Elo ratings
        logger.info("Loading Computed Elo ratings into DuckDB...")
        con.execute(f"CREATE OR REPLACE TABLE fct_international_elo AS SELECT * FROM read_csv_auto('{os.path.join(fd_dir, 'final_ratings.csv')}')")
        con.execute(f"CREATE OR REPLACE TABLE fct_international_elo_trace AS SELECT * FROM read_csv_auto('{os.path.join(fd_dir, 'elo_trace.csv')}')")
        
        logger.info("DuckDB Tables successfully loaded:")
        tables = con.execute("SHOW TABLES").fetchall()
        for t in tables:
            count = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
            logger.info(f" - {t[0]}: {count} rows")
            
        return True
        
    except Exception as e:
        logger.error(f"Error loading data into DuckDB: {e}")
        return False
    finally:
        con.close()

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    raw_dir = os.path.join(base_dir, "data", "raw")
    db_path = os.path.join(base_dir, "data", "fifa_world_cup.duckdb")
    
    logger.info("========================================")
    logger.info("Phase 1: Starting Data Ingestion Pipeline")
    logger.info("========================================")
    
    # 1. Ingest Fjelstul
    logger.info("Ingesting Fjelstul World Cup Database...")
    if not ingest_fjelstul(raw_dir):
        logger.error("Fjelstul Ingestion Failed!")
        return
        
    # 2. Ingest Transfermarkt
    logger.info("Ingesting Transfermarkt Valuations...")
    if not ingest_transfermarkt(raw_dir):
        logger.error("Transfermarkt Ingestion Failed!")
        return
        
    # 3. Ingest StatsBomb
    logger.info("Ingesting StatsBomb Shot logs...")
    if not ingest_statsbomb_shots(raw_dir):
        logger.error("StatsBomb Ingestion Failed!")
        return
        
    # 4. Ingest FootballData Results and Odds
    logger.info("Ingesting FootballData results and odds...")
    if not ingest_footballdata(raw_dir):
        logger.error("FootballData Ingestion Failed!")
        return
        
    # 5. Calculate chronological Elo ratings
    results_file = os.path.join(raw_dir, "footballdata", "results.csv")
    elo_trace_file = os.path.join(raw_dir, "footballdata", "elo_trace.csv")
    logger.info("Calculating Chronological Elo ratings...")
    compute_historical_elos(results_file, elo_trace_file)
    
    # 6. Scaffold and Populate DuckDB
    logger.info("Scaffolding DuckDB and loading datasets...")
    if scaffold_and_load_duckdb(raw_dir, db_path):
        logger.info("========================================")
        logger.info("Phase 1: Ingestion Successfully Completed!")
        logger.info("========================================")
    else:
        logger.error("DuckDB loading failed!")

if __name__ == "__main__":
    main()
