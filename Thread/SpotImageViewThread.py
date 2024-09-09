import numpy as np
from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


class SpotImageViewThread(QThread):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.camera_manager = self.main_operator.spot_robot.robot_camera_manager
        self.is_running = False

    def run(self):
        self.is_running = True

        image_sources = ['frontleft_fisheye_image', 'frontright_fisheye_image', 'left_fisheye_image', 'right_fisheye_image']
        images = [self.camera_manager.take_image_from_source(source) for source in image_sources]
        labels = [self.main_operator.main_window.body_widget.body_display_widget.lbl_front_left_fisheye,
                  self.main_operator.main_window.body_widget.body_display_widget.lbl_front_right_fisheye,
                  self.main_operator.main_window.body_widget.body_display_widget.lbl_left_fisheye,
                  self.main_operator.main_window.body_widget.body_display_widget.lbl_right_fisheye,
                  ]

        while self.is_running:
            # 1. image load
            # frontleft_fisheye_image
            # frontright_fisheye_image
            # left_fisheye_image
            # right_fisheye_image
            for image, label in zip(images, labels):
                pixmap = convert_image_to_pixmap(image)
                # scaled_pixmap = pixmap.scaled(320, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label.setPixmap(pixmap)

    def stop(self):
        self.is_running = False
        self.wait()  # Wait for the thread to finish


def convert_image_to_pixmap(image_input):
    """이미지 입력을 QPixmap으로 변환"""
    if isinstance(image_input, np.ndarray):
        # np.ndarray (OpenCV 이미지)일 경우
        image_input = np.ascontiguousarray(image_input, dtype=np.uint8)

        if image_input.shape[-1] == 3:
            height, width, channels = image_input.shape
            format = QImage.Format_RGB888
        else:
            height, width = image_input.shape
            channels = 1
            format = QImage.Format_Grayscale8

        bytes_per_line = channels * width
        qimage = QImage(image_input.data, width, height, bytes_per_line, format)
        return QPixmap.fromImage(qimage.rgbSwapped())
    elif isinstance(image_input, QImage):
        return QPixmap.fromImage(image_input)
    elif isinstance(image_input, QPixmap):
        return image_input
    else:
        raise ValueError("Unsupported image type")
