from __future__ import annotations

import logging
from pathlib import Path

import torch
from ultralytics import YOLO

from app.config import WEIGHTS_PATH, MODEL_CONF, MODEL_IMG_SIZE

logger = logging.getLogger(__name__)

_model: YOLO | None = None
_device: str | None = None


def get_device() -> str:
    """Select best available device."""
    global _device
    if _device is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Inference device: %s", _device)
    return _device


def load_model(weights: Path | str | None = None) -> YOLO:
    """Load YOLOv11 model (singleton). Reuses GPU across requests."""
    global _model
    if _model is not None:
        return _model

    weights = weights or WEIGHTS_PATH
    if not Path(weights).exists():
        raise FileNotFoundError(f"Model weights not found: {weights}")

    device = get_device()
    logger.info("Loading YOLO model from %s on %s", weights, device)
    _model = YOLO(str(weights))
    _model.to(device)
    logger.info("Model loaded successfully")
    return _model


def predict(image, conf: float = MODEL_CONF, imgsz: int = MODEL_IMG_SIZE):
    """Run inference on an image (numpy array or path).

    Returns the YOLO Results object list.
    """
    model = load_model()
    results = model.predict(
        source=image,
        conf=conf,
        imgsz=imgsz,
        device=get_device(),
        verbose=False,
    )
    return results
