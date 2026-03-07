"""
prepare_dataset.py
==================
One-shot dataset preparation script for the CANNES_TILES_512x512 pool dataset.

Run from pool-risk-ai/backend/:
    python prepare_dataset.py

Steps performed
---------------
1. Discover all PNG images and XML annotations in the Kaggle download.
2. Create datasets/raw/images/ and datasets/raw/labels/
3. Copy every PNG into datasets/raw/images/
4. Convert each XML (Pascal VOC) → YOLO .txt label in datasets/raw/labels/
5. Create an *empty* .txt label for images that have no annotation
   (these are the "background / no-pool" negative examples — important for
   reducing false positives during training).
6. Split the full dataset into train / val / test and build the YOLO data.yaml.

After this script completes you can train directly with:
    python -m app.models.train_yolo --data datasets/data.yaml --epochs 50 --batch 8
"""

import logging
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — adjust if your Kaggle download landed elsewhere
# ---------------------------------------------------------------------------
WORKSPACE = Path(__file__).resolve().parent.parent.parent  # Desktop/Yolov11 Pools/

KAGGLE_BASE = WORKSPACE / "alexj21" / "swimming-pool-512x512" / "versions" / "5"
SRC_IMAGES  = KAGGLE_BASE / "CANNES_TILES_512x512_PNG"  / "CANNES_TILES_512x512_PNG"
SRC_XMLS    = KAGGLE_BASE / "CANNES_TILES_512x512_labels" / "CANNES_TILES_512x512_labels"

# Output layout inside backend/
BACKEND_DIR  = Path(__file__).resolve().parent
RAW_IMAGES   = BACKEND_DIR / "datasets" / "raw" / "images"
RAW_LABELS   = BACKEND_DIR / "datasets" / "raw" / "labels"
DATASET_ROOT = BACKEND_DIR / "datasets"

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
if not SRC_IMAGES.exists():
    log.error("Image directory not found: %s", SRC_IMAGES)
    sys.exit(1)
if not SRC_XMLS.exists():
    log.error("XML directory not found: %s", SRC_XMLS)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Step 1 — gather files
# ---------------------------------------------------------------------------
png_files = sorted(SRC_IMAGES.glob("*.png"))
xml_files = {f.stem: f for f in SRC_XMLS.glob("*.xml")}

log.info("Found %d PNG images", len(png_files))
log.info("Found %d XML annotations", len(xml_files))

# ---------------------------------------------------------------------------
# Step 2 — create output directories
# ---------------------------------------------------------------------------
RAW_IMAGES.mkdir(parents=True, exist_ok=True)
RAW_LABELS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Step 3 — copy images
# ---------------------------------------------------------------------------
log.info("Copying images …")
for i, src in enumerate(png_files):
    dst = RAW_IMAGES / src.name
    if not dst.exists():
        shutil.copy2(src, dst)
    if (i + 1) % 200 == 0:
        log.info("  %d / %d copied", i + 1, len(png_files))
log.info("  Done — %d images in %s", len(png_files), RAW_IMAGES)

# ---------------------------------------------------------------------------
# Step 4 — convert XML → YOLO .txt
# ---------------------------------------------------------------------------
log.info("Converting XML annotations …")

from app.preprocessing.xml_to_yolo_converter import convert_single

converted = 0
failed = 0
for stem, xml_path in xml_files.items():
    result = convert_single(str(xml_path), str(RAW_LABELS))
    if result:
        converted += 1
    else:
        failed += 1

log.info("  Converted %d / %d XMLs   (%d failed)", converted, len(xml_files), failed)

# ---------------------------------------------------------------------------
# Step 5 — skip negatives for segmentation training
# ---------------------------------------------------------------------------
# Ultralytics YOLOv11 segmentation crashes during augmentation when it
# encounters images with empty label files (the semantic aug pipeline does
# index[0] - 1 on an empty cls tensor).  For segmentation we do NOT need
# explicit negative examples — the model learns background from the regions
# inside annotated images that are not labelled.  Only annotated tiles go
# into the split.
log.info("Skipping empty-label negatives (not compatible with YOLO seg training).")

# ---------------------------------------------------------------------------
# Step 6 — train / val / test split
# ---------------------------------------------------------------------------
log.info("Splitting dataset …")
from app.utils.dataset_utils import split_dataset

counts = split_dataset(
    image_dir=str(RAW_IMAGES),
    label_dir=str(RAW_LABELS),
    output_dir=str(DATASET_ROOT),
    train_ratio=0.70,
    val_ratio=0.20,
    test_ratio=0.10,
    seed=42,
)
log.info("  Split: %s", counts)

# ---------------------------------------------------------------------------
# Step 7 — generate data.yaml
# ---------------------------------------------------------------------------
log.info("Writing data.yaml …")
from app.models.train_yolo import create_dataset_yaml

create_dataset_yaml(
    dataset_path=DATASET_ROOT,
    output_yaml=DATASET_ROOT / "data.yaml",
    class_names=["pool"],
)

log.info("")
log.info("=" * 60)
log.info("Dataset ready!  Summary:")
log.info("  Total images : %d", len(png_files))
log.info("  With labels  : %d", converted)
log.info("  Negatives    : skipped (not used for seg training)")
log.info("  Train        : %d", counts.get("train", 0))
log.info("  Val          : %d", counts.get("val", 0))
log.info("  Test         : %d", counts.get("test", 0))
log.info("  data.yaml    : %s", DATASET_ROOT / 'data.yaml')
log.info("=" * 60)
log.info("")
log.info("Train with:")
log.info("  python -m app.models.train_yolo --data datasets/data.yaml --epochs 50 --batch 8")
