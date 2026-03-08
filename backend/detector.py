"""
YOLOv11 Object Detection for Swimming Pools

This detector uses ultralytics YOLOv11 medium for identification of swimming pools.
"""

import time
import io
import math
import numpy as np
import cv2
import exifread
import os
from ultralytics import YOLO

# ── YOLO Config ───────────────────────────────────────────────────────────────
# Define the path to the custom YOLO model.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "YOLOV11M WEIGHTS", "best.pt")
model = None

def _load_model():
    global model
    if model is None:
        try:
            model = YOLO(MODEL_PATH)
        except Exception as e:
            print(f"Error loading YOLO model: {e}")

_load_model()

def _get_decimal_from_dms(dms, ref):
    try:
        degrees = float(dms.values[0].num) / float(dms.values[0].den)
        minutes = float(dms.values[1].num) / float(dms.values[1].den)
        seconds = float(dms.values[2].num) / float(dms.values[2].den)
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ["S", "W"]:
            decimal = -decimal
        return decimal
    except Exception:
        return None

def _extract_gps(image_bytes: bytes):
    tags = exifread.process_file(io.BytesIO(image_bytes), details=False)
    if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
        lat_ref = tags["GPS GPSLatitudeRef"].values if "GPS GPSLatitudeRef" in tags else "N"
        lng_ref = tags["GPS GPSLongitudeRef"].values if "GPS GPSLongitudeRef" in tags else "E"
        lat = _get_decimal_from_dms(tags["GPS GPSLatitude"], lat_ref)
        lng = _get_decimal_from_dms(tags["GPS GPSLongitude"], lng_ref)
        if lat is not None and lng is not None:
            return round(lat, 6), round(lng, 6)
    return None, None

def detect_pools(image_bytes: bytes, lat: float = None, zoom: int = None) -> dict:
    t0 = time.perf_counter()
    
    if model is None:
        _load_model()
        if model is None:
            return {"error": "YOLO model could not be loaded"}
    
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Could not decode image"}
        
    H, W = img.shape[:2]
    
    # Pre-compute physical pixel resolution if we have geospatial data
    sqm_per_pixel = None
    sqft_per_pixel = None
    if lat is not None and zoom is not None:
        meters_per_pixel = 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)
        sqm_per_pixel = meters_per_pixel ** 2
        sqft_per_pixel = sqm_per_pixel * 10.7639

    total_pools = 0
    all_confidences = []
    
    categories = {
        "uncovered_grounded": [],
        "uncovered_above_ground": [],
        "covered_grounded": [],
        "covered_above_ground": []
    }
    
    # Run YOLO inferencing
    # We will use conf=0.25 as generic default for object detection
    results = model.predict(source=img, conf=0.25, verbose=False)
    
    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue
            
        for box in boxes:
            # Get box coordinates (x_left, y_top, x_right, y_bottom) in pixels
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            
            w_px = x2 - x1
            h_px = y2 - y1
            area_px = w_px * h_px
            
            # Confidence (scale to 0-100 to match old code)
            confidence_pct = round(conf * 100, 1)
            all_confidences.append(confidence_pct)
            
            # Categories:
            # For now, map classes 0-3 to the 4 categories
            category = "uncovered_grounded"
            class_name = model.names[cls_id].lower() if cls_id in model.names else ""
            
            if "uncovered_grounded" in class_name or cls_id == 0:
                category = "uncovered_grounded"
            elif "uncovered_above_ground" in class_name or cls_id == 1:
                category = "uncovered_above_ground"
            elif "covered_grounded" in class_name or cls_id == 2:
                category = "covered_grounded"
            elif "covered_above_ground" in class_name or cls_id == 3:
                category = "covered_above_ground"
            
            # Create polygon logic (4 corners of box as percentage of H/W)
            polygon_points = [
                {"x": round(x1 / W * 100, 2), "y": round(y1 / H * 100, 2)},
                {"x": round(x2 / W * 100, 2), "y": round(y1 / H * 100, 2)},
                {"x": round(x2 / W * 100, 2), "y": round(y2 / H * 100, 2)},
                {"x": round(x1 / W * 100, 2), "y": round(y2 / H * 100, 2)}
            ]
            
            area_sqft = None
            area_sqm = None
            if sqft_per_pixel is not None and sqm_per_pixel is not None:
                area_sqft = round(area_px * sqft_per_pixel)
                area_sqm = round(area_px * sqm_per_pixel)
            
            pool_data = {
                "box": {
                    "x": round(x1 / W * 100, 2),
                    "y": round(y1 / H * 100, 2),
                    "w": round(w_px / W * 100, 2),
                    "h": round(h_px / H * 100, 2),
                    "confidence": confidence_pct,
                },
                "polygon": {
                    "points": polygon_points,
                    "confidence": confidence_pct
                },
                "is_covered": "covered" in category,
                "is_above_ground": "above_ground" in category,
                "area_sqft": area_sqft,
                "area_sqm": area_sqm
            }
            
            categories[category].append(pool_data)
            total_pools += 1

    elapsed = round(time.perf_counter() - t0, 2)
    avg_conf = round(float(np.mean(all_confidences)), 1) if all_confidences else 0.0
    
    # Try to extract GPS from original bytes
    img_lat, img_lng = _extract_gps(image_bytes)
    
    # If GPS provided via API, override EXIF lat but keep EXIF lng if not provided
    # Keep original logic which was returning EXIF GPS or None
    lat_final = img_lat if img_lat is not None else lat
    lng_final = img_lng
    
    return {
        "pools": total_pools,
        "confidence": avg_conf,
        "time": elapsed,
        "lat": lat_final,
        "lng": lng_final,
        "categories": categories
    }
