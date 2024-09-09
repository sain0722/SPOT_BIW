import cv2
import torch
from PySide6.QtCore import QThread, QObject, Signal
from PIL import Image
from torchvision import transforms
import numpy as np

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class ModelLoaderThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, model_path):
        super().__init__()
        self.model_path = model_path

    def run(self):
        try:
            print("run model load")
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            model = torch.hub.load('./yolov5', 'custom', path=self.model_path, source='local').to(device)
            self.completed.emit(model)
            print("model load complete.")
        except Exception as e:
            self.failed.emit(str(e))

class ModelManager(QObject):
    model_loaded = Signal(object)
    model_load_failed = Signal(str)

    def __init__(self, initial_model_path):
        super().__init__()
        self.model_path = initial_model_path
        self.model = None

    def load_model(self):
        self.loader_thread = ModelLoaderThread(self.model_path)
        self.loader_thread.completed.connect(self.on_model_loaded)
        self.loader_thread.failed.connect(self.on_model_load_failed)
        self.loader_thread.start()

    def on_model_loaded(self, model):
        self.model = model
        self.model_loaded.emit(model)

    def on_model_load_failed(self, error_message):
        self.model_load_failed.emit(error_message)

    def get_model(self):
        return self.model

    def change_model_path(self, new_path):
        self.model_path = new_path
        self.load_model()

def preprocess_image(image_path):
    image = Image.open(image_path)
    transform = transforms.Compose([
        transforms.Resize((640, 640)),
        transforms.ToTensor()
    ])
    return transform(image).unsqueeze(0).to(device), image.size


def infer_image(image_path, model):
    image_tensor, original_size = preprocess_image(image_path)
    try:
        results = model(image_tensor)
    except Exception as e:
        print(f"YoloManager.py - infer_image: {e}")
        return None, str(e)
    results = results[0].cpu().numpy()

    if results.shape[0] == 0:
        return None, "No detections."

    best_result = results[np.argmax(results[:, 4])]
    orig_w, orig_h = original_size
    scale_x, scale_y = orig_w / 640, orig_h / 640

    x1 = int((best_result[0] - best_result[2] / 2) * scale_x)
    y1 = int((best_result[1] - best_result[3] / 2) * scale_y)
    x2 = int((best_result[0] + best_result[2] / 2) * scale_x)
    y2 = int((best_result[1] + best_result[3] / 2) * scale_y)

    image = cv2.imread(image_path)
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    label_text = f'Class: {int(best_result[5])}, Score: {best_result[4]:.2f}'
    cv2.putText(image, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return image, label_text
