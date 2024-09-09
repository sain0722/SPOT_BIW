from PySide6.QtCore import Qt
from PySide6.QtGui import QContextMenuEvent, QAction, QPainter
from PySide6.QtWidgets import QMenu, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # 드래그 모드 설정
        self.setRenderHint(QPainter.Antialiasing)

    def set_image(self, pixmap):
        self.pixmap_item.setPixmap(pixmap)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.setSceneRect(self.pixmap_item.boundingRect())

    def wheelEvent(self, event):
        factor = 1.1
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """우클릭 메뉴 이벤트 처리"""
        context_menu = QMenu(self)
        fit_in_view_action = QAction("Fit in View", self)
        fit_in_view_action.triggered.connect(self.fit_in_view)

        context_menu.addAction(fit_in_view_action)

        context_menu.exec(event.globalPos())

    def fit_in_view(self):
        """'Fit in View' 기능 구현"""
        self.fitInView(self.scene.itemsBoundingRect(), Qt.IgnoreAspectRatio)
