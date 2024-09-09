import sys
import numpy as np
import torch
from PySide6.QtGui import QImage, QPixmap, QPainter, QContextMenuEvent, QAction
from torchvision import transforms
from PIL import Image
import cv2
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFileDialog, \
    QMessageBox, QLineEdit, QDialog, QProgressBar, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu
from PySide6.QtCore import QObject, QThread, Signal, Qt

from ImageViewer import ImageViewer

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
            model = torch.hub.load('../yolov5', 'custom', path=self.model_path, source='local').to(device)
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
    results = model(image_tensor)
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


class MainWindow(QWidget):
    def __init__(self, model_manager):
        super().__init__()
        self.model_manager = model_manager
        self.loading_dialog = None
        self.initUI()
        self.connect_signals()
        self.btn_select.setEnabled(False)  # 초기에 버튼 비활성화

    def connect_signals(self):
        self.model_manager.model_loaded.connect(self.on_model_loaded)
        self.model_manager.model_load_failed.connect(self.on_model_load_failed)

    def initUI(self):
        self.setWindowTitle('YOLOv5 Object Detection')
        layout = QVBoxLayout()

        self.viewer = ImageViewer()
        layout.addWidget(self.viewer)

        self.btn_select = QPushButton('Select Image')
        self.btn_select.clicked.connect(self.load_image)
        layout.addWidget(self.btn_select)

        model_layout = QHBoxLayout()
        self.model_path_input = QLineEdit(self.model_manager.model_path)
        self.model_path_input.setReadOnly(True)
        model_layout.addWidget(self.model_path_input)

        self.btn_change_model = QPushButton('Change Model Path')
        self.btn_change_model.clicked.connect(self.change_model_path)
        model_layout.addWidget(self.btn_change_model)

        layout.addLayout(model_layout)
        self.setLayout(layout)
        self.resize(800, 600)

    def on_model_loaded(self):
        if self.loading_dialog:
            self.loading_dialog.accept()
        QMessageBox.information(self, 'Model Loaded', 'The model has been loaded successfully!')
        self.btn_select.setEnabled(True)  # 모델 로드 완료 시 버튼 활성화

    def on_model_load_failed(self, error_message):
        if self.loading_dialog:
            self.loading_dialog.reject()
        QMessageBox.critical(self, 'Model Load Error', error_message)
        self.btn_select.setEnabled(False)  # 모델 로드 실패 시 버튼 다시 비활성화

    def change_model_path(self):
        new_path, _ = QFileDialog.getOpenFileName(self, 'Select Model', '.', 'Model Files (*.pt)')
        if new_path:
            self.model_path_input.setText(new_path)
            self.model_manager.change_model_path(new_path)
            # self.loading_dialog = LoadingDialog("Loading model from " + new_path, self)
            # self.loading_dialog.show()

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open Image', '', 'Image Files (*.png *.jpg *.jpeg)')
        if file_name:
            image, label_text = infer_image(file_name, self.model_manager.get_model())
            if image is None:
                QMessageBox.information(self, 'Detection Result', 'No detections found.')
            else:
                height, width, channels = image.shape
                bytes_per_line = channels * width
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                pixmap = QPixmap.fromImage(q_image)
                self.viewer.set_image(pixmap)

                # pixmap = QPixmap.fromImage(q_image)
                # self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio))

                # self.image_label.setText(label_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    model_manager = ModelManager('model/best.pt')

    main_window = MainWindow(model_manager)
    main_window.show()
    sys.exit(app.exec())
