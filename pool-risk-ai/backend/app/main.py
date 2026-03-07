"""
FastAPI application entry point for Pool Risk AI.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_detect, routes_risk
from app.config import OUTPUT_PATH

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure output directory exists at startup
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Pool Risk AI",
    description=(
        "AI-powered swimming pool detection and insurance risk intelligence "
        "using YOLOv11 segmentation, geospatial analysis, and Grad-CAM explainability."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow any origin during development (restrict in production)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(routes_detect.router, prefix="/api/v1", tags=["Detection"])
app.include_router(routes_risk.router, prefix="/api/v1", tags=["Risk Assessment"])


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def root() -> dict:
    return {"service": "Pool Risk AI", "version": "1.0.0", "status": "running"}


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
