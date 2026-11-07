"""FastAPI application entry point for the Chess Review Engine.

Configures CORS, registers global exception handlers, and wires
all API routers (games, analysis, streams).
"""

from fastapi import FastAPI

from app.middleware import setup_cors, setup_exception_handlers
from app.database import init_db

from app.routers.analysis import router as analysis_router
from app.routers.games import router as games_router
from app.routers.streams import router as streams_router

# Initialize database schema on startup
init_db()

app = FastAPI(
    title="Chess Review Engine",
    description="Analyze chess games with Stockfish",
    version="0.1.0",
)

# Configure CORS (allows all origins for Docker Compose dev setup)
setup_cors(app)

# Register global exception handlers for domain errors
setup_exception_handlers(app)

# Wire API routers
app.include_router(games_router)
app.include_router(analysis_router)
app.include_router(streams_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
