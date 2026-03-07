# Pool Risk AI — Swimming Pool Detection & Insurance Risk Intelligence

AI-powered swimming pool detection system for insurance risk assessment, built on **YOLOv11 segmentation**, **FastAPI**, and geospatial analysis.

---

## Architecture

```
pool-risk-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── config.py                  # Global settings & paths
│   │   ├── api/
│   │   │   ├── routes_detect.py       # /detect endpoint
│   │   │   └── routes_risk.py         # /risk endpoint
│   │   ├── models/
│   │   │   ├── train_yolo.py          # YOLOv11 training pipeline
│   │   │   ├── detect_pool.py         # Pool detection inference
│   │   │   └── classify_pool.py       # Pool type classification + fence detection
│   │   ├── geospatial/
│   │   │   ├── building_extractor.py  # OSM building footprint extraction
│   │   │   ├── distance_calculator.py # Shapely pool-to-building distance
│   │   │   └── gis_utils.py           # Coordinate transforms, haversine
│   │   ├── risk_engine/
│   │   │   └── risk_scoring.py        # Insurance risk score calculation
│   │   ├── change_detection/
│   │   │   └── change_detector.py     # Time-series new-pool detection
│   │   ├── explainability/
│   │   │   └── heatmap_generator.py   # Grad-CAM heatmap overlay
│   │   ├── preprocessing/
│   │   │   ├── xml_to_yolo_converter.py  # Pascal VOC → YOLO label conversion
│   │   │   └── image_tiling.py           # Large-image tile splitting
│   │   └── utils/
│   │       ├── image_utils.py         # Image I/O, resize, draw utils
│   │       └── dataset_utils.py       # Dataset split, verification
│   ├── datasets/                      # Place your dataset here
│   ├── models/                        # Trained weights saved here
│   └── outputs/                       # Inference outputs & visualizations
└── requirements.txt
```

---

## Setup

```bash
# Clone / open project
cd pool-risk-ai

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / Mac

# Install dependencies
pip install -r requirements.txt
```

---

## Dataset Preparation

> **All Python commands must be run from the `backend/` directory**, because that is the root where the `app` package lives.
> ```cmd
> cd pool-risk-ai\backend
> ```

### 1. Convert Pascal VOC XML → YOLO labels

```bash
# run from pool-risk-ai/backend/
python -m app.preprocessing.xml_to_yolo_converter \
    --xml_dir  datasets/raw/annotations \
    --output_dir datasets/raw/labels
```

### 2. Split into train / val / test

```bash
# run from pool-risk-ai/backend/
python -c "
from app.utils.dataset_utils import split_dataset
split_dataset(
    image_dir='datasets/raw/images',
    label_dir='datasets/raw/labels',
    output_dir='datasets',
    train_ratio=0.7,
    val_ratio=0.2,
    test_ratio=0.1,
)
"
```

### 3. (Optional) Tile large satellite images

```bash
# run from pool-risk-ai/backend/
python -c "
from app.preprocessing.image_tiling import ImageTiler
tiler = ImageTiler(tile_size=512, overlap=64)
tiler.tile_image_file('large_image.tif', output_dir='datasets/tiles')
"
```

---

## Training

```bash
# Run from pool-risk-ai/backend/
python -m app.models.train_yolo \
    --data  datasets/data.yaml \
    --model yolo11s-seg.pt \
    --epochs 50 \
    --batch  8 \
    --imgsz  1024 \
    --output models
```

A `data.yaml` template is auto-generated when you call `create_dataset_yaml()`:

```bash
# Run from pool-risk-ai/backend/
python -c "
from app.models.train_yolo import create_dataset_yaml
from pathlib import Path
create_dataset_yaml(
    dataset_path=Path('datasets'),
    output_yaml=Path('datasets/data.yaml'),
    class_names=['pool'],
)
"
```

---

## Running the API

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI: http://localhost:8000/docs

---

## API Endpoints

### `POST /api/v1/detect`

Detect and classify a swimming pool in an aerial image.

**Request:** multipart/form-data with `file` (image)

**Response:**
```json
{
  "pool_detected": true,
  "confidence": 0.92,
  "bbox": [120, 80, 340, 260],
  "pool_type": "uncovered",
  "pool_area": 4800.0
}
```

---

### `POST /api/v1/risk`

Full insurance risk assessment.

**Request:** multipart/form-data

| Field | Type | Description |
|---|---|---|
| `file` | image | Current satellite image |
| `file_t1` | image (optional) | Prior-date image for change detection |
| `lat` | float (optional) | Latitude for OSM building lookup |
| `lon` | float (optional) | Longitude for OSM building lookup |
| `pixels_per_meter` | float | Image resolution (default: 0.5) |

**Response:**
```json
{
  "pool_detected": true,
  "pool_type": "uncovered",
  "confidence": 0.92,
  "distance_from_house": "4.2m",
  "fence_detected": false,
  "change_detected": true,
  "risk_score": 125,
  "risk_level": "HIGH",
  "risk_factors": [
    "Pool detected (+40)",
    "Uncovered/in-ground pool (+25)",
    "Large pool area (72.0 m²) (+20)",
    "No fence detected (+20)",
    "Newly built pool detected (+25)"
  ]
}
```

---

## Risk Scoring Logic

| Factor | Score |
|---|---|
| Pool present | +40 |
| Uncovered / in-ground pool | +25 |
| Large pool (>50 m²) | +20 |
| Pool < 3 m from building | +15 |
| No fence detected | +20 |
| Newly built pool | +25 |

| Total Score | Risk Level |
|---|---|
| 0 – 50 | LOW |
| 51 – 90 | MEDIUM |
| 91+ | HIGH |

---

## Explainability

Generate a Grad-CAM heatmap showing which image regions drove the detection:

```python
from app.explainability.heatmap_generator import HeatmapGenerator
from ultralytics import YOLO
import cv2

model = YOLO("backend/models/best.pt")
gen = HeatmapGenerator(yolo_model=model)

image = cv2.imread("aerial.jpg")
overlay = gen.generate_gradcam(image)
cv2.imwrite("gradcam_output.jpg", overlay)
```

---

## Change Detection

```python
from app.change_detection.change_detector import ChangeDetector
from app.models.detect_pool import PoolDetector

detector = PoolDetector("backend/models/best.pt")
cd = ChangeDetector(pool_detector=detector)

result = cd.detect_change(image_2023, image_2024)
print(result["new_pool"])       # True if pool appeared
print(result["ssim_score"])     # Structural similarity score
```
