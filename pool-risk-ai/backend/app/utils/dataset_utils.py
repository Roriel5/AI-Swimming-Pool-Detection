"""
Dataset management utilities: splitting, verification, and statistics.
"""

import logging
import random
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")


# ---------------------------------------------------------------------------
# Dataset splitting
# ---------------------------------------------------------------------------

def split_dataset(
    image_dir: str,
    label_dir: str,
    output_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.20,
    test_ratio: float = 0.10,
    seed: int = 42,
    extensions: Tuple[str, ...] = _IMAGE_EXTENSIONS,
) -> Dict[str, int]:
    """
    Split a flat image/label dataset into train / val / test subsets.

    Expects *image_dir* and *label_dir* to share the same file stems.
    Creates the YOLO directory structure under *output_dir*:

        output_dir/
          images/train/  images/val/  images/test/
          labels/train/  labels/val/  labels/test/

    Args:
        image_dir:   Directory of source images.
        label_dir:   Directory of YOLO .txt label files.
        output_dir:  Root directory for the split output.
        train_ratio: Fraction of data for training.
        val_ratio:   Fraction for validation.
        test_ratio:  Fraction for test (remainder after train+val).
        seed:        Random seed for reproducible shuffles.
        extensions:  Recognised image file extensions.

    Returns:
        dict {'train': n, 'val': n, 'test': n} with sample counts.
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    image_dir, label_dir, output_dir = Path(image_dir), Path(label_dir), Path(output_dir)

    # Collect paired image/label samples
    pairs: List[Tuple[Path, Path]] = []
    for ext in extensions:
        for img in image_dir.glob(f"*{ext}"):
            lbl = label_dir / (img.stem + ".txt")
            if lbl.exists():
                pairs.append((img, lbl))

    if not pairs:
        logger.warning("No paired image/label samples found in '%s' + '%s'.", image_dir, label_dir)
        return {"train": 0, "val": 0, "test": 0}

    random.seed(seed)
    random.shuffle(pairs)

    n = len(pairs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits: Dict[str, List] = {
        "train": pairs[:n_train],
        "val":   pairs[n_train:n_train + n_val],
        "test":  pairs[n_train + n_val:],
    }
    counts: Dict[str, int] = {}

    for split_name, split_pairs in splits.items():
        img_out = output_dir / "images" / split_name
        lbl_out = output_dir / "labels" / split_name
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        for img_path, lbl_path in split_pairs:
            shutil.copy2(img_path, img_out / img_path.name)
            shutil.copy2(lbl_path, lbl_out / lbl_path.name)

        counts[split_name] = len(split_pairs)
        logger.info("  %-6s → %d samples", split_name, len(split_pairs))

    logger.info("Dataset split complete: %s", counts)
    return counts


# ---------------------------------------------------------------------------
# Dataset verification
# ---------------------------------------------------------------------------

def verify_dataset(dataset_dir: str) -> Dict[str, int]:
    """
    Check that every image in a split dataset has a matching label file.

    Args:
        dataset_dir: Root directory with images/ and labels/ sub-trees.

    Returns:
        dict with 'total_images', 'paired', 'missing_labels', 'empty_labels'.
    """
    dataset_dir = Path(dataset_dir)
    stats = {"total_images": 0, "paired": 0, "missing_labels": 0, "empty_labels": 0}

    for split in ("train", "val", "test"):
        img_dir = dataset_dir / "images" / split
        lbl_dir = dataset_dir / "labels" / split

        if not img_dir.exists():
            continue

        for img_path in img_dir.iterdir():
            if img_path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue

            stats["total_images"] += 1
            lbl_path = lbl_dir / (img_path.stem + ".txt")

            if not lbl_path.exists():
                stats["missing_labels"] += 1
            elif lbl_path.read_text().strip():
                stats["paired"] += 1
            else:
                stats["empty_labels"] += 1

    return stats


# ---------------------------------------------------------------------------
# Class distribution
# ---------------------------------------------------------------------------

def compute_class_distribution(label_dir: str) -> Dict[int, int]:
    """
    Count the number of annotated instances for each class.

    Args:
        label_dir: Directory (searched recursively) containing YOLO .txt files.

    Returns:
        dict mapping class_id (int) to instance count.
    """
    distribution: Dict[int, int] = {}

    for lbl_file in Path(label_dir).rglob("*.txt"):
        for line in lbl_file.read_text().splitlines():
            parts = line.strip().split()
            if parts:
                cls_id = int(parts[0])
                distribution[cls_id] = distribution.get(cls_id, 0) + 1

    return distribution


# ---------------------------------------------------------------------------
# Anchor / object statistics
# ---------------------------------------------------------------------------

def compute_object_size_stats(
    label_dir: str,
    image_size: int = 640,
) -> Dict[str, float]:
    """
    Compute mean and standard deviation of object bounding-box dimensions
    across all YOLO label files in *label_dir*.

    Args:
        label_dir:   Directory of .txt label files.
        image_size:  Reference image size for scaling normalised coords.

    Returns:
        dict with 'mean_w', 'std_w', 'mean_h', 'std_h', 'count'.
    """
    widths: List[float] = []
    heights: List[float] = []

    for lbl_file in Path(label_dir).rglob("*.txt"):
        for line in lbl_file.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                widths.append(float(parts[3]) * image_size)
                heights.append(float(parts[4]) * image_size)

    if not widths:
        return {"mean_w": 0.0, "std_w": 0.0, "mean_h": 0.0, "std_h": 0.0, "count": 0}

    w_arr = np.array(widths)
    h_arr = np.array(heights)
    return {
        "mean_w": float(np.mean(w_arr)),
        "std_w":  float(np.std(w_arr)),
        "mean_h": float(np.mean(h_arr)),
        "std_h":  float(np.std(h_arr)),
        "count":  len(widths),
    }
