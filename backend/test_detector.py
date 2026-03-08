import cv2
import numpy as np
from detector import detect_pools

# Create a small dummy blue image
dummy = np.zeros((640, 640, 3), dtype=np.uint8)
dummy[:, :] = (255, 0, 0) # Blue backtound
cv2.rectangle(dummy, (200, 200), (300, 300), (200, 255, 200), -1)

# Encode to bytes
is_success, buffer = cv2.imencode(".jpg", dummy)
if not is_success:
    print("Failed to encode dummy image")
    exit(1)
    
img_bytes = buffer.tobytes()

print("Testing detect_pools on dummy image...")
result = detect_pools(img_bytes)

print("\n--- Detection Result ---")
for k, v in result.items():
    if k == "categories":
        print("Categories:")
        for cat_k, cat_v in v.items():
            print(f"  {cat_k}: {len(cat_v)} pools")
    else:
        print(f"{k}: {v}")

print("\nTest Complete!")
