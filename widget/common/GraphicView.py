import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PySide6 import QtCore
from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtGui import QPixmap, QImage, QPainter, QFont, QColor, QBrush, QAction
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu, QDialog, QFileDialog, \
    QMessageBox


class GraphicView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pixmap_item = None
        self.current_image = None  # 현재 이미지를 저장하는 멤버 변수
        self.setStyleSheet('padding: 0px; margin: 0px')

    def setScenePixmap(self, scene: QGraphicsScene, pixmap_item: QGraphicsPixmapItem) -> None:
        self.setScene(scene)
        self.pixmap_item = pixmap_item

    def wheelEvent(self, event):
        # 마우스 휠 이벤트 처리
        delta = event.angleDelta().y()
        if delta > 0:
            self.scale(1.1, 1.1)  # 확대
        else:
            self.scale(0.9, 0.9)  # 축소

    def contextMenuEvent(self, event):
        if self.pixmap_item is None:
            return

        context_menu = QMenu(self)

        # show_action = QAction("이미지 확인", self)
        # show_action.triggered.connect(self.show_image)
        save_action = QAction("이미지 저장", self)
        save_action.triggered.connect(self.save_image)  # 이미지 저장 기능에 연결
        fit_action = QAction("fit to view", self)
        fit_action.triggered.connect(self.fit_to_view)

        # context_menu.addAction(show_action)
        context_menu.addAction(save_action)
        context_menu.addAction(fit_action)

        # 추가적인 메뉴 항목이 필요하다면 여기에 추가
        context_menu.exec_(event.globalPos())

    def set_bgr_image(self, image: np.ndarray):
        pixmap_item = create_pixmap_item(image)
        scene = QGraphicsScene()
        scene.addItem(pixmap_item)
        self.setScenePixmap(scene, pixmap_item)
        self.fit_to_view()

    def set_bgr_image_with_text(self, pil_img: Image, text):
        # pil_img = numpy_array_to_pil_image(image)
        pil_img = add_text_to_pil_image(pil_img, text, position='bottom-right')
        pixmap_item = pil_image_to_qt_pixmap_item(pil_img)
        # image = add_text_to_image(image, text)
        # pixmap_item = create_pixmap_item(image)
        scene = QGraphicsScene()
        scene.addItem(pixmap_item)
        self.setScenePixmap(scene, pixmap_item)

    def save_image(self):
        # 파일 저장 대화상자 표시
        file_name, _ = QFileDialog.getSaveFileName(self, "이미지 저장", "",
                                                   "PNG Files (*.png);;JPEG Files (*.jpeg);;All Files (*)")
        if file_name:
            # 이미지 저장
            qimage = self.pixmap_item.pixmap().toImage()
            if qimage.save(file_name):
                # 저장 성공 메시지
                QMessageBox.information(self, "저장 완료", "이미지가 성공적으로 저장되었습니다.")
            else:
                # 저장 실패 메시지
                QMessageBox.warning(self, "저장 실패", "이미지 저장에 실패했습니다.")

    def fit_to_view(self):
        if self.pixmap_item:
            self.fitInView(self.pixmap_item, QtCore.Qt.AspectRatioMode.KeepAspectRatio)


def numpy_to_qimage(bgr_img):
    h, w, ch = bgr_img.shape
    bytes_per_line = ch * w
    return QImage(bgr_img.data, w, h, bytes_per_line, QImage.Format_BGR888)

def qimage_to_qpixmap(qimg):
    return QPixmap.fromImage(qimg)

def create_pixmap_item(bgr_img):
    qimg = numpy_to_qimage(bgr_img)
    qpixmap = qimage_to_qpixmap(qimg)
    return QGraphicsPixmapItem(qpixmap)

def add_text_to_image(image, text, position='top-right', font_scale=1, thickness=2):
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = image.shape[1] - text_size[0] - 10  # 우측 정렬
    text_y = text_size[1] + 10  # 상단 정렬

    if position == 'bottom-right':
        text_y = image.shape[0] - 10  # 하단 정렬

    # 이미지에 텍스트 그리기
    cv2.putText(image, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    return image


def numpy_array_to_pil_image(np_img):
    # NumPy 배열을 PIL 이미지로 변환합니다. (RGB로 가정)
    return Image.fromarray(np_img)


def pil_image_to_qt_pixmap_item(pil_img):
    # PIL 이미지를 QByteArray로 변환
    # data = pil_img.tobytes("raw", "BGR")

    # PIL 이미지를 NumPy 배열로 변환 (BGR to RGB)
    image_array = np.array(pil_img)
    image_array = image_array[:, :, ::-1]  # BGR에서 RGB로 변환

    image_array = np.ascontiguousarray(image_array, dtype=np.uint8)

    # NumPy 배열을 QImage 객체로 변환
    height, width, channels = image_array.shape
    bytes_per_line = channels * width

    # qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGB888)
    qimage = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
    qpixmap = QPixmap.fromImage(qimage)

    return QGraphicsPixmapItem(qpixmap)


def add_text_to_pil_image(image, text, position='top-right'):
    # 폰트 설정
    title_font_size = 20
    text_font_size = 15
    title_font = ImageFont.truetype('./font/NotoSans-Bold.ttf', title_font_size)
    text_font = ImageFont.truetype('./font/NotoSans-Medium.ttf', text_font_size)
    # 드로잉 객체 생성
    draw = ImageDraw.Draw(image)

    text_width, text_height = draw.textsize(text, font=text_font)
    lines = text.split('\n')
    line_heights = [draw.textsize(line, font=text_font)[1] for line in lines]
    label_length = max(len(line.split(':')[0]) for line in lines)

    total_height = sum(line_heights) + (len(lines) - 1) * 5  # 라인 사이의 간격

    # 이미지 크기
    img_width, img_height = image.size

    # 텍스트 위치 계산
    if position == 'top-right':
        text_x = img_width - text_width - 10
        text_y = 10
    elif position == 'bottom-right':
        text_x = img_width - text_width - 10
        text_y = img_height - text_height - 10
    else:
        text_x = 10  # default to top-left if position is not recognized
        text_y = 10

    # 텍스트 색상 설정
    bg_color = (50, 205, 50)
    title_color = (255, 215, 78)  # 금색
    key_color = (0, 0, 0)  # 흰색
    value_color = (173, 216, 230)  # 연한 파랑

    # 배경 사각형 그리기
    draw.rectangle([text_x, text_y, text_x + text_width, text_y + total_height], fill='white')

    x, y = text_x, text_y
    line_height = 5
    for i, line in enumerate(lines):
        if i == 0:
            draw.text((x, y), line.strip(), font=title_font, fill=title_color)
            y += title_font_size + line_height
        else:
            if ':' in line:
                key, value = line.split(':', 1)
                draw.text((x, y), key.strip() + ":", font=text_font, fill=key_color)
                draw.text((img_width - draw.textsize(key + ":", font=text_font)[1] - 180, y), value.strip(), font=text_font,
                          fill=value_color)
            else:
                draw.text((x, y), line.strip(), font=text_font, fill=key_color)
            y += text_font_size + line_height

    return image
