import time

import numpy as np
from PySide6.QtCore import QThread, Signal

from biw_utils import qr_functions, spot_functions


class CaptureThread(QThread):
    # Signal for progress
    progress = Signal(np.ndarray)
    progress_log = Signal(str)

    # Signal for completion
    completed = Signal()

    def __init__(self, capture_function):
        super().__init__()
        self.capture_function = capture_function
        self.running = True  # 스레드 실행 여부를 나타내는 플래그

    def run(self):
        # 스레드 정지 상황에서 버튼 클릭 시, 플래그를 True로 설정
        if not self.running:
            self.running = True
        message = ""
        while self.running:
            image = self.capture_function()
            if image.shape[-1] == 3:
                image, message, qr_image = qr_functions.read_frame(image)
                # image, message, qr_image = qr_functions.read_frame_qreader(image)

            self.progress.emit(image)
            if message:
                message = f"QR Code Reading: {message}"
                self.progress_log.emit(message)

            time.sleep(0.01)

        # 작업 완료 신호 발생 후 스레드 종료
        self.completed.emit()

    def stop(self):
        # 스레드를 종료하기 위해 running 플래그를 False로 설정
        self.running = False


class CaptureProgressThread(QThread):
    progress = Signal(np.ndarray)

    timeout = Signal(np.ndarray)

    # Signal for completion
    completed = Signal(np.ndarray, np.ndarray, str)

    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.running = True  # 스레드 실행 여부를 나타내는 플래그
        self.elasped_time = 0

    def __del__(self):
        self.stop()

    def run(self):
        # 스레드 정지 상황에서 버튼 클릭 시, 플래그를 True로 설정
        if not self.running:
            self.running = True

        st_time = time.time()
        # TODO: Edit Timeout value
        timeout = 0.0
        timeout_occurred = False  # 타임아웃 발생 여부 플래그
        while self.running:
            image = spot_functions.capture_bgr(self.main_operator.spot_robot.robot_camera_manager)

            self.progress.emit(image)

            image, message, qr_image = qr_functions.read_frame(image)

            if message:
                message = f"QR Code Reading: {message}"
                self.main_operator.write_qr_result(message)
                self.stop()

                # 작업 완료 신호 발생 후 스레드 종료
                self.completed.emit(image, qr_image, message)
                self.stop()

            # 몇 초 이상 QR 코드를 인식하지 못하고, 타임아웃 로그가 아직 기록되지 않았을 경우
            elif time.time() - st_time > timeout and not timeout_occurred:
                log_message = "Timeout exceeded: 인식 실패. 해상도를 확인해주세요."
                self.main_operator.write_qr_result(log_message)
                timeout_occurred = True  # 타임아웃 발생 표시
                self.timeout.emit(image)
                self.stop()

            time.sleep(0.01)

    def stop(self):
        # 스레드를 종료하기 위해 running 플래그를 False로 설정
        self.running = False
