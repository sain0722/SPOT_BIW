import sys
import cv2
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from dbr import BarcodeReader, BarcodeReaderError

# Dynamsoft Barcode Reader 초기화
license_key = "t0068lQAAACyybRzwX/fWYv5ABAfjzu56G5uq/HwTZuHWbUzOfsc+zVg1dA67r40/kCmljMJ3nVTFYRPabVkKBR9yPOYuTA8=;t0068lQAAAKJx66lA4swh5KRaKzlaCfNCdo6rDJg6bs4a7oLGBFAOA5z0VDAMhJSSpkKgrduwxonnIjZWDQmChZt6CCCURog="  # Dynamsoft에서 발급받은 라이선스 키를 사용합니다.
reader = BarcodeReader()
reader.init_license(license_key)


class BarcodeScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Matrix Scanner")
        self.setGeometry(100, 100, 800, 600)

        self.image = None
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

        self.button_scan_image = QPushButton("Scan Image")
        self.button_scan_image.clicked.connect(self.scan_image)
        self.layout.addWidget(self.button_scan_image)

        self.result_label = QLabel("Result: ")
        self.layout.addWidget(self.result_label)

        self.central_widget.setLayout(self.layout)

    def load_image(self):
        file_dialog = QFileDialog()
        path, _ = file_dialog.getOpenFileName(self, "Load Image", "", "Images (*.png *.jpg *.bmp)")
        if path:
            self.image = cv2.imread(path)
            self.image_path = path
            self.display_image(self.image)

    def display_image(self, image):
        height, width, channel = image.shape
        bytes_per_line = 3 * width
        q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        pixmap = QPixmap.fromImage(q_image)

        self.image_label.setPixmap(pixmap)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignCenter)

    def scan_image(self):
        if self.image is None:
            self.result_label.setText("Result: No Image Loaded")
            return

        try:
            # image_path = "temp_image.png"
            # cv2.imwrite(image_path, self.image)
            results = reader.decode_file(self.image_path)
            if results:
                result_texts = [f"Format: {result.barcode_format_string}, Text: {result.barcode_text}" for result in
                                results]
                self.result_label.setText("Result:\n" + "\n".join(result_texts))
            else:
                self.result_label.setText("Result: No barcode found.")
        except BarcodeReaderError as bre:
            self.result_label.setText(f"Barcode reader error: {bre}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BarcodeScannerApp()
    window.show()
    sys.exit(app.exec_())
