"""
Image tiling utility for large satellite / aerial images.

Splits a large image into overlapping square tiles suitable for model inference.
Also provides:
  - Label remapping: YOLO-format annotations are clipped and re-normalised to
    each tile's coordinate space.
  - Tile stitching: shifts tile-level bounding-box detections back to original
    image pixel coordinates for downstream NMS.

Usage:
    tiler = ImageTiler(tile_size=512, overlap=64)

    # Tile a file to disk
    saved = tiler.tile_image_file("large.jpg", output_dir="tiles/")

    # Tile in memory
    tiles = tiler.tile_image(image_array)
    for tile, (x1, y1, x2, y2) in tiles:
        detections = model(tile)
"""

import logging
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ImageTiler:
    """
    Splits images into fixed-size overlapping tiles.

    Args:
        tile_size: Side length of each square tile in pixels.
        overlap:   Pixel overlap between adjacent tiles.  Must be < tile_size.
    """

    def __init__(self, tile_size: int = 512, overlap: int = 64) -> None:
        if overlap >= tile_size:
            raise ValueError("overlap must be smaller than tile_size.")
        self.tile_size = tile_size
        self.overlap = overlap
        self.stride = tile_size - overlap

    # ------------------------------------------------------------------
    # Core tiling
    # ------------------------------------------------------------------

    def tile_image(
        self,
        image: np.ndarray,
        pad_value: int = 114,
    ) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Split *image* into overlapping tiles.

        Args:
            image:     Input BGR (or greyscale) numpy array.
            pad_value: Grey value used to pad edge tiles to tile_size.

        Returns:
            List of (tile_array, (x1, y1, x2, y2)) where the coordinate tuple
            gives the tile's top-left / bottom-right in the original image.
            x2 − x1 = y2 − y1 = tile_size (after padding).
        """
        h, w = image.shape[:2]
        tiles: List[Tuple[np.ndarray, Tuple[int, int, int, int]]] = []

        y_starts = self._positions(h)
        x_starts = self._positions(w)

        for ys in y_starts:
            for xs in x_starts:
                ye = min(ys + self.tile_size, h)
                xe = min(xs + self.tile_size, w)
                crop = image[ys:ye, xs:xe]

                if crop.shape[0] < self.tile_size or crop.shape[1] < self.tile_size:
                    crop = self._pad(crop, pad_value)

                tiles.append((crop, (xs, ys, xs + self.tile_size, ys + self.tile_size)))

        return tiles

    def tile_image_file(
        self,
        image_path: str,
        output_dir: str,
        prefix: Optional[str] = None,
        ext: str = ".jpg",
    ) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Tile an image file and save each tile to *output_dir*.

        Args:
            image_path: Source image path.
            output_dir: Directory for output tile files.
            prefix:     Filename stem prefix.  Defaults to the source stem.
            ext:        Output file extension (e.g. '.jpg', '.png').

        Returns:
            List of (saved_path, (x1, y1, x2, y2)) for each tile.
        """
        image_path = Path(image_path)
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Cannot read image: {image_path}")

        prefix = prefix or image_path.stem
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        tiles = self.tile_image(image)
        saved = []

        for idx, (tile, (x1, y1, x2, y2)) in enumerate(tiles):
            fname = f"{prefix}_t{idx:04d}_x{x1}_y{y1}{ext}"
            out_path = output_dir / fname
            cv2.imwrite(str(out_path), tile)
            saved.append((str(out_path), (x1, y1, x2, y2)))

        logger.info("Saved %d tiles from '%s' → '%s'", len(saved), image_path.name, output_dir)
        return saved

    # ------------------------------------------------------------------
    # Label remapping
    # ------------------------------------------------------------------

    def remap_labels_to_tile(
        self,
        labels: List[Tuple[int, float, float, float, float]],
        tile_coords: Tuple[int, int, int, int],
        orig_w: int,
        orig_h: int,
        min_overlap_ratio: float = 0.20,
    ) -> List[Tuple[int, float, float, float, float]]:
        """
        Clip and re-normalise YOLO labels from original-image space to tile space.

        Args:
            labels:            List of (class_id, xc, yc, bw, bh) normalised to
                               original image dimensions.
            tile_coords:       (x1, y1, x2, y2) pixels in the original image.
            orig_w, orig_h:    Original image dimensions.
            min_overlap_ratio: Minimum fraction of a bbox that must fall inside the
                               tile for the annotation to be kept.

        Returns:
            Filtered list of (class_id, xc, yc, bw, bh) normalised to tile size.
        """
        tx1, ty1, tx2, ty2 = tile_coords
        tw = tx2 - tx1
        th = ty2 - ty1

        remapped = []

        for cls_id, xc, yc, bw, bh in labels:
            # Absolute coordinates in original image
            ax1 = (xc - bw / 2) * orig_w
            ay1 = (yc - bh / 2) * orig_h
            ax2 = (xc + bw / 2) * orig_w
            ay2 = (yc + bh / 2) * orig_h

            # Clip to tile
            cx1 = max(ax1, tx1)
            cy1 = max(ay1, ty1)
            cx2 = min(ax2, tx2)
            cy2 = min(ay2, ty2)

            if cx1 >= cx2 or cy1 >= cy2:
                continue

            orig_area = (ax2 - ax1) * (ay2 - ay1)
            clip_area = (cx2 - cx1) * (cy2 - cy1)
            if orig_area > 0 and clip_area / orig_area < min_overlap_ratio:
                continue

            # Re-normalise to tile
            norm_xc = ((cx1 + cx2) / 2.0 - tx1) / tw
            norm_yc = ((cy1 + cy2) / 2.0 - ty1) / th
            norm_bw = (cx2 - cx1) / tw
            norm_bh = (cy2 - cy1) / th

            remapped.append((
                cls_id,
                max(0.0, min(1.0, norm_xc)),
                max(0.0, min(1.0, norm_yc)),
                max(0.0, min(1.0, norm_bw)),
                max(0.0, min(1.0, norm_bh)),
            ))

        return remapped

    # ------------------------------------------------------------------
    # Stitching tile detections back to original coordinates
    # ------------------------------------------------------------------

    def stitch_predictions(
        self,
        tile_predictions: List[Tuple[List, Tuple[int, int, int, int]]],
        orig_h: int,
        orig_w: int,
    ) -> List[List]:
        """
        Shift tile-level detections to original image coordinates.

        Args:
            tile_predictions: List of (detections, (tx1, ty1, tx2, ty2)).
                              Each detection row: [x1, y1, x2, y2, conf, cls].
            orig_h, orig_w:   Original image dimensions for clamping.

        Returns:
            Flat list of detections: [x1, y1, x2, y2, conf, cls] in original pixels.
        """
        all_dets = []
        for detections, (tx1, ty1, _, _) in tile_predictions:
            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                ox1 = max(0, min(int(x1 + tx1), orig_w))
                oy1 = max(0, min(int(y1 + ty1), orig_h))
                ox2 = max(0, min(int(x2 + tx1), orig_w))
                oy2 = max(0, min(int(y2 + ty1), orig_h))
                all_dets.append([ox1, oy1, ox2, oy2, conf, cls])
        return all_dets

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _positions(self, length: int) -> List[int]:
        """Compute tile start positions along one axis."""
        positions = list(range(0, length - self.tile_size + 1, self.stride))
        # Make sure the last chunk covers the image end
        if not positions or positions[-1] + self.tile_size < length:
            positions.append(max(0, length - self.tile_size))
        # Remove duplicates (can happen when image < tile_size)
        return sorted(set(positions))

    def _pad(self, tile: np.ndarray, pad_value: int) -> np.ndarray:
        """Pad *tile* to (tile_size, tile_size) with *pad_value*."""
        th, tw = tile.shape[:2]
        pad_h = self.tile_size - th
        pad_w = self.tile_size - tw

        if tile.ndim == 3:
            canvas = np.full(
                (self.tile_size, self.tile_size, tile.shape[2]),
                pad_value,
                dtype=tile.dtype,
            )
        else:
            canvas = np.full((self.tile_size, self.tile_size), pad_value, dtype=tile.dtype)

        canvas[:th, :tw] = tile
        return canvas
