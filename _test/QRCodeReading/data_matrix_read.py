import sys
import cv2
import numpy as np
import time
from pyzbar.pyzbar import decode
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, \
    QComboBox, QHBoxLayout, QSlider, QFormLayout, QCheckBox
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt


class DataMatrixTester(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Data Matrix Reader Test Program")
        self.setGeometry(100, 100, 1000, 800)

        self.image = None
        self.processed_image = None

        self.initUI()

    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()

        self.image_label = QLabel("No Image Loaded")
        self.layout.addWidget(self.image_label)

        self.button_load_image = QPushButton("Load Image")
        self.button_load_image.clicked.connect(self.load_image)
        self.layout.addWidget(self.button_load_image)

        self.checkbox_layout = QHBoxLayout()
        self.threshold_checkbox = QCheckBox("Threshold")
        self.threshold_checkbox.stateChanged.connect(self.toggle_threshold_slider)
        self.grayscale_checkbox = QCheckBox("Grayscale")
        self.grayscale_checkbox.stateChanged.connect(self.update_image)
        self.blur_checkbox = QCheckBox("Blur")
        self.blur_checkbox.stateChanged.connect(self.toggle_blur_slider)
        self.edges_checkbox = QCheckBox("Edge Detection")
        self.edges_checkbox.stateChanged.connect(self.toggle_edges_slider)
        self.equalize_checkbox = QCheckBox("Equalize Histogram")
        self.equalize_checkbox.stateChanged.connect(self.update_image)
        self.invert_checkbox = QCheckBox("Invert Colors")
        self.invert_checkbox.stateChanged.connect(self.update_image)
        self.flip_checkbox = QCheckBox("Flip Horizontally")
        self.flip_checkbox.stateChanged.connect(self.update_image)

        self.checkbox_layout.addWidget(self.threshold_checkbox)
        self.checkbox_layout.addWidget(self.grayscale_checkbox)
        self.checkbox_layout.addWidget(self.blur_checkbox)
        self.checkbox_layout.addWidget(self.edges_checkbox)
        self.checkbox_layout.addWidget(self.equalize_checkbox)
        self.checkbox_layout.addWidget(self.invert_checkbox)
        self.checkbox_layout.addWidget(self.flip_checkbox)
        self.layout.addLayout(self.checkbox_layout)

        self.form_layout = QFormLayout()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.valueChanged.connect(self.update_image)
        self.form_layout.addRow("Threshold Value", self.threshold_slider)
        self.threshold_slider.hide()

        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setMinimum(1)
        self.blur_slider.setMaximum(31)
        self.blur_slider.setValue(5)
        self.blur_slider.valueChanged.connect(self.update_image)
        self.form_layout.addRow("Blur Kernel Size", self.blur_slider)
        self.blur_slider.hide()

        self.edges_slider = QSlider(Qt.Horizontal)
        self.edges_slider.setMinimum(0)
        self.edges_slider.setMaximum(255)
        self.edges_slider.setValue(100)
        self.edges_slider.valueChanged.connect(self.update_image)
        self.form_layout.addRow("Canny Edge Threshold", self.edges_slider)
        self.edges_slider.hide()

        self.layout.addLayout(self.form_layout)

        self.button_apply_preprocessing = QPushButton("Apply Preprocessing")
        self.button_apply_preprocessing.clicked.connect(self.apply_preprocessing)
        self.layout.addWidget(self.button_apply_preprocessing)

        self.button_read_datamatrix = QPushButton("Read Data Matrix")
        self.button_read_datamatrix.clicked.connect(self.read_datamatrix)
        self.layout.addWidget(self.button_read_datamatrix)

        self.result_label = QLabel("Result: ")
        self.layout.addWidget(self.result_label)

        self.central_widget.setLayout(self.layout)

    def toggle_threshold_slider(self):
        self.threshold_slider.setVisible(self.threshold_checkbox.isChecked())
        self.update_image()

    def toggle_blur_slider(self):
        self.blur_slider.setVisible(self.blur_checkbox.isChecked())
        self.update_image()

    def toggle_edges_slider(self):
        self.edges_slider.setVisible(self.edges_checkbox.isChecked())
        self.update_image()

    def load_image(self):
        file_dialog = QFileDialog()
        path, _ = file_dialog.getOpenFileName(self, "Load Image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.image = cv2.imread(path)
            self.display_image(self.image)

    def display_image(self, image):
        height, width = image.shape[:2]
        max_height = 600
        max_width = 800

        if height > max_height or width > max_width:
            scaling_factor = min(max_width / width, max_height / height)
            image = cv2.resize(image, (int(width * scaling_factor), int(height * scaling_factor)),
                               interpolation=cv2.INTER_AREA)

        qformat = QImage.Format_Indexed8 if len(image.shape) == 2 else QImage.Format_RGB888
        if len(image.shape) == 3 and image.shape[2] == 4:
            qformat = QImage.Format_RGBA8888
        out_image = QImage(image, image.shape[1], image.shape[0], image.strides[0], qformat)
        out_image = out_image.rgbSwapped()
        self.image_label.setPixmap(QPixmap.fromImage(out_image))
        self.image_label.setAlignment(Qt.AlignCenter)

    def update_image(self):
        if self.image is None:
            return

        self.processed_image = self.image.copy()

        if self.grayscale_checkbox.isChecked():
            self.processed_image = cv2.cvtColor(self.processed_image, cv2.COLOR_BGR2GRAY)
        if self.threshold_checkbox.isChecked():
            _, self.processed_image = cv2.threshold(self.processed_image, self.threshold_slider.value(), 255,
                                                    cv2.THRESH_BINARY)
        if self.blur_checkbox.isChecked():
            blur_value = self.blur_slider.value()
            if blur_value % 2 == 0:  # Ensure the blur kernel size is odd
                blur_value += 1
            self.processed_image = cv2.GaussianBlur(self.processed_image, (blur_value, blur_value), 0)
        if self.edges_checkbox.isChecked():
            self.processed_image = cv2.Canny(self.processed_image, self.edges_slider.value(), 200)
        if self.equalize_checkbox.isChecked():
            if len(self.processed_image.shape) == 2:
                self.processed_image = cv2.equalizeHist(self.processed_image)
            else:
                ycrcb = cv2.cvtColor(self.processed_image, cv2.COLOR_BGR2YCrCb)
                ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
                self.processed_image = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        if self.invert_checkbox.isChecked():
            self.processed_image = cv2.bitwise_not(self.processed_image)
        if self.flip_checkbox.isChecked():
            self.processed_image = cv2.flip(self.processed_image, 1)

        self.display_image(self.processed_image)

    def apply_preprocessing(self):
        self.update_image()

    def read_datamatrix(self):
        if self.processed_image is None:
            self.result_label.setText("Result: No Processed Image")
            return

        from pylibdmtx.pylibdmtx import decode
        from PIL import Image

        # Data Matrix 코드 디코딩
        start_time = time.time()
        decoded_objects = decode(self.processed_image)
        end_time = time.time()

        # 디코딩 결과 출력
        for obj in decoded_objects:
            print("Decoded Data:", obj.data.decode('utf-8'))
            print("Rect:", obj.rect)

        datamatrix_results = [result.data.decode('utf-8') for result in decoded_objects]
        datamatrix_time = end_time - start_time

        # start_time = time.time()
        # results = decode(self.processed_image)
        # end_time = time.time()
        #
        # datamatrix_results = [result.data.decode('utf-8') for result in results]
        # datamatrix_time = end_time - start_time

        self.result_label.setText(f"Result: {datamatrix_results}\nTime: {datamatrix_time:.4f} seconds")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DataMatrixTester()
    window.show()
    sys.exit(app.exec_())
