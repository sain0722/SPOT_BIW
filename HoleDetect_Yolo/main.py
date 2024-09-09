# YOLOv5 PyTorch HUB Inference (DetectionModels only)
import torch

model = torch.hub.load('../yolov5', 'custom', 'model/yolov5s.pt', source='local')  # yolov5n - yolov5x6 or custom
im = './img.png'  # file, Path, PIL.Image, OpenCV, nparray, list
results = model(im)  # inference
results.print()  # or .show(), .save(), .crop(), .pandas(), etc.
