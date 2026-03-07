"""
Pascal VOC XML → YOLO format annotation converter.

Input  (per image):
    image.jpg
    annotation.xml   (Pascal VOC format)

Output:
    labels/image.txt

YOLO label format (one row per object):
    <class_id> <x_center> <y_center> <width> <height>

All coordinates are normalised to [0, 1] relative to image dimensions.

Usage (CLI):
    python -m app.preprocessing.xml_to_yolo_converter \\
        --xml_dir  path/to/annotations \\
        --output_dir path/to/labels

Usage (Python):
    from app.preprocessing.xml_to_yolo_converter import convert_batch
    convert_batch("annotations/", "labels/")
"""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default class map — covers common label names found in pool datasets.
# Extend by passing a custom dict to convert_* functions.
DEFAULT_CLASS_MAP: Dict[str, int] = {
    "pool": 0,
    "swimming_pool": 0,
    "swimmingpool": 0,
    "pool_inground": 0,
    "pool_aboveground": 0,
}


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_pascal_voc_xml(xml_path: str) -> Tuple[int, int, List[Dict]]:
    """
    Parse a Pascal VOC XML annotation file.

    Args:
        xml_path: Path to the XML file.

    Returns:
        (image_width, image_height, annotations)
        Each annotation is a dict: {name, xmin, ymin, xmax, ymax}

    Raises:
        ValueError: if the XML is missing a <size> element.
        ET.ParseError: if the XML is malformed.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    size_elem = root.find("size")
    if size_elem is None:
        raise ValueError(f"<size> element missing in {xml_path}")

    img_w = int(size_elem.findtext("width", default="0"))
    img_h = int(size_elem.findtext("height", default="0"))

    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"Invalid image dimensions {img_w}×{img_h} in {xml_path}")

    annotations: List[Dict] = []

    for obj in root.findall("object"):
        name_text = obj.findtext("name")
        if name_text is None:
            continue
        name = name_text.strip().lower()

        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue

        try:
            xmin = float(bndbox.findtext("xmin"))
            ymin = float(bndbox.findtext("ymin"))
            xmax = float(bndbox.findtext("xmax"))
            ymax = float(bndbox.findtext("ymax"))
        except (TypeError, ValueError):
            logger.warning("Skipping malformed bndbox in %s", xml_path)
            continue

        # Clamp to image bounds
        xmin = max(0.0, min(xmin, img_w))
        ymin = max(0.0, min(ymin, img_h))
        xmax = max(0.0, min(xmax, img_w))
        ymax = max(0.0, min(ymax, img_h))

        if xmax <= xmin or ymax <= ymin:
            logger.warning("Skipping degenerate bbox [%s %s %s %s] in %s", xmin, ymin, xmax, ymax, xml_path)
            continue

        annotations.append({"name": name, "xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax})

    return img_w, img_h, annotations


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def annotation_to_yolo(
    ann: Dict,
    img_w: int,
    img_h: int,
    class_map: Dict[str, int],
    seg_format: bool = True,
) -> Optional[tuple]:
    """
    Convert one Pascal VOC annotation dict to YOLO format.

    Args:
        seg_format: When True (default), output YOLO **segmentation** polygon format:
                        class_id  x1 y1  x2 y1  x2 y2  x1 y2
                    using the four corners of the bounding box as the polygon.
                    This is required for YOLOv11-seg models — the detection
                    format (class xc yc w h) leaves the instance mask tensor
                    empty, causing an IndexError in the semantic augmentation.
                    When False, output detection format: class xc yc w h.

    Returns None when the class name is not in class_map.
    """
    name = ann["name"]
    cls_id = class_map.get(name)

    if cls_id is None:
        for key, val in class_map.items():
            if key in name or name in key:
                cls_id = val
                break

    if cls_id is None:
        logger.debug("Unknown class '%s' — skipping.", name)
        return None

    # Normalised bbox corners
    x1 = max(0.0, min(1.0, ann["xmin"] / img_w))
    y1 = max(0.0, min(1.0, ann["ymin"] / img_h))
    x2 = max(0.0, min(1.0, ann["xmax"] / img_w))
    y2 = max(0.0, min(1.0, ann["ymax"] / img_h))

    if seg_format:
        # 4-corner polygon: top-left → top-right → bottom-right → bottom-left
        return (cls_id, x1, y1, x2, y1, x2, y2, x1, y2)
    else:
        xc = (x1 + x2) / 2.0
        yc = (y1 + y2) / 2.0
        bw = x2 - x1
        bh = y2 - y1
        return (cls_id, xc, yc, bw, bh)


# ---------------------------------------------------------------------------
# Single-file conversion
# ---------------------------------------------------------------------------

def convert_single(
    xml_path: str,
    output_dir: str,
    class_map: Optional[Dict[str, int]] = None,
    seg_format: bool = True,
) -> Optional[str]:
    """
    Convert one Pascal VOC XML file to a YOLO label file.

    Args:
        xml_path:   Path to the source XML annotation.
        output_dir: Directory where the .txt file will be written.
        class_map:  Class-name → class-id mapping.
        seg_format: Output segmentation polygon format (default True).
                    Required for YOLOv11-seg training.

    Returns:
        Absolute path of the written .txt file, or None on failure.
    """
    if class_map is None:
        class_map = DEFAULT_CLASS_MAP

    xml_path = Path(xml_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        img_w, img_h, annotations = parse_pascal_voc_xml(str(xml_path))
    except Exception as exc:
        logger.error("Failed to parse %s: %s", xml_path, exc)
        return None

    lines: List[str] = []
    for ann in annotations:
        yolo_ann = annotation_to_yolo(ann, img_w, img_h, class_map, seg_format=seg_format)
        if yolo_ann is not None:
            cls_id, *coords = yolo_ann
            coord_str = " ".join(f"{v:.6f}" for v in coords)
            lines.append(f"{cls_id} {coord_str}")

    out_file = output_dir / (xml_path.stem + ".txt")
    out_file.write_text("\n".join(lines))

    return str(out_file)


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------

def convert_batch(
    xml_dir: str,
    output_dir: str,
    class_map: Optional[Dict[str, int]] = None,
    recursive: bool = True,
    seg_format: bool = True,
) -> Tuple[int, int]:
    """
    Convert all Pascal VOC XML files in *xml_dir* to YOLO format.

    Args:
        xml_dir:    Directory containing .xml annotation files.
        output_dir: Directory for output .txt label files.
        class_map:  Class-name → class-id mapping.
        recursive:  When True, search sub-directories.
        seg_format: Output segmentation polygon format (default True).

    Returns:
        (success_count, fail_count)
    """
    if class_map is None:
        class_map = DEFAULT_CLASS_MAP

    xml_dir = Path(xml_dir)
    xml_files = list(xml_dir.rglob("*.xml") if recursive else xml_dir.glob("*.xml"))

    if not xml_files:
        logger.warning("No XML files found in '%s'", xml_dir)
        return 0, 0

    logger.info("Converting %d XML files…", len(xml_files))
    success = fail = 0

    for xml_file in xml_files:
        result = convert_single(str(xml_file), output_dir, class_map, seg_format=seg_format)
        if result:
            success += 1
        else:
            fail += 1

    logger.info("Done — %d succeeded, %d failed.", success, fail)
    return success, fail


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Convert Pascal VOC XML annotations to YOLO format")
    parser.add_argument("--xml_dir",    type=str, required=True, help="Source directory of XML files")
    parser.add_argument("--output_dir", type=str, required=True, help="Destination directory for .txt labels")
    parser.add_argument("--no_recursive", action="store_true", help="Do not search sub-directories")
    args = parser.parse_args()

    ok, fail = convert_batch(
        xml_dir=args.xml_dir,
        output_dir=args.output_dir,
        recursive=not args.no_recursive,
    )
    print(f"Converted {ok} files — {fail} failures.")
