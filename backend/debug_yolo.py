import cv2
import numpy as np
from detector import detect_pools

def main():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Ultralytics not installed. Please run: pip install ultralytics")
        return
        
    model = YOLO("yolo11m.pt")
    
    # Let's check what classes YOLO11m *actually* has
    print("Default COCO Classes in yolo11m.pt:")
    for i in range(10): # just print the first 10
        print(f"Class {i}: {model.names.get(i, 'unknown')}")
        
    # Is there a pool class?
    pool_classes = [name for id, name in model.names.items() if 'pool' in name.lower()]
    print(f"\nPool classes explicitly in model: {pool_classes}")

if __name__ == "__main__":
    main()
