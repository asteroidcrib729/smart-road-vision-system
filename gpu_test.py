import torch
from ultralytics import YOLO

print("--- FYP System Check ---")

# 1. Check PyTorch & CUDA Bridge
print(f"PyTorch Version: {torch.__version__}")
cuda_available = torch.cuda.is_available()
print(f"CUDA Available: {cuda_available}")

if cuda_available:
    print(f"GPU Detected: {torch.cuda.get_device_name(0)}")
    print(f"Allocated Memory: {torch.cuda.memory_allocated(0)} bytes")
else:
    print("WARNING: CUDA is NOT available. Falling back to CPU.")

# 2. Check Ultralytics Integration
try:
    print("\nInitializing YOLO...")
    # This just loads the architecture to ensure the library works
    model = YOLO("yolov8n.yaml")
    print("YOLO initialization successful!")
except Exception as e:
    print(f"YOLO Error: {e}")

print("------------------------")