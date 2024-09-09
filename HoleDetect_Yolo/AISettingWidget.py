import sys

import torch
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QFileDialog, QLabel, \
    QTextEdit, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu, QHBoxLayout, QMessageBox
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from PySide6.QtGui import QContextMenuEvent, QAction, QPainter

import os
from HoleDetect_Yolo.YoloManager import ModelManager, infer_image


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


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class AISettingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.model_manager = ModelManager('model/best.pt')
        self.connect_signals()

        self.hlayout_main = QHBoxLayout()
        self.initUI()
        self.model_path = None  # 선택된 모델 경로를 저장

    def initUI(self):
        layout = QVBoxLayout()

        # 1. 모델 경로 설정
        self.model_path_label = QLabel("모델 경로:")
        layout.addWidget(self.model_path_label)

        self.model_path_line_edit = QLineEdit(self)
        self.model_path_line_edit.setReadOnly(True)
        layout.addWidget(self.model_path_line_edit)

        self.btn_model_path = QPushButton("모델 경로 선택", self)
        self.btn_model_path.clicked.connect(self.select_model_path)
        layout.addWidget(self.btn_model_path)

        # 2. 모델 적용 (경로 설정 후 재시작 필요)
        self.apply_model_button = QPushButton("모델 경로 적용", self)
        self.apply_model_button.clicked.connect(self.apply_model_path)
        layout.addWidget(self.apply_model_button)

        # 3. 모델 테스트
        self.test_inference_button = QPushButton("테스트 인퍼런스", self)
        self.test_inference_button.clicked.connect(self.test_inference)
        layout.addWidget(self.test_inference_button)

        # 4. 테스트 결과 로그
        self.log_text_edit = QTextEdit(self)
        self.log_text_edit.setReadOnly(True)
        layout.addWidget(self.log_text_edit)

        # 결과 표시를 위한 그래픽 뷰
        self.graphics_view = ImageViewer()

        self.hlayout_main.addLayout(layout)
        self.hlayout_main.addWidget(self.graphics_view)

        self.hlayout_main.setStretch(0, 2)
        self.hlayout_main.setStretch(1, 8)

        self.setLayout(self.hlayout_main)

    def connect_signals(self):
        self.model_manager.model_loaded.connect(self.on_model_loaded)
        self.model_manager.model_load_failed.connect(self.on_model_load_failed)

    def on_model_loaded(self):
        QMessageBox.information(self, 'Model Loaded', 'The model has been loaded successfully!')
        self.btn_model_path.setEnabled(True)  # 모델 로드 완료 시 버튼 활성화

    def on_model_load_failed(self, error_message):
        QMessageBox.critical(self, 'Model Load Error', error_message)
        self.btn_model_path.setEnabled(False)  # 모델 로드 실패 시 버튼 다시 비활성화

    def select_model_path(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Model files (*.pt)")
        if file_dialog.exec():
            model_path = file_dialog.selectedFiles()[0]
            self.model_path_line_edit.setText(model_path)
            self.model_path = model_path
            self.log_text_edit.append(f"모델 경로 선택됨: {model_path}")

    def apply_model_path(self):
        if self.model_path:
            self.log_text_edit.append(f"모델 경로가 적용되었습니다: {self.model_path}")

            self.model_manager.model_path = self.model_path
            self.model_manager.load_model()

            self.log_text_edit.append("프로그램을 재시작해야 모델이 적용됩니다.")
        else:
            self.log_text_edit.append("모델 경로를 먼저 선택하세요.")

    def test_inference(self):
        if not self.model_path:
            self.log_text_edit.append("모델 경로가 설정되지 않았습니다. 먼저 모델 경로를 설정하세요.")
            return

        file_name, _ = QFileDialog.getOpenFileName(self, 'Open Image', '', 'Image Files (*.png *.jpg *.jpeg)')
        if file_name:
            image, label_text = infer_image(file_name, self.model_manager.get_model())
            self.log_text_edit.append(f"이미지 선택됨: {file_name}")

            if image is None:
                QMessageBox.information(self, 'Detection Result', label_text)
            else:
                height, width, channels = image.shape
                bytes_per_line = channels * width
                q_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
                pixmap = QPixmap.fromImage(q_image)
                self.graphics_view.set_image(pixmap)
                self.log_text_edit.append("인퍼런스가 완료되었습니다.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AISettingWidget()
    window.setWindowTitle("Yolov5 인퍼런스 설정")
    window.show()
    sys.exit(app.exec())

