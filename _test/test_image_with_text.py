import sys
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt


class ImageLabelWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Image with Text Overlay")
        self.setGeometry(100, 100, 600, 400)
        self.layout = QVBoxLayout(self)

        # QLabel 설정
        self.label = QLabel(self)
        self.layout.addWidget(self.label)
        self.showImageWithText("D:/Project/2024/BIW (미국 HMGMA)/git/BIW-US-/data/hand_color.jpg", "QR Code Result: OK", position="top-right")

    def showImageWithText(self, image_path, text, position="top-right"):
        original_pixmap = QPixmap(image_path)
        scaled_pixmap = original_pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # 이미지 크기 조정

        # QPainter를 사용하여 이미지 위에 텍스트 그리기
        painter = QPainter(scaled_pixmap)
        painter.setPen(QColor(255, 255, 255))  # 텍스트 색상
        painter.setFont(QFont("현대하모니 L", 30))  # 텍스트 폰트

        # 위치에 따른 텍스트 위치 설정
        if position == "top-right":
            text_rect = scaled_pixmap.rect().adjusted(scaled_pixmap.width() - 200, 10, -10, -10)
        elif position == "bottom-right":
            text_rect = scaled_pixmap.rect().adjusted(scaled_pixmap.width() - 200, scaled_pixmap.height() - 30, -10, -10)

        # 텍스트 그리기
        painter.drawText(text_rect, Qt.AlignRight, text)
        painter.end()

        # QLabel에 완성된 QPixmap 설정
        self.label.setPixmap(scaled_pixmap)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ImageLabelWidget()
    ex.show()
    sys.exit(app.exec_())
