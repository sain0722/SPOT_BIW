from PySide6.QtGui import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QListWidget, QListWidgetItem, QGraphicsPixmapItem, QGraphicsScene

from widget.common.GraphicView import GraphicView


class TemplateDisplayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QHBoxLayout()
        self.imageListWidget = QListWidget()
        # self.imageListWidget.itemClicked.connect(self.onImageSelected)
        self.imageListWidget.currentItemChanged.connect(self.onImageSelected)
        self.gview_image = GraphicView()  # GraphicView 사용
        self.layout.addWidget(self.gview_image)
        self.layout.addWidget(self.imageListWidget)
        self.layout.setStretch(0, 10)
        self.layout.setStretch(1, 3)

        self.setLayout(self.layout)

    def addImageToList(self, pixmap, name):
        item = QListWidgetItem(name)
        self.imageListWidget.addItem(item)
        item.setData(Qt.UserRole, pixmap)

    def onImageSelected(self, item):
        if item is None:
            print("item is None")
            return

        pixmap = item.data(Qt.UserRole)
        pixmap_item = QGraphicsPixmapItem(pixmap)  # QGraphicsPixmapItem 생성
        self.scene = QGraphicsScene()
        self.scene.addItem(pixmap_item)
        self.gview_image.setScenePixmap(self.scene, pixmap_item)
        self.gview_image.fitInView(pixmap_item, Qt.KeepAspectRatio)
