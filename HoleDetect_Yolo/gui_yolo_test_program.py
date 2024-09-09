import sys
import numpy as np
import torch
from torchvision import transforms
from PIL import Image
import cv2
from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog, QMessageBox
from PySide2.QtGui import QPixmap, QImage

# 모델 로드
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = torch.hub.load('../yolov5', 'custom', path='model/best.pt', source='local').to(device)


def preprocess_image(image_path):
    image = Image.open(image_path)
    transform = transforms.Compose([
        transforms.Resize((640, 640)),
        transforms.ToTensor()
    ])
    return transform(image).unsqueeze(0).to(device), image.size


def infer_image(image_path):
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
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YOLOv5 Object Detection')
        layout = QVBoxLayout()

        self.image_label = QLabel('No image selected.')
        layout.addWidget(self.image_label)

        self.btn_select = QPushButton('Select Image')
        self.btn_select.clicked.connect(self.load_image)
        layout.addWidget(self.btn_select)

        self.setLayout(layout)
        self.resize(800, 600)

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open Image', '.', 'Image Files (*.png *.jpg *.jpeg)')
        if file_name:
            image, label_text = infer_image(file_name)
            if image is None:
                QMessageBox.information(self, 'Detection Result', label_text)
            else:
                height, width, channels = image.shape
                bytes_per_line = channels * width
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                pixmap = QPixmap.fromImage(q_image)
                self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), aspectRatioMode=1))
                self.image_label.setText(label_text)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
