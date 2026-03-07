"""
YOLOv11 segmentation training pipeline for swimming pool detection.

Usage (CLI):
    python -m app.models.train_yolo \\
        --data  backend/datasets/data.yaml \\
        --model yolo11s-seg.pt \\
        --epochs 50 --batch 8 --imgsz 1024 \\
        --output backend/models

Usage (Python):
    from app.models.train_yolo import train, create_dataset_yaml
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataset YAML helper
# ---------------------------------------------------------------------------

def create_dataset_yaml(
    dataset_path: Path,
    output_yaml: Path,
    class_names: Optional[List[str]] = None,
) -> Path:
    """
    Generate a YOLO-format dataset YAML configuration file.

    Args:
        dataset_path:  Root directory that contains images/ and labels/.
        output_yaml:   Destination path for the YAML file.
        class_names:   List of class names (default: ["pool"]).

    Returns:
        Path to the written YAML file.
    """
    if class_names is None:
        class_names = ["pool"]

    config = {
        "path": str(dataset_path.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": len(class_names),
        "names": class_names,
    }

    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(output_yaml, "w") as fh:
        yaml.dump(config, fh, default_flow_style=False)

    logger.info("Dataset YAML written to %s", output_yaml)
    return output_yaml


# ---------------------------------------------------------------------------
# Training pipeline
# ---------------------------------------------------------------------------

def train(
    dataset_yaml: str,
    base_model: str = "yolo11s-seg.pt",
    output_dir: str = "backend/models",
    epochs: int = 50,
    batch_size: int = 8,
    image_size: int = 1024,
    device: Optional[str] = None,
    resume: bool = False,
    project: str = "runs/segment",
    name: str = "pool_detection",
    workers: int = 0,
) -> str:
    """
    Fine-tune a YOLOv11 segmentation model for pool detection.

    Args:
        dataset_yaml:  Path to the dataset YAML config.
        base_model:    Base YOLO model identifier or .pt path.
        output_dir:    Directory where best.pt will be copied after training.
        epochs:        Number of training epochs.
        batch_size:    Batch size.
        image_size:    Input image size (square).
        device:        Compute device string ('cpu', 'cuda', '0', etc.).
                       Auto-detected when None.
        resume:        Resume training from last checkpoint.
        project:       Ultralytics project folder for run artefacts.
        name:          Run name sub-folder inside project/.

    Returns:
        Absolute path to the saved best.pt weights.
    """
    import torch
    from ultralytics import YOLO

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Training on device : %s", device)
    logger.info("Base model         : %s", base_model)
    logger.info("Dataset YAML       : %s", dataset_yaml)
    logger.info("Epochs / Batch / Imgsz : %d / %d / %d", epochs, batch_size, image_size)

    model = YOLO(base_model)

    results = model.train(
        data=dataset_yaml,
        epochs=epochs,
        batch=batch_size,
        imgsz=image_size,
        device=device,
        workers=workers,
        # Optimiser
        optimizer="AdamW",
        lr0=1e-3,
        lrf=0.01,
        momentum=0.937,
        weight_decay=5e-4,
        # Warm-up
        warmup_epochs=3,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        # Augmentations
        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.1,
        degrees=15.0,
        translate=0.1,
        scale=0.5,
        shear=0.0,
        perspective=0.0,
        flipud=0.5,
        fliplr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        erasing=0.4,
        close_mosaic=10,
        # Run management
        project=project,
        name=name,
        save=True,
        save_period=-1,
        resume=resume,
        amp=True,
        verbose=True,
    )

    # Copy best weights to the requested output directory
    best_src = Path(results.save_dir) / "weights" / "best.pt"
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "best.pt"

    if best_src.exists():
        shutil.copy2(best_src, dest)
        logger.info("Best weights saved to %s", dest)
    else:
        logger.warning("best.pt not found at %s — check training logs.", best_src)

    return str(dest)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Train YOLOv11 segmentation model for pool detection")
    parser.add_argument("--data",   type=str, required=True,            help="Path to dataset YAML")
    parser.add_argument("--model",  type=str, default="yolo11s-seg.pt", help="Base model identifier")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch",  type=int, default=8)
    parser.add_argument("--imgsz",  type=int, default=1024)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--output", type=str, default="backend/models")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=0)
    args = parser.parse_args()

    train(
        dataset_yaml=args.data,
        base_model=args.model,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        image_size=args.imgsz,
        device=args.device,
        resume=args.resume,
        workers=args.workers,
    )
