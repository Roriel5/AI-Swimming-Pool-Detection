"""
Image I/O, resize, annotation drawing, and base64 encoding utilities.
"""

import base64
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def load_image(path: str) -> np.ndarray:
    """
    Load an image from *path* as a BGR uint8 numpy array.

    Raises:
        ValueError: if the file cannot be decoded.
    """
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Could not load image: {path}")
    return img


def save_image(image: np.ndarray, path: str) -> None:
    """Save a BGR numpy array to *path*, creating parent directories as needed."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def decode_bytes(raw: bytes) -> np.ndarray:
    """
    Decode raw image bytes (JPEG, PNG, …) to a BGR numpy array.

    Raises:
        ValueError: if decoding fails.
    """
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image from bytes.")
    return img


# ---------------------------------------------------------------------------
# Resize / preprocessing
# ---------------------------------------------------------------------------

def resize_image(
    image: np.ndarray,
    target_size: Tuple[int, int],
    keep_aspect: bool = True,
    pad_value: int = 114,
) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Resize an image to *target_size* with optional letterbox padding.

    Args:
        image:       BGR or greyscale numpy array.
        target_size: (width, height) in pixels.
        keep_aspect: When True, preserves aspect ratio and pads the remainder.
        pad_value:   Pixel value for padding regions.

    Returns:
        (resized_image, scale_factor, (pad_left, pad_top))
        scale_factor is the ratio of new to original side length.
    """
    h, w = image.shape[:2]
    tw, th = target_size

    if keep_aspect:
        scale = min(tw / w, th / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

        channels = image.shape[2] if image.ndim == 3 else None
        canvas = (
            np.full((th, tw, channels), pad_value, dtype=image.dtype)
            if channels
            else np.full((th, tw), pad_value, dtype=image.dtype)
        )
        pad_x, pad_y = (tw - nw) // 2, (th - nh) // 2
        canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = resized
        return canvas, scale, (pad_x, pad_y)

    resized = cv2.resize(image, (tw, th), interpolation=cv2.INTER_LINEAR)
    scale = tw / w
    return resized, scale, (0, 0)


def normalize_image(image: np.ndarray) -> np.ndarray:
    """Normalise a uint8 image to float32 in [0, 1]."""
    return image.astype(np.float32) / 255.0


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply CLAHE contrast enhancement to the L-channel of a BGR image.

    Useful for improving detection in low-contrast aerial imagery.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_ch, a_ch, b_ch = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    l_eq = clahe.apply(l_ch)
    return cv2.cvtColor(cv2.merge([l_eq, a_ch, b_ch]), cv2.COLOR_LAB2BGR)


# ---------------------------------------------------------------------------
# Annotation drawing
# ---------------------------------------------------------------------------

def draw_annotations(
    image: np.ndarray,
    bboxes: List[List[int]],
    masks: Optional[List[np.ndarray]] = None,
    labels: Optional[List[str]] = None,
    confidences: Optional[List[float]] = None,
) -> np.ndarray:
    """
    Draw bounding boxes, optional segmentation masks, and labels on *image*.

    Args:
        image:       BGR uint8 array (not modified in place).
        bboxes:      List of [x1, y1, x2, y2] boxes.
        masks:       Optional list of binary mask arrays (0 / 1).
        labels:      Optional list of class name strings.
        confidences: Optional list of confidence floats.

    Returns:
        Annotated copy of the image.
    """
    _COLORS = [
        (0, 255, 0), (255, 100, 0), (0, 100, 255),
        (255, 0, 255), (0, 255, 255), (255, 255, 0),
    ]

    vis = image.copy()

    for i, bbox in enumerate(bboxes):
        color = _COLORS[i % len(_COLORS)]
        x1, y1, x2, y2 = [int(v) for v in bbox]

        # Bounding box
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

        # Mask overlay
        if masks is not None and i < len(masks):
            overlay = vis.copy()
            overlay[masks[i] > 0] = color
            vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)

        # Label
        parts: List[str] = []
        if labels and i < len(labels):
            parts.append(labels[i])
        if confidences and i < len(confidences):
            parts.append(f"{confidences[i]:.2f}")

        if parts:
            text = " ".join(parts)
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(text, font, 0.6, 2)
            cv2.rectangle(vis, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(vis, text, (x1 + 2, y1 - 4), font, 0.6, (0, 0, 0), 2)

    return vis


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def bgr_to_base64(image: np.ndarray, quality: int = 90) -> str:
    """
    Encode a BGR image as a base64-encoded JPEG string.

    Args:
        image:   BGR uint8 array.
        quality: JPEG quality (1 – 100).

    Returns:
        Base64 ASCII string.
    """
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buf = cv2.imencode(".jpg", image, encode_params)
    return base64.b64encode(buf).decode("utf-8")
