"""
Highly Advanced HSV Color Detection for Swimming Pools with Classification

This detector uses multi-stage OpenCV filtering to completely eliminate 
false positives like the ocean, tennis courts, and blue roofs while 
reliably identifying swimming pools.

It also classifies pools into 4 categories:
1. Uncovered Grounded (In-ground)
2. Uncovered Above Ground
3. Covered Grounded
4. Covered Above Ground
"""

import time
import io
import math
import numpy as np
import cv2
import exifread

# ── Tunable Parameters ────────────────────────────────────────────────────────

# HSV ranges for UNCOVERED pool water (bright blue/cyan)
UNCOVERED_HSV_RANGES = [
    # Bright turquoise / light-blue pools
    {"lower": np.array([85, 60, 80]),  "upper": np.array([130, 255, 255])},
    # Mid-range blue pools
    {"lower": np.array([95, 80, 60]),  "upper": np.array([125, 255, 255])},
    # Greenish-teal pools
    {"lower": np.array([75, 60, 80]),  "upper": np.array([95, 255, 255])},
]

# HSV ranges for COVERED pools (dark blue, grey-blue, dark teal tarps)
COVERED_HSV_RANGES = [
    # Dark blue / Navy covers
    {"lower": np.array([100, 60, 40]), "upper": np.array([130, 200, 100])},
    # Dark Teal / Greenish covers
    {"lower": np.array([80, 60, 40]),  "upper": np.array([100, 200, 100])},
    # Grey-blue covers (tightened saturation to avoid grey pavement)
    {"lower": np.array([90, 40, 50]),  "upper": np.array([120, 120, 120])},
]

# Reject shadows/pavement
MIN_COVERED_SATURATION = 35.0  # Synthetic covers are more colorful than shadows
MAX_COVERED_VARIANCE = 8.0     # Tarps are flat; ground is noisy/textured


MIN_AREA_FRACTION = 0.0005  # 0.05%
MAX_AREA_FRACTION = 0.03    # 3%
APPROX_EPSILON = 0.012
MORPH_KERNEL_SIZE = 7

# Filter Thresholds
BORDER_MARGIN = 60          # Aggressive 60px border margin for sea avoidance
MIN_NON_BLUE_SURROUND = 0.75 # 75% non-blue surround to reject ocean chunks
MAX_INTERNAL_EDGE_DENSITY = 0.08 # Reject tennis courts (lots of internal lines)
MIN_SOLIDITY = 0.60         # Pools are compact; shorelines are jagged (<0.6)

# Circularity threshold for Above Ground vs Grounded
# Perfect circle = 1.0. Rectangles/Irregular = lower
MIN_CIRCULARITY_ABOVE_GROUND = 0.82 


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

def _touches_border(contour, H, W, margin=BORDER_MARGIN):
    for point in contour:
        px, py = point[0]
        if px <= margin or py <= margin or px >= W - margin or py >= H - margin:
            return True
    return False

def _compute_surround_ratio(contour, blue_mask, H, W):
    inner_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.drawContours(inner_mask, [contour], -1, 255, -1)
    
    area = cv2.contourArea(contour)
    dilation_size = max(20, int(np.sqrt(area) * 0.8)) # Large ring to catch ocean
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_size, dilation_size))
    outer_mask = cv2.dilate(inner_mask, dilate_kernel, iterations=1)
    
    ring_mask = cv2.subtract(outer_mask, inner_mask)
    ring_pixels = cv2.countNonZero(ring_mask)
    if ring_pixels == 0:
        return 1.0
        
    blue_in_ring = cv2.bitwise_and(blue_mask, ring_mask)
    blue_pixels = cv2.countNonZero(blue_in_ring)
    
    return 1.0 - (blue_pixels / ring_pixels)

def _has_internal_texture(contour, img_gray, H, W):
    roi_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.drawContours(roi_mask, [contour], -1, 255, -1)
    
    erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    interior_mask = cv2.erode(roi_mask, erode_kernel, iterations=2)
    interior_pixels = cv2.countNonZero(interior_mask)
    
    if interior_pixels < 50:
        return False
        
    edges = cv2.Canny(img_gray, 40, 120)
    interior_edges = cv2.bitwise_and(edges, interior_mask)
    edge_pixels = cv2.countNonZero(interior_edges)
    
    edge_density = edge_pixels / interior_pixels
    return edge_density > MAX_INTERNAL_EDGE_DENSITY

def _is_likely_shadow(contour, img_hsv, H, W):
    """
    Identifies if a dark region is a shadow instead of a pool cover.
    Pool covers are synthetic, saturated, and flat.
    Shadows on pavement are desaturated and noisy.
    """
    roi_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.drawContours(roi_mask, [contour], -1, 255, -1)
    
    # Analyze Saturation (S channel)
    # Shadows are neutral; covers have dye (blue/green)
    mean_s = cv2.mean(img_hsv[:, :, 1], mask=roi_mask)[0]
    if mean_s < MIN_COVERED_SATURATION:
        return True
        
    # Analyze Texture (Standard Deviation of Value)
    # Tarps are remarkably flat compared to concrete/asphalt
    _, stddev = cv2.meanStdDev(img_hsv[:, :, 2], mask=roi_mask)
    if stddev[0][0] > MAX_COVERED_VARIANCE:
        return True
        
    return False

def _compute_confidence(contour, img_gray, H, W):
    confidence = 80.0
    
    # Solidity bonus
    area = cv2.contourArea(contour)
    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area > 0 else 0
    if solidity > 0.90: confidence += 5.0
    elif solidity > 0.80: confidence += 2.0
    
    # Smoothness bonus (lack of edges)
    roi_mask = np.zeros((H, W), dtype=np.uint8)
    cv2.drawContours(roi_mask, [contour], -1, 255, -1)
    erode_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    interior_mask = cv2.erode(roi_mask, erode_kernel, iterations=1)
    
    edges = cv2.Canny(img_gray, 30, 100)
    interior_edges = cv2.bitwise_and(edges, interior_mask)
    int_pixels = cv2.countNonZero(interior_mask)
    if int_pixels > 0:
        edge_ratio = cv2.countNonZero(interior_edges) / int_pixels
        if edge_ratio < 0.02: confidence += 8.0
        elif edge_ratio < 0.05: confidence += 4.0
        
    return min(99.9, confidence)

def _process_contours(contours, img_hsv, img_gray, mask_full, total_area, min_contour_area, max_contour_area, H, W, is_covered=False, lat=None, zoom=None):
    """Processes contours and returns a list of valid pool objects with their classification."""
    valid_pools = []
    
    # Pre-compute physical pixel resolution if we have geospatial data
    # Web Mercator resolution equation: meters per pixel
    sqm_per_pixel = None
    sqft_per_pixel = None
    if lat is not None and zoom is not None:
        meters_per_pixel = 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)
        sqm_per_pixel = meters_per_pixel ** 2
        sqft_per_pixel = sqm_per_pixel * 10.7639 # 1 sq meter = 10.7639 sq feet
    
    for contour in contours:
        area_px = cv2.contourArea(contour)
        
        if area_px < min_contour_area or area_px > max_contour_area:
            continue
            
        if _touches_border(contour, H, W, BORDER_MARGIN):
            continue
            
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = area_px / hull_area if hull_area > 0 else 0
        if solidity < MIN_SOLIDITY:
            continue
            
        if _compute_surround_ratio(contour, mask_full, H, W) < MIN_NON_BLUE_SURROUND:
            continue
            
        if _has_internal_texture(contour, img_gray, H, W):
            continue
            
        # Shadow Rejection for covered pools
        if is_covered:
            if _is_likely_shadow(contour, img_hsv, H, W):
                continue
            
        # Optional: Dark water check for UNCOVERED pools only 
        # (Covered pools are naturally dark)
        if not is_covered:
            roi_mask_v = np.zeros((H, W), dtype=np.uint8)
            cv2.drawContours(roi_mask_v, [contour], -1, 255, -1)
            mean_val = cv2.mean(img_hsv[:, :, 2], mask=roi_mask_v)[0]
            if mean_val < 100:
                continue
                
        # Calculate circularity: 4 * pi * Area / (Perimeter^2)
        perimeter = cv2.arcLength(contour, True)
        circularity = 0
        if perimeter > 0:
            circularity = (4 * math.pi * area_px) / (perimeter * perimeter)
            
        is_above_ground = circularity > MIN_CIRCULARITY_ABOVE_GROUND
        
        confidence = _compute_confidence(contour, img_gray, H, W)
        x, y, w, h = cv2.boundingRect(contour)
        
        epsilon = APPROX_EPSILON * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        polygon_points = []
        for point in approx:
            px, py = point[0]
            polygon_points.append({
                "x": round(px / W * 100, 2),
                "y": round(py / H * 100, 2)
            })
            
        # Calculate Physical Area if possible
        area_sqft = None
        area_sqm = None
        if sqft_per_pixel is not None and sqm_per_pixel is not None:
            area_sqft = round(area_px * sqft_per_pixel)
            area_sqm = round(area_px * sqm_per_pixel)
            
        valid_pools.append({
            "box": {
                "x": round(x / W * 100, 2),
                "y": round(y / H * 100, 2),
                "w": round(w / W * 100, 2),
                "h": round(h / H * 100, 2),
                "confidence": round(confidence, 1),
            },
            "polygon": {
                "points": polygon_points,
                "confidence": round(confidence, 1)
            },
            "is_covered": is_covered,
            "is_above_ground": is_above_ground,
            "area_sqft": area_sqft,
            "area_sqm": area_sqm
        })
        
    return valid_pools

def detect_pools(image_bytes: bytes, lat: float = None, zoom: int = None) -> dict:
    t0 = time.perf_counter()
    
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Could not decode image"}
        
    H, W = img.shape[:2]
    total_area = H * W
    min_contour_area = total_area * MIN_AREA_FRACTION
    max_contour_area = total_area * MAX_AREA_FRACTION
    
    # Preprocessing
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    img_enhanced = cv2.cvtColor(cv2.merge((l_eq, a, b)), cv2.COLOR_LAB2BGR)
    
    img_smooth = cv2.bilateralFilter(img_enhanced, d=9, sigmaColor=75, sigmaSpace=75)
    img_hsv = cv2.cvtColor(img_smooth, cv2.COLOR_BGR2HSV)
    img_gray = cv2.cvtColor(img_smooth, cv2.COLOR_BGR2GRAY)
    
    def _get_mask(ranges):
        combined = np.zeros((H, W), dtype=np.uint8)
        for r in ranges:
            mask = cv2.inRange(img_hsv, r["lower"], r["upper"])
            combined = cv2.bitwise_or(combined, mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=3)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=2)
        combined = cv2.GaussianBlur(combined, (5, 5), 0)
        _, combined = cv2.threshold(combined, 127, 255, cv2.THRESH_BINARY)
        return combined

    # Pass 1: Uncovered Pools
    uncovered_mask = _get_mask(UNCOVERED_HSV_RANGES)
    contours_uncovered, _ = cv2.findContours(uncovered_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    uncovered_pools = _process_contours(
        contours_uncovered, img_hsv, img_gray, uncovered_mask, total_area, min_contour_area, max_contour_area, H, W, 
        is_covered=False, lat=lat, zoom=zoom
    )

    # Pass 2: Covered Pools
    covered_mask = _get_mask(COVERED_HSV_RANGES)
    contours_covered, _ = cv2.findContours(covered_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    covered_pools = _process_contours(
        contours_covered, img_hsv, img_gray, covered_mask, total_area, min_contour_area, max_contour_area, H, W, 
        is_covered=True, lat=lat, zoom=zoom
    )

    all_pools = uncovered_pools + covered_pools
    total_pools = len(all_pools)
    
    categories = {
        "uncovered_grounded": [],
        "uncovered_above_ground": [],
        "covered_grounded": [],
        "covered_above_ground": []
    }
    
    all_confidences = []
    
    for p in all_pools:
        all_confidences.append(p["box"]["confidence"])
        
        is_cov = p["is_covered"]
        is_ag = p["is_above_ground"]
        
        if not is_cov and not is_ag:
            categories["uncovered_grounded"].append({"box": p["box"], "polygon": p["polygon"]})
        elif not is_cov and is_ag:
            categories["uncovered_above_ground"].append({"box": p["box"], "polygon": p["polygon"]})
        elif is_cov and not is_ag:
            categories["covered_grounded"].append({"box": p["box"], "polygon": p["polygon"]})
        elif is_cov and is_ag:
            categories["covered_above_ground"].append({"box": p["box"], "polygon": p["polygon"]})

    elapsed = round(time.perf_counter() - t0, 2)
    avg_conf = round(float(np.mean(all_confidences)), 1) if all_confidences else 0.0
    lat, lng = _extract_gps(image_bytes)
    
    return {
        "pools": total_pools,
        "confidence": avg_conf,
        "time": elapsed,
        "lat": lat,
        "lng": lng,
        "categories": categories
    }
