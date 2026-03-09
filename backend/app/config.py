import os
from pathlib import Path

from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / "app" / ".env")
WEIGHTS_PATH = BASE_DIR.parent / "yolov11m weights" / "best.pt"

# Mapbox
MAPBOX_ACCESS_TOKEN = os.getenv("MAPBOX_ACCESS_TOKEN")

MAPBOX_TILE_URL = (
    "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"
    "/{lng},{lat},{zoom}/{size}x{size}"
    "?access_token={token}"
)

# Model
MODEL_CONF = 0.15
MODEL_IMG_SIZE = 640
DEFAULT_ZOOM = 18
TILE_SIZE = 640

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
