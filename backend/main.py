"""
PoolDetect AI – FastAPI backend
Run with:  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import math

from detector import detect_pools

# --- Helper: Intersection Over Union (IoU) ---
def calculate_iou(box1, box2):
    """Calculate Intersection over Union for two boxes: {x, y, w, h}"""
    # Determine coordinates of the intersection rectangle
    x_left = max(box1["x"], box2["x"])
    y_top = max(box1["y"], box2["y"])
    x_right = min(box1["x"] + box1["w"], box2["x"] + box2["w"])
    y_bottom = min(box1["y"] + box1["h"], box2["y"] + box2["h"])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection area
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # The area of both rectangles
    box1_area = box1["w"] * box1["h"]
    box2_area = box2["w"] * box2["h"]

    # Compute IoU
    iou = intersection_area / float(box1_area + box2_area - intersection_area)
    return iou

app = FastAPI(title="PoolDetect AI", version="1.0.0")

# Allow the Vite dev-server (any localhost origin) to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "PoolDetect AI"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    Upload an aerial image (JPEG / PNG / TIFF / WebP).
    Returns JSON: { pools, confidence, time, boxes[] }
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file received.")

    result = detect_pools(image_bytes)

    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result

class LocationRequest(BaseModel):
    lat: float
    lon: float

@app.post("/detect-location")
def detect_location(req: LocationRequest):
    """
    Fetch a satellite imagery tile from Esri World Imagery (free, no API key) 
    by converting lat/lon to Web Mercator Slippy Map tilenames.
    """
    zoom = 18
    lat_rad = math.radians(req.lat)
    n = 2.0 ** zoom
    xtile = int((req.lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)

    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{ytile}/{xtile}"
    
    headers = {
        "User-Agent": "PoolDetectAI/1.0"
    }
    
    resp = requests.get(url, headers=headers, timeout=10)
    
    if resp.status_code != 200:
        raise HTTPException(
            status_code=400, 
            detail=f"Esri Tile API failed: {resp.status_code}"
        )
        
    image_bytes = resp.content
    result = detect_pools(image_bytes, lat=req.lat, zoom=zoom)
    
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
        
    return result

@app.post("/detect-change")
async def detect_change(image_before: UploadFile = File(...), image_after: UploadFile = File(...)):
    """
    Compare two aerial images to find NEW pool construction.
    Returns: { new_pools: [...], existing_pools: [...], removed_pools: [...] }
    """
    # Read both images
    before_bytes = await image_before.read()
    after_bytes = await image_after.read()
    
    if len(before_bytes) == 0 or len(after_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty files received.")

    # Detect pools in both
    res_before = detect_pools(before_bytes)
    res_after = detect_pools(after_bytes)

    if "error" in res_before or "error" in res_after:
        raise HTTPException(status_code=422, detail="Error processing one or both images.")

    # Flatten all categories into a single list for easier comparison
    before_pools = []
    for cat in res_before.get("categories", {}).values():
        before_pools.extend(cat)
        
    after_pools = []
    for cat in res_after.get("categories", {}).values():
        after_pools.extend(cat)

    new_pools = []
    existing_pools = []
    
    # Track which 'before' pools were matched
    matched_before_indices = set()

    # Compare every pool in AFTER against every pool in BEFORE
    for after_pool in after_pools:
        is_new = True
        best_iou = 0
        
        for i, before_pool in enumerate(before_pools):
            iou = calculate_iou(after_pool["box"], before_pool["box"])
            if iou > best_iou:
                best_iou = iou
            
            # If overlap > 10% (accounting for slight alignment shifts in satellites)
            if iou > 0.1:
                is_new = False
                matched_before_indices.add(i)
                
        if is_new:
            new_pools.append(after_pool)
        else:
            existing_pools.append(after_pool)

    removed_pools = [before_pools[i] for i in range(len(before_pools)) if i not in matched_before_indices]

    return {
        "status": "success",
        "comparisons": {
            "new_built": len(new_pools),
            "existing": len(existing_pools),
            "removed_or_filled": len(removed_pools)
        },
        "new_pools": new_pools,
        "existing_pools": existing_pools,
        "removed_pools": removed_pools
    }
