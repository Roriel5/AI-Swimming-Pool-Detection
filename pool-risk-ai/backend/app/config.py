"""
Global configuration and path settings for Pool Risk AI.
All paths are derived from this file — edit here to relocate the project.
"""

from pathlib import Path
import torch

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # pool-risk-ai/
BACKEND_DIR = BASE_DIR / "backend"
APP_DIR = BACKEND_DIR / "app"

# ---------------------------------------------------------------------------
# Model settings
# ---------------------------------------------------------------------------
MODEL_PATH: Path = BACKEND_DIR / "models" / "best.pt"
BASE_MODEL: str = "yolo11s-seg.pt"

# ---------------------------------------------------------------------------
# Dataset / output paths
# ---------------------------------------------------------------------------
DATASET_PATH: Path = BACKEND_DIR / "datasets"
OUTPUT_PATH: Path = BACKEND_DIR / "outputs"

# ---------------------------------------------------------------------------
# Compute device
# ---------------------------------------------------------------------------
DEVICE: str = "cuda" if torch.cuda.is_available() else "cpu"

# ---------------------------------------------------------------------------
# Inference hyper-parameters
# ---------------------------------------------------------------------------
CONFIDENCE_THRESHOLD: float = 0.5
IOU_THRESHOLD: float = 0.45
IMAGE_SIZE: int = 1024        # pixels — used for training & tiled inference

# ---------------------------------------------------------------------------
# Tiling
# ---------------------------------------------------------------------------
TILE_SIZE: int = 512
TILE_OVERLAP: int = 64

# ---------------------------------------------------------------------------
# Training hyper-parameters
# ---------------------------------------------------------------------------
EPOCHS: int = 50
BATCH_SIZE: int = 8
OPTIMIZER: str = "AdamW"

# ---------------------------------------------------------------------------
# Risk scoring thresholds
# ---------------------------------------------------------------------------
LARGE_POOL_AREA_PX: float = 10_000.0   # pixels² — adjust when scale is known
LARGE_POOL_AREA_M2: float = 50.0       # m²
CLOSE_DISTANCE_M: float = 3.0          # metres
