import os
import logging
import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import predictions, xg, penalty, players, teams
from src.api.schemas import HealthResponse, ModelLoadingStatus
from src.api.database import get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("api_main")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATCH_MODEL_PATH = os.path.join(BASE_DIR, "models", "match_outcome_v1.pkl")
XG_MODEL_PATH = os.path.join(BASE_DIR, "models", "xg_model_v1.pkl")
PENALTY_TRACE_PATH = os.path.join(BASE_DIR, "models", "penalty_trace_v1.nc")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load calibrated Match Outcome classifier (Platt scaled HistGBM)
    logger.info(f"Loading Match Outcome model from {MATCH_MODEL_PATH}...")
    if os.path.exists(MATCH_MODEL_PATH):
        try:
            app.state.match_model = joblib.load(MATCH_MODEL_PATH)
            logger.info("Match Outcome model successfully loaded.")
        except Exception as e:
            logger.error(f"Failed to load Match Outcome model: {e}")
            app.state.match_model = None
    else:
        logger.warning("Match Outcome model binary not found.")
        app.state.match_model = None

    # Load calibrated Expected Goals classifier (Isotonic scaled XGBoost)
    logger.info(f"Loading Expected Goals model from {XG_MODEL_PATH}...")
    if os.path.exists(XG_MODEL_PATH):
        try:
            app.state.xg_model = joblib.load(XG_MODEL_PATH)
            logger.info("Expected Goals model successfully loaded.")
        except Exception as e:
            logger.error(f"Failed to load Expected Goals model: {e}")
            app.state.xg_model = None
    else:
        logger.warning("Expected Goals model binary not found.")
        app.state.xg_model = None

    yield
    # Clean up model state
    app.state.match_model = None
    app.state.xg_model = None

app = FastAPI(
    title="GoalIQ FIFA World Cup 2026 Prediction Platform API",
    description="FastAPI async REST endpoints exposing precomputed simulations and on-the-fly Dixon-Coles expected goals and penalty shootout forecasts.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for the dashboard integrations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(predictions.router)
app.include_router(xg.router)
app.include_router(penalty.router)
app.include_router(players.router)
app.include_router(teams.router)

@app.get("/", tags=["root"])
async def root():
    return {
        "title": "GoalIQ Prediction API",
        "version": "1.0.0",
        "documentation": "/docs",
        "prediction_freeze_date": "2026-06-06",
        "status": "online"
    }

@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    # Verify DuckDB Connection
    db_status = "disconnected"
    try:
        with get_db_connection() as conn:
            # Simple check query
            res = conn.execute("SELECT 1").fetchone()
            if res and res[0] == 1:
                db_status = "connected"
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        db_status = f"error: {str(e)}"

    # Check loaded models in app.state
    match_status = "loaded" if getattr(app.state, "match_model", None) is not None else "missing"
    xg_status = "loaded" if getattr(app.state, "xg_model", None) is not None else "missing"
    
    # Check if NetCDF file exists on disk
    penalty_status = "available" if os.path.exists(PENALTY_TRACE_PATH) else "missing"

    models_ready = ModelLoadingStatus(
        match_outcome_model=match_status,
        xg_model=xg_status,
        penalty_shootout_model=penalty_status
    )

    return HealthResponse(
        status="healthy" if db_status == "connected" and match_status == "loaded" and xg_status == "loaded" else "degraded",
        database_connection=db_status,
        models_ready=models_ready,
        simulation_status="complete"
    )
