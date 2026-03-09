import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.models.yolo_model import load_model
from app.routes.detect_routes import router as detect_router
from app.routes.analysis_routes import router as analysis_router
from app.routes.scan_routes import router as scan_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AquaVision API",
    description="Swimming pool detection from satellite imagery using YOLOv11",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(detect_router)
app.include_router(analysis_router)
app.include_router(scan_router)


@app.on_event("startup")
async def startup():
    """Load model into memory at startup so first request is fast."""
    logger.info("Loading YOLO model at startup...")
    load_model()
    logger.info("Model ready")


@app.get("/health")
async def health():
    return {"status": "ok"}
