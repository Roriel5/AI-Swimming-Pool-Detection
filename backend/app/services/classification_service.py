from __future__ import annotations

import logging

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms

from app.models.yolo_model import get_device

logger = logging.getLogger(__name__)

POOL_TYPES = ["above_ground", "covered", "in_ground", "uncovered"]

_classifier: nn.Module | None = None
_transform: transforms.Compose | None = None


def _build_classifier() -> nn.Module:
    """Build a lightweight MobileNetV3-Small classifier for pool types.

    Uses feature extraction from the pretrained backbone with a custom
    classification head. Works without a separately trained checkpoint
    by applying heuristic-based classification on image features.
    """
    from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights

    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    # Replace the classifier head for 4 pool-type classes
    in_features = model.classifier[0].in_features
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 128),
        nn.Hardswish(),
        nn.Dropout(p=0.2),
        nn.Linear(128, len(POOL_TYPES)),
    )
    return model


def _get_transform() -> transforms.Compose:
    global _transform
    if _transform is None:
        _transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])
    return _transform


def _load_classifier() -> nn.Module:
    global _classifier
    if _classifier is not None:
        return _classifier

    device = get_device()
    _classifier = _build_classifier()
    _classifier.to(device)
    _classifier.eval()
    logger.info("Pool classifier loaded on %s", device)
    return _classifier


def classify_pool_crop(crop_bgr: np.ndarray) -> dict:
    """Classify a single pool crop into a pool type.

    Args:
        crop_bgr: BGR image crop of the detected pool region.

    Returns:
        {"pool_type": str, "type_confidence": float}
    """
    if crop_bgr.size == 0 or crop_bgr.shape[0] < 4 or crop_bgr.shape[1] < 4:
        return {"pool_type": "in_ground", "type_confidence": 0.5}

    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

    # Heuristic classification based on color and texture analysis
    # This is more reliable than an untrained neural network head
    return _heuristic_classify(crop_rgb)


def _heuristic_classify(crop_rgb: np.ndarray) -> dict:
    """Rule-based pool classification using color/texture features.

    Analyzes the HSV color distribution and edge density of the pool
    crop to determine pool type. This provides consistent results
    without requiring a separately trained classification model.
    """
    hsv = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)

    mean_h = float(np.mean(h))
    mean_s = float(np.mean(s))
    mean_v = float(np.mean(v))
    std_v = float(np.std(v))

    # Edge density — high edges suggest structure / cover
    gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.sum(edges > 0)) / edges.size

    # Blue-dominant hue with decent saturation → uncovered water
    is_blue = 85 <= mean_h <= 135 and mean_s > 60

    # Low saturation + moderate value → covered / tarp
    is_muted = mean_s < 50 and mean_v > 80

    # High edge density + round shape cues → above-ground
    is_edgy = edge_density > 0.15

    # Bright and uniform → clean in-ground pool
    is_uniform = std_v < 35

    scores = {
        "in_ground": 0.0,
        "above_ground": 0.0,
        "covered": 0.0,
        "uncovered": 0.0,
    }

    if is_blue and is_uniform:
        scores["in_ground"] = 0.75
        scores["uncovered"] = 0.15
    elif is_blue and not is_uniform:
        scores["uncovered"] = 0.65
        scores["in_ground"] = 0.20
    elif is_muted:
        scores["covered"] = 0.70
        scores["in_ground"] = 0.15
    elif is_edgy:
        scores["above_ground"] = 0.60
        scores["uncovered"] = 0.20
    else:
        scores["in_ground"] = 0.50
        scores["uncovered"] = 0.25

    # Normalize
    total = sum(scores.values()) or 1.0
    scores = {k: v / total for k, v in scores.items()}

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return {"pool_type": best, "type_confidence": round(scores[best], 3)}


def classify_detections(
    image: np.ndarray, detections: list[dict]
) -> list[dict]:
    """Classify each detection's pool type and append to the detection dict.

    Args:
        image: Full BGR image the detections came from.
        detections: List of dicts with 'bbox' key ([xmin, ymin, xmax, ymax]).

    Returns:
        Same list with 'pool_type' and 'type_confidence' added.
    """
    h_img, w_img = image.shape[:2]

    for det in detections:
        xmin, ymin, xmax, ymax = [int(round(v)) for v in det["bbox"]]
        # Clamp to image bounds
        xmin = max(0, xmin)
        ymin = max(0, ymin)
        xmax = min(w_img, xmax)
        ymax = min(h_img, ymax)

        crop = image[ymin:ymax, xmin:xmax]
        cls = classify_pool_crop(crop)
        det["pool_type"] = cls["pool_type"]
        det["type_confidence"] = cls["type_confidence"]

    return detections
