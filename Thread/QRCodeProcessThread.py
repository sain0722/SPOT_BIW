import os
import time
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

import DefineGlobal
from Thread.CaptureThread import CaptureProgressThread
from main_operator import MainOperator
import spot_functions, qr_functions
from qr_functions import read_datamatrix


class QRCodeProcess(QThread):
    # Signal for completion
    completed = Signal()
    read_success = Signal(np.ndarray, np.ndarray, str)
    read_fail = Signal(np.ndarray, str)

    process_error = Signal()

    def __init__(self, main_operator: MainOperator, position: str):
        super().__init__()
        self.position = position
        self.duration_seconds = 1
        self.main_operator = main_operator

        self.running = True  # 스레드 실행 여부를 나타내는 플래그
        # self.capture_thread = CaptureProgressThread(self.main_operator)
        # self.capture_thread.progress.connect(self.on_progress_running)
        # self.capture_thread.completed.connect(self.on_process_completed)
        # self.capture_thread.timeout.connect(self.on_timeout_occurred)

    def run(self):
        self.running = True
        try:
            # QRCode Reading 일 때는 선택된 해상도의 이미지 취득
            focus_absolute = self.main_operator.spot_manager.get_focus_absolute(self.position)
            self.main_operator.spot_robot.robot_camera_param_manager.set_focus(False, focus_absolute, True)

            # s_resolution = self.main_window.cbx_resolution.currentText()
            # self.main_window.robot.robot_camera_param_manager.set_resolution(s_resolution)
            # self.main_window.robot.robot_camera_param_manager.set_focus(False, self.focus_absolute, True)

            # Set Focus Absolute

            # config = config_utils.get_config()
            # waypoint = config[self.position]['waypoint']

            waypoint = self.main_operator.spot_manager.get_waypoint(self.position)
            self.move_to_waypoint(waypoint)

            debug_start_always_p1 = True
            # if not debug_start_always_p1:
            #     waypoint = self.main_operator.spot_manager.get_waypoint(self.position)
            #     self.move_to_waypoint(waypoint)
            #
            # if self.position == "3":
            #     waypoint = self.main_operator.spot_manager.get_waypoint(self.position)
            #     self.move_to_waypoint(waypoint)

            # # Body Assist Setting
            # body_control = spot_command_pb2.BodyControlParams(
            #     body_assist_for_manipulation=spot_command_pb2.BodyControlParams.
            #     BodyAssistForManipulation(enable_hip_height_assist=True, enable_body_yaw_assist=False))
            # blocking_stand(command_client, timeout_sec=10,
            #                params=spot_command_pb2.MobilityParams(body_control=body_control))

            # 3. 촬영
            self.joint_move()
            time.sleep(1.5)
            image = spot_functions.capture_bgr(self.main_operator.spot_robot.robot_camera_manager)

            self.on_progress_running(image)
            # self.main_operator.update_spot_image(image)

            # self.capture_thread.start()
            # self.capture_thread.wait()

            self.completed.emit()

            self.stow()
            self.stop()

        except Exception as e:
            print(f"[{datetime.now()}] QRCodeProcessThread.py - Exception Raised. {e}")
            self.process_error.emit()

    def on_progress_running(self, image):
        # graphic_view = self.body_widget.body_display_widget.image_gview
        self.main_operator.update_spot_image(image)
        image, message, qr_image = qr_functions.read_datamatrix(image)

        if message:
            message = f"QR Code Reading: \n{message}"
            self.main_operator.write_qr_result(message)

            # 작업 완료 신호 발생 후 스레드 종료
            self.read_success.emit(image, qr_image, message)
        else:
            message = "QR Code Read Fail."
            self.read_fail.emit(image, message)

        # 이미지 저장
        date = datetime.now().strftime("%Y%m%d")

        save_path = DefineGlobal.IMAGE_SAVE_PATH
        path = os.path.join(save_path, date, self.position)
        qr_folder = os.path.join(path, "readed_qrcode")
        if not os.path.exists(path) or not os.path.exists(qr_folder):
            os.makedirs(path, exist_ok=True)
            os.makedirs(qr_folder, exist_ok=True)

        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_fname = f"{current_time}.jpg"
        qrimage_fname = f"{current_time}.png"
        image_path = os.path.join(path, image_fname)
        qrimage_path = os.path.join(qr_folder, qrimage_fname)
        cv2.imwrite(image_path, image)
        if qr_image is not None:
            cv2.imwrite(qrimage_path, qr_image)


    def on_process_completed(self, image, qr_image, qr_content):
        # 결과 이미지 표시
        # graphic_view = self.main_operator.main_window.body_widget.body_display_widget.RH_image_view
        graphic_view = self.main_operator.main_window.body_widget.body_display_widget.image_gview
        # qr_gview = self.main_operator.main_window.body_widget.body_display_widget.RH_qr_code_1_image
        # self.main_operator.update_spot_image(image, graphic_view)
        qr_content = "QR CODE INFORMATION\n"
        qr_content += "MODEL: N3"
        qr_content += "DOOR: 4DR"
        qr_content += "DRIVE: LHD"
        qr_content += "REGION: USA"
        qr_content += "TRANSMISSION: AT"
        qr_content += "ROOF: G/ROOF"
        qr_content += "MATERIAL: CR"
        qr_content += "ENGINE: EV"
        qr_content += "WHEEL TYPE: 2WD"
        qr_content += "PASSANGER: 5_PASSANGER"
        qr_content += "BATTERY: LONG RANGE"
        qr_content += "ROOFRACK: NONE ROOF RACK"
        qr_content += "POWERTAILGATE: General Tail Gate"
        qr_content += "Sliding Console: General Console"
        qr_content += "Woofer Speaker: General Speaker"
        self.main_operator.update_spot_image_with_text(image, graphic_view, qr_content)
        # self.main_operator.update_spot_image(qr_image, qr_gview)

        # 결과 텍스트 표시
        self.main_operator.write_qr_result(qr_content)

        # utils.set_graphic_view_image(image, graphic_view)

        # 결과 화면 표시
        # position_number = self.position[-1]
        # frame_widget = getattr(self.main_window.process_result_widget, f"frame_point_{position_number}", None)
        # self.main_window.process_result_widget.show_inspection_result(frame_widget, qr_image, qr_content)

        # 이미지 저장
        date = datetime.now().strftime("%Y%m%d")

        save_path = DefineGlobal.IMAGE_SAVE_PATH
        path = os.path.join(save_path, date, self.position)
        qr_folder = os.path.join(path, "readed_qrcode")
        if not os.path.exists(path) or not os.path.exists(qr_folder):
            os.makedirs(path, exist_ok=True)
            os.makedirs(qr_folder, exist_ok=True)

        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_fname = f"{current_time}.jpg"
        qrimage_fname = f"{current_time}.png"
        image_path = os.path.join(path, image_fname)
        qrimage_path = os.path.join(qr_folder, qrimage_fname)
        cv2.imwrite(image_path, image)
        cv2.imwrite(qrimage_path, qr_image)

    def on_timeout_occurred(self, image):
        # graphic_view = self.main_operator.body_widget.body_display_widget.image_gview
        qr_content = "Timeout. Fail to read QR Code."
        self.main_operator.update_spot_image_with_text(image, qr_content)

    def stop(self):
        # 스레드를 종료하기 위해 running 플래그를 False로 설정
        self.running = False

    def move_to_waypoint(self, waypoint: str):
        nav_manager = self.main_operator.spot_robot.robot_graphnav_manager
        return nav_manager.navigate_to(waypoint)

    def joint_move(self):
        # sh0, sh1, el0, el1, wr0, wr1 = config_utils.read_arm_position(position)
        arm_position = self.main_operator.spot_manager.get_arm_setting(self.position)

        arm_manager = self.main_operator.spot_robot.robot_arm_manager
        arm_position_list = [arm_position['sh0'], arm_position['sh1'], arm_position['el0'], arm_position['el1'], arm_position['wr0'], arm_position['wr1']]

        cmd_id = arm_manager.joint_move_manual(arm_position_list)

        command_manager = self.main_operator.spot_robot.robot_commander
        command_manager.wait_until_arm_arrives(cmd_id, self.duration_seconds)

    def stow(self):
        arm_manager = self.main_operator.spot_robot.robot_arm_manager
        arm_manager.stow()

