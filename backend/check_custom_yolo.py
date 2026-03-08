import os
from ultralytics import YOLO

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "..", "YOLOV11M WEIGHTS", "best.pt")
    print(f"Loading custom model from: {model_path}")
    
    try:
        model = YOLO(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return
        
    print(f"\nCustom model loaded successfully!")
    print("\nClasses in the custom model:")
    for id, name in dict(model.names).items():
        print(f"Class {id}: {name}")

if __name__ == "__main__":
    main()
