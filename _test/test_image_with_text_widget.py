# import sys
# from PySide2.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem, \
#     QGraphicsRectItem
# from PySide2.QtGui import QPixmap, QFont, QColor, QBrush
# from PySide2.QtCore import Qt
#
# class ImageWithTextWidget(QGraphicsView):
#     def __init__(self, image_path):
#         super().__init__()
#
#         # QGraphicsScene 생성
#         self.scene = QGraphicsScene(self)
#         self.setScene(self.scene)
#
#         # 이미지 로드 및 리사이즈
#         pixmap = QPixmap(image_path)
#         scale = 4
#         scaled_pixmap = pixmap.scaled(pixmap.size() / scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
#
#         # 이미지 아이템 생성 및 추가
#         self.image_item = QGraphicsPixmapItem(scaled_pixmap)
#         self.scene.addItem(self.image_item)
#
#         # 텍스트 아이템 생성 및 추가
#         text = """QR CODE INFORMATION
# MODEL           : N3
# DOOR            : 4DR
# DRIVE           : LHD
# REGION          : USA
# TRANSMISSION    : AT
# ROOF            : G/ROOF
# MATERIAL        : CR
# ENGINE          : EV
# WHEEL TYPE      : 2WD
# PASSENGER       : 5_PASSENGER
# BATTERY         : LONG RANGE
# ROOFRACK        : NONE ROOF RACK
# Power Tail Gate : General Tail Gate
# Sliding Console : General Console
# Woofer Speaker  : General
#         """
#         # 텍스트 폭 설정
#         text_width  = 330
#         text_height = 300
#         # 배경 사각형 생성 및 추가
#         background_rect = QGraphicsRectItem(scaled_pixmap.width() - text_width - 20, 0,
#                                             text_width + 20, text_height + 20)
#         background_rect.setBrush(QBrush(QColor(0, 100, 0, 128)))  # 약간 초록색 느낌의 반투명 배경
#         background_rect.setPen(Qt.NoPen)
#         self.scene.addItem(background_rect)
#
#         # 텍스트 아이템 생성 및 추가
#         self.text_item = QGraphicsTextItem(text)
#         self.text_item.setDefaultTextColor(QColor("black"))
#         self.text_item.setFont(QFont('Consolas', 12))
#         self.text_item.setTextWidth(text_width)  # 텍스트 폭 설정
#
#         # 텍스트 위치 설정 (오른쪽 위에 배치)
#         self.text_item.setPos(scaled_pixmap.width() - text_width - 10, 0)
#         self.scene.addItem(self.text_item)
#
#         # 윈도우 설정
#         self.setWindowTitle('Image with Text Overlay')
#         self.setFixedSize(scaled_pixmap.width() + 10, scaled_pixmap.height() + 10)
#
#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     widget = ImageWithTextWidget('../data/hand_color.jpg')
#     widget.show()
#     sys.exit(app.exec_())



import sys
from PySide6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsSimpleTextItem
from PySide6.QtGui import QPixmap, QFont, QColor, QBrush
from PySide6.QtCore import Qt

class ImageWithTextWidget(QGraphicsView):
    def __init__(self, image_path):
        super().__init__()

        # QGraphicsScene 생성
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # 이미지 로드 및 리사이즈 (원래 비율을 무시)
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(922, 747, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        # 이미지 아이템 생성 및 추가
        self.image_item = QGraphicsPixmapItem(scaled_pixmap)
        self.scene.addItem(self.image_item)

        # 텍스트 폭 설정
        text_width = 340
        text_height = 340

        # 배경 사각형 생성 및 추가
        background_rect = QGraphicsRectItem(10, 10, text_width + 20, text_height + 20)
        background_rect.setBrush(QBrush(QColor(0, 100, 0, 128)))  # 약간 초록색 느낌의 반투명 배경
        background_rect.setPen(Qt.NoPen)
        self.scene.addItem(background_rect)

        # 텍스트 항목들 생성 및 추가
        title_text = "QR CODE INFORMATION"
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

        # 가장 긴 label의 길이를 구함
        max_label_length = max(len(label) for label in labels)

        # 타이틀 추가
        title_item = QGraphicsSimpleTextItem(title_text)
        title_item.setBrush(QBrush(QColor("cyan")))
        title_item.setFont(QFont('Consolas', 14, QFont.Bold))
        title_item.setPos(20, 20)
        self.scene.addItem(title_item)

        # 각 항목 추가
        y_offset = 60
        label_color = QColor("black")
        value_color = QColor("white")
        for label, value in zip(labels, values):
            label_item = label.center(max_label_length)
            label_item += " :"
            label_item = QGraphicsSimpleTextItem(label_item)
            label_item.setBrush(QBrush(label_color))
            label_item.setFont(QFont('Consolas', 12))
            label_item.setPos(20, y_offset)
            self.scene.addItem(label_item)

            value_item = QGraphicsSimpleTextItem(value)
            value_item.setBrush(QBrush(value_color))
            value_item.setFont(QFont('Consolas', 12))
            value_item.setPos(200, y_offset)
            self.scene.addItem(value_item)

            y_offset += 20

        # 윈도우 설정
        self.setWindowTitle('Image with Text Overlay')
        self.setFixedSize(922, 747)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = ImageWithTextWidget('../data/hand_color.jpg')
    widget.show()
    sys.exit(app.exec_())
