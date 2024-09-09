import sys
import numpy as np
import cv2
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsSimpleTextItem, QMenu
from PySide6.QtGui import QPixmap, QImage, QFont, QColor, QBrush, QWheelEvent, QContextMenuEvent, QPainter, QAction
from PySide6.QtCore import Qt


class CustomGraphicView(QGraphicsView):
    def __init__(self):
        super().__init__()

        # QGraphicsScene 생성
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 윈도우 설정
        self.setWindowTitle('Image with Text Overlay')
        # self.setFixedSize(960, 840)
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        # self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # 드래그 모드 설정

        # 기본 텍스트 항목들
        self.title_item = None
        self.label_items = []
        self.value_items = []

    def convert_image_to_pixmap(self, image_input):
        """이미지 입력을 QPixmap으로 변환"""
        if isinstance(image_input, np.ndarray):
            # np.ndarray (OpenCV 이미지)일 경우
            image_input = np.ascontiguousarray(image_input, dtype=np.uint8)
            height, width, channels = image_input.shape
            bytes_per_line = channels * width
            qimage = QImage(image_input.data, width, height, bytes_per_line, QImage.Format_RGB888)
            return QPixmap.fromImage(qimage.rgbSwapped())
        elif isinstance(image_input, QImage):
            return QPixmap.fromImage(image_input)
        elif isinstance(image_input, QPixmap):
            return image_input
        else:
            raise ValueError("Unsupported image type")

    def set_image(self, image_input):
        """이미지를 설정하고 QGraphicsPixmapItem으로 추가"""
        pixmap = self.convert_image_to_pixmap(image_input)
        # scaled_pixmap = pixmap.scaled(960, 840, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        # 이미지 아이템 생성 및 추가
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.fit_in_view()

    def set_text_list(self, title, labels, values):
        """텍스트 데이터를 설정하고 씬에 추가"""
        # 기존 텍스트 항목 제거
        if self.title_item:
            self.scene.removeItem(self.title_item)
        for item in self.label_items:
            self.scene.removeItem(item)
        for item in self.value_items:
            self.scene.removeItem(item)

        self.label_items.clear()
        self.value_items.clear()

        # 텍스트 폭 설정
        text_width = 680
        text_height = 680

        # 배경 사각형 생성 및 추가
        background_rect = QGraphicsRectItem(10, 10, text_width + 20, text_height + 20)
        background_rect.setBrush(QBrush(QColor(0, 100, 0, 128)))  # 약간 초록색 느낌의 반투명 배경
        background_rect.setPen(Qt.NoPen)
        self.scene.addItem(background_rect)

        # 가장 긴 label의 길이를 구함
        max_label_length = max(len(label) for label in labels)

        # 타이틀 추가
        self.title_item = QGraphicsSimpleTextItem(title)
        self.title_item.setBrush(QBrush(QColor("cyan")))
        self.title_item.setFont(QFont('Consolas', 28, QFont.Bold))
        self.title_item.setPos(20, 20)
        self.scene.addItem(self.title_item)

        # 각 항목 추가
        y_offset = 80
        label_color = QColor("black")
        value_color = QColor("white")
        for label, value in zip(labels, values):
            label_item_text = label.center(max_label_length) + " :"
            label_item = QGraphicsSimpleTextItem(label_item_text)
            label_item.setBrush(QBrush(label_color))
            label_item.setFont(QFont('Consolas', 24))
            label_item.setPos(40, y_offset)
            self.scene.addItem(label_item)
            self.label_items.append(label_item)

            value_item = QGraphicsSimpleTextItem(value)
            value_item.setBrush(QBrush(value_color))
            value_item.setFont(QFont('Consolas', 24))
            value_item.setPos(400, y_offset)
            self.scene.addItem(value_item)
            self.value_items.append(value_item)

            y_offset += 40

    def set_text(self, title, text):
        """텍스트 데이터를 설정하고 씬에 추가"""
        # 기존 텍스트 항목 제거
        if self.title_item:
            self.scene.removeItem(self.title_item)
        for item in self.label_items:
            self.scene.removeItem(item)
        for item in self.value_items:
            self.scene.removeItem(item)

        self.label_items.clear()
        self.value_items.clear()

        # 텍스트 폭 설정
        text_width  = 300 * 4
        text_height = 150 * 4

        # 배경 사각형 생성 및 추가
        background_rect = QGraphicsRectItem(10, 10, text_width + 20, text_height + 20)
        background_rect.setBrush(QBrush(QColor(0, 100, 0, 128)))  # 약간 초록색 느낌의 반투명 배경
        background_rect.setPen(Qt.NoPen)
        self.scene.addItem(background_rect)

        # 타이틀 추가
        title_font = QFont('Consolas', 14*3, QFont.Bold)
        self.title_item = QGraphicsSimpleTextItem(title)
        self.title_item.setBrush(QBrush(QColor("cyan")))
        self.title_item.setFont(title_font)
        self.title_item.setPos(20, 20)
        self.scene.addItem(self.title_item)

        y_offset = 60 * 4

        label_item_font = QFont('Consolas', 12*3)

        label_item = QGraphicsSimpleTextItem(text)
        label_item.setBrush(QBrush(QColor("black")))
        label_item.setFont(label_item_font)
        label_item.setPos(20, y_offset)
        self.scene.addItem(label_item)
        self.label_items.append(label_item)

    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠 이벤트 처리 (확대/축소)"""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """우클릭 메뉴 이벤트 처리"""
        context_menu = QMenu(self)
        fit_in_view_action = QAction("Fit in View", self)
        fit_in_view_action.triggered.connect(self.fit_in_view)

        test_action = QAction("(Test) 이미지 등록", self)
        test_action.triggered.connect(self.test_set_image)  # 이미지 저장 기능에 연결

        context_menu.addAction(fit_in_view_action)
        context_menu.addAction(test_action)

        context_menu.exec_(event.globalPos())

    def fit_in_view(self):
        """'Fit in View' 기능 구현"""
        self.fitInView(self.scene.itemsBoundingRect(), Qt.IgnoreAspectRatio)

    def test_set_image(self):
        # 예제 이미지 (OpenCV 사용)
        image_path = 'data/hand_color.jpg'
        image_cv = cv2.imread(image_path)

        # 예제 텍스트 데이터
        title = "QR CODE INFORMATION"
        labels = [
            "MODEL",
            "DOOR",
            "DRIVE",
            "REGION",
            "TRANSMISSION",
            "ROOF",
            "MATERIAL",
            "ENGINE",
            "WHEEL TYPE",
            "PASSENGER",
            "BATTERY",
            "ROOFRACK",
            "Power Tail Gate",
            "Sliding Console",
            "Woofer Speaker"
        ]
        values = [
            "N3",
            "4DR",
            "LHD",
            "USA",
            "AT",
            "G/ROOF",
            "CR",
            "EV",
            "2WD",
            "5_PASSENGER",
            "LONG RANGE",
            "NONE ROOF RACK",
            "General Tail Gate",
            "General Console",
            "General"
        ]

        self.set_image(image_cv)
        self.set_text_list(title, labels, values)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 예제 이미지 (OpenCV 사용)
    image_path = '../../data/hand_color.jpg'
    image_cv = cv2.imread(image_path)

    # 예제 텍스트 데이터
    title = "QR CODE INFORMATION"
    labels = [
        "MODEL",
        "DOOR",
        "DRIVE",
        "REGION",
        "TRANSMISSION",
        "ROOF",
        "MATERIAL",
        "ENGINE",
        "WHEEL TYPE",
        "PASSENGER",
        "BATTERY",
        "ROOFRACK",
        "Power Tail Gate",
        "Sliding Console",
        "Woofer Speaker"
    ]
    values = [
        "N3",
        "4DR",
        "LHD",
        "USA",
        "AT",
        "G/ROOF",
        "CR",
        "EV",
        "2WD",
        "5_PASSENGER",
        "LONG RANGE",
        "NONE ROOF RACK",
        "General Tail Gate",
        "General Console",
        "General"
    ]

    widget = CustomGraphicView()
    widget.set_image(image_cv)
    widget.set_text_list(title, labels, values)
    widget.show()
    sys.exit(app.exec_())
