"""
Pool detection inference module using a trained YOLOv11 segmentation model.

Responsible for:
- Loading model weights
- Running single-image or batch inference
- Returning structured detection results
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class PoolDetector:
    """
    Wraps a YOLOv11 segmentation model for swimming pool detection.

    Attributes:
        confidence_threshold: Minimum confidence to accept a detection.
        iou_threshold:        Non-maximum suppression IoU threshold.
        device:               Torch device string (e.g. 'cpu', 'cuda').
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
    ) -> None:
        """
        Args:
            model_path:            Path to trained .pt weights.  Falls back to the
                                   base model when the file is missing (useful before
                                   first training run).
            confidence_threshold:  Detection confidence cut-off.
            iou_threshold:         NMS IoU cut-off.
        """
        from app.config import DEVICE

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = DEVICE
        self.model = None

        path = Path(model_path)
        if path.exists():
            self._load_model(str(path))
        else:
            logger.warning(
                "Trained weights not found at '%s'. Loading base model 'yolo11s-seg.pt'.", path
            )
            self._load_model("yolo11s-seg.pt")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self, path: str) -> None:
        from ultralytics import YOLO

        self.model = YOLO(path)
        self.model.to(self.device)
        logger.info("Model loaded from '%s' → device: %s", path, self.device)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Run pool detection on a single BGR image.

        Args:
            image: BGR uint8 numpy array.

        Returns:
            dict with keys:
                pool_detected (bool)
                confidence    (float)
                bbox          (List[int])  — [x1, y1, x2, y2] in pixels
                mask          (List[List[int]] | None) — 2-D binary mask
                all_detections (List[dict]) — every detection above threshold
        """
        if self.model is None:
            raise RuntimeError("Model has not been loaded.")

        results = self.model(
            image,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        result = results[0]

        if result.boxes is None or len(result.boxes) == 0:
            return {
                "pool_detected": False,
                "confidence": 0.0,
                "bbox": [],
                "mask": None,
                "all_detections": [],
            }

        # Select highest-confidence detection
        confs = result.boxes.conf.cpu().numpy()
        best_idx = int(np.argmax(confs))

        bbox = result.boxes.xyxy[best_idx].cpu().numpy().astype(int).tolist()
        confidence = float(confs[best_idx])

        # Segmentation mask
        mask_list: Optional[List] = None
        if result.masks is not None and best_idx < len(result.masks):
            h, w = image.shape[:2]
            raw_mask = result.masks.data[best_idx].cpu().numpy()
            mask_resized = cv2.resize(raw_mask, (w, h), interpolation=cv2.INTER_NEAREST)
            binary_mask = (mask_resized > 0.5).astype(np.uint8)
            mask_list = binary_mask.tolist()

        return {
            "pool_detected": True,
            "confidence": round(confidence, 4),
            "bbox": bbox,
            "mask": mask_list,
            "all_detections": self._format_all(result),
        }

    def detect_batch(self, images: List[np.ndarray]) -> List[Dict[str, Any]]:
        """
        Run detection on a list of images.

        Args:
            images: list of BGR uint8 arrays.

        Returns:
            List of detection result dicts (same schema as detect()).
        """
        return [self.detect(img) for img in images]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _format_all(self, result) -> List[Dict[str, Any]]:
        """Serialise all detections above threshold."""
        out = []
        for i in range(len(result.boxes)):
            out.append({
                "confidence": round(float(result.boxes.conf[i].cpu()), 4),
                "bbox": result.boxes.xyxy[i].cpu().numpy().astype(int).tolist(),
                "class_id": int(result.boxes.cls[i].cpu()),
            })
        return out
