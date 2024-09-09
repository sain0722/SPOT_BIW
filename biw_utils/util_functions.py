# Function to show the message box
import os
from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QIcon, QFont
from PySide6.QtWidgets import QMessageBox, QGraphicsPixmapItem, QGraphicsScene
import numpy as np
import cv2

import DefineGlobal


def is_position_RH():
    return DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH

def is_position_LH():
    return DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.LH


def get_information_box(text: str = "", font: QFont = QFont("현대하모니 L", 14), title: str = "Information"):
    msg_box = QMessageBox()
    msg_box.setFont(font)
    msg_box.setWindowIcon(QIcon('resources/BIW_logo.png'))
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    # msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    return msg_box


def show_message(text: str = "", font: QFont = QFont("현대하모니 L", 14), title: str = "Information"):
    msg_box = QMessageBox()
    msg_box.setFont(font)
    msg_box.setWindowIcon(QIcon('resources/BIW_logo.png'))
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec_()


def show_confirm_box(text: str = "", font: QFont = QFont("현대하모니 L", 14), title: str = "Information"):
    msg_box = QMessageBox()
    msg_box.setFont(font)
    msg_box.setWindowIcon(QIcon('resources/BIW_logo.png'))
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    return msg_box.exec_()


def get_critical_box(text: str = "", font: QFont = QFont("현대하모니 L", 14), title: str = "Error"):
    msg_box = QMessageBox()
    msg_box.setFont(font)
    msg_box.setWindowIcon(QIcon('resources/BIW_logo.png'))
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    # msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    return msg_box


def read_spot_arm_position(arm_pose_json):
    sh0 = arm_pose_json['sh0']
    sh1 = arm_pose_json['sh1']
    el0 = arm_pose_json['el0']
    el1 = arm_pose_json['el1']
    wr0 = arm_pose_json['wr0']
    wr1 = arm_pose_json['wr1']

    return sh0, sh1, el0, el1, wr0, wr1


def convert_to_target_pose(arm_position_real):
    target_pose = {
        "x": arm_position_real["position"]["x"],
        "y": arm_position_real["position"]["y"],
        "z": arm_position_real["position"]["z"],
        "rotation": {
            "w": arm_position_real["rotation"]["w"],
            "x": arm_position_real["rotation"]["x"],
            "y": arm_position_real["rotation"]["y"],
            "z": arm_position_real["rotation"]["z"],
        },
    }
    return target_pose


def draw_box(image: np.ndarray, pt1, pt2, color=(0, 255, 0), thickness=4):
    cv2.rectangle(image, pt1, pt2, color, thickness)


def select_roi(origin_image: np.ndarray) -> tuple:
    image = deepcopy(origin_image)

    # 모니터 화면 크기 가져오기
    screen_width, screen_height = 1920, 1080  # 여기에 모니터의 해상도를 설정합니다. 실제 모니터 해상도로 변경해야 합니다.

    # 이미지 크기 가져오기
    image_height, image_width, _ = image.shape

    # 이미지 크기가 화면보다 크면 화면 크기에 맞게 이미지 크기 조정
    if image_height > screen_height or image_width > screen_width:
        scale_factor = min(screen_width / image_width, screen_height / image_height)
        image = cv2.resize(image, None, fx=scale_factor, fy=scale_factor)

    # selectROI 호출
    region = cv2.selectROI("region", image, showCrosshair=False)
    cv2.destroyAllWindows()

    # 이미지 크기 조정된 비율 계산
    scale_x = image_width / image.shape[1]
    scale_y = image_height / image.shape[0]

    # ROI 좌표를 비율에 따라 조정
    x, y, w, h = region
    x = int(x * scale_x)
    y = int(y * scale_y)
    w = int(w * scale_x)
    h = int(h * scale_y)

    return x, y, w, h


def set_graphic_view_image(image, view):
    qpixmap = convert_image_to_pixmap(image)
    pixmap_item = QGraphicsPixmapItem(qpixmap)
    scene = QGraphicsScene()
    scene.addItem(pixmap_item)
    view.setScenePixmap(scene, pixmap_item)
    view.fitInView(pixmap_item, Qt.KeepAspectRatio)


def convert_image_to_pixmap(image_input):
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


def read_roi_images(roi_filepath) -> list:
    # 확장자가 ".png"인 파일만 읽음
    ext = ".png"

    # Debug Code
    try:
        rois = [os.path.join(roi_filepath, path) for path in os.listdir(roi_filepath) if path.lower().endswith(ext)]

    except FileNotFoundError as err:
        print("[utils_functions.py] -> read_roi_images: ", err)
        return err

    return rois
