import os
import duckdb
from contextlib import contextmanager

# Resolve absolute path to the database file dynamically
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "fifa_world_cup.duckdb")

@contextmanager
def get_db_connection():
    """
    Context manager to open a read-only connection to the DuckDB database.
    Using read_only=True ensures multi-threaded compatibility and prevents locks.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found at expected path: {DB_PATH}")
    
    conn = duckdb.connect(database=DB_PATH, read_only=True)
    try:
        yield conn
    finally:
        conn.close()
