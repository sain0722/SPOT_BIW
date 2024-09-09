import threading
import time
from copy import deepcopy
from datetime import datetime
import os
import cv2

from PySide6.QtCore import QThread, Signal
import numpy as np

import DefineGlobal
from DataManager.config import config_utils
from Thread.ArmCorrection import ArmCorrectionData, ArmCorrector, arm_corrector_prepare
from main_operator import MainOperator
from biw_utils import rule_inspection, util_functions


class HoleInspectionProcess(QThread):
    progress = Signal()

    # Signal for completion
    completed = Signal(np.ndarray, bool)
    process_error = Signal()

    def __init__(self, main_operator: MainOperator, position: str):
        super().__init__()
        self.position = position
        self.main_operator = main_operator

        self.duration_seconds = 1.5
        self.rule_threshold = 0.7

        self.master = ArmCorrectionData()
        self.arm_corrector = ArmCorrector(self.main_operator.spot_robot)

        self.running = True  # 스레드 실행 여부를 나타내는 플래그

        self.hole_inspection_result = False

    def run(self):
        self.running = True
        self.hole_inspection_result = False

        # Hole Inspection 일 때는 4k 이미지 취득
        # self.main_window.robot.robot_camera_param_manager.set_resolution("4096x2160")
        try:
            # Set Focus Absolute
            focus_absolute = self.main_operator.spot_manager.get_focus_absolute(self.position)
            self.main_operator.spot_robot.robot_camera_param_manager.set_focus(False, focus_absolute, True)

            waypoint1, waypoint2 = self.main_operator.spot_manager.get_hole_waypoint()
            self.move_to_waypoint(waypoint1)

            # joint up
            up_params = [-0.013, -1.7133, 0.5644, -0.0466, 1.0832, 0.0114]
            self.main_operator.spot_joint_move_manual(up_params)

            self.move_to_waypoint(waypoint2)

            self.main_operator.height_change(0.3)
            self.joint_move(is_wait_until_arm_arrive=True)

            # is_arm_correct = config_utils.is_arm_correction()
            is_arm_correct = True

            if is_arm_correct:
                st_time = time.time()
                arm_corrector_prepare(self.master, self.arm_corrector)
                try:
                    self.arm_corrector.run()
                except Exception as arm_correction_error:
                    print(f"Arm Correction Error: {arm_correction_error}")

                end_time = time.time()
                elapsed_time = end_time - st_time
                elapsed_log = f"Arm Correction Elapsed Time : {elapsed_time}s"
                self.main_operator.write_log(elapsed_log)

            # 3. 촬영
            self.main_operator.spot_robot.robot_camera_param_manager.set_led_mode("TORCH")
            self.main_operator.spot_robot.robot_camera_param_manager.set_led_torch_brightness(f_torch_brightness=1.0)
            time.sleep(1.0)
            print("capture start")
            image = self.capture_rgb()

            self.main_operator.spot_robot.robot_camera_param_manager.set_led_mode("OFF")

            up_params = [-0.013, -1.7133, 0.5644, -0.0466, 1.0832, 0.0114]
            cmd_id = self.main_operator.spot_joint_move_manual(up_params)
            is_wait_until_arm_arrive = True
            if is_wait_until_arm_arrive:
                self.main_operator.spot_robot.robot_commander.wait_until_arm_arrives(cmd_id, 1.0)

            self.move_to_waypoint(waypoint1)
            self.stow()
            self.stop()

            # RUN HOLE INSPECTION
            rule_inspection_thread = threading.Thread(target=self.run_hole_inspection, args=[image])
            rule_inspection_thread.start()
            #
            # rule_result_image, region_image, hole_inspection_result = self.run_hole_inspection(image)

            # Hole Inspection 결과 표시
            # 결과 화면 표시

            # utils.save_image(path, image)
            # utils.save_image(rule_result_path, rule_result_image)
            # self.completed.emit()
            #
            # # Battery Check
            # battery_threshold = self.main_window.sbx_battery_threshold.value()
            # if self.main_window.robot.is_battery_low(battery_threshold):
            #     robot = self.main_window.robot
            #     dock_id = robot.dock_id
            #
            #     self.main_window.write_log(f"Battery Low, Setting Threshold: {battery_threshold}")
            #
            #     def on_operation_complete(success, message):
            #         if success:
            #             self.main_window.write_log(message)
            #         else:
            #             self.main_window.write_log(message)
            #
            #     from Thread.modules.DockingThread import DockingThread
            #     dock_thread = DockingThread(robot, dock_id, is_docking=True)
            #     dock_thread.operation_result.connect(on_operation_complete)
            #     dock_thread.start()
        except Exception as e:
            print(f"[{datetime.now()}] HoleInspectionProcessThread.py - Exception Raised. {e}")
            waypoint1, waypoint2 = self.main_operator.spot_manager.get_hole_waypoint()
            self.move_to_waypoint(waypoint1)
            self.stow()
            self.process_error.emit()

    def stop(self):
        # 스레드를 종료하기 위해 running 플래그를 False로 설정
        self.running = False

    def move_to_waypoint(self, waypoint: str):
        nav_manager = self.main_operator.spot_robot.robot_graphnav_manager
        return nav_manager.navigate_to(waypoint)

    def joint_move(self, is_wait_until_arm_arrive=True):
        arm_position = self.main_operator.spot_manager.get_arm_setting(self.position)
        arm_manager = self.main_operator.spot_robot.robot_arm_manager
        arm_position_list = [arm_position['sh0'], arm_position['sh1'], arm_position['el0'], arm_position['el1'], arm_position['wr0'], arm_position['wr1']]
        cmd_id = arm_manager.joint_move_manual(arm_position_list)

        command_manager = self.main_operator.spot_robot.robot_commander
        if is_wait_until_arm_arrive:
            command_manager.wait_until_arm_arrives(cmd_id, self.duration_seconds)
        # command_manager.wait_command(cmd_id)

    def capture_rgb(self) -> np.ndarray:
        camera_manager = self.main_operator.spot_robot.robot_camera_manager
        image = camera_manager.take_image()
        return image

    def stow(self):
        arm_manager = self.main_operator.spot_robot.robot_arm_manager
        arm_manager.stow()

    def run_for_teaching(self):
        # Set Focus Absolute
        focus_absolute = self.main_operator.spot_manager.get_focus_absolute(self.position)
        self.main_operator.spot_robot.robot_camera_param_manager.set_focus(False, focus_absolute, True)

        waypoint1, waypoint2 = self.main_operator.spot_manager.get_hole_waypoint()
        self.move_to_waypoint(waypoint1)

        # joint up
        up_params = [-0.013, -1.7133, 0.5644, -0.0466, 1.0832, 0.0114]
        self.main_operator.spot_joint_move_manual(up_params)

        self.move_to_waypoint(waypoint2)

        self.main_operator.height_change(0.3)
        self.joint_move(is_wait_until_arm_arrive=True)

    def run_hole_inspection(self, image):
        # Rule Inspection
        hole_inspection_setting = self.main_operator.spot_manager.get_hole_inspection_setting()
        region = hole_inspection_setting['region']

        st_time = time.time()
        roi_file_path = hole_inspection_setting['template_image_path']
        rois_path = [os.path.join(roi_file_path, path) for path in os.listdir(roi_file_path) if
                     path.lower().endswith('png')]
        rois_image = [cv2.imread(file) for file in rois_path]
        # 저장된 ROI들 중에서 가장 높은 점수를 받은 ROI 선택.
        best_roi, top_left, bottom_right, max_val, best_roi_file_path = rule_inspection.select_best_roi(image,
                                                                                                        rois_image,
                                                                                                        region,
                                                                                                        self.rule_threshold,
                                                                                                        rois_path)

        drawed_image = deepcopy(image)
        if best_roi is not None:
            rule_result_image = rule_inspection.draw_match_result(drawed_image, top_left, bottom_right, max_val,
                                                                  best_roi.shape[1], best_roi.shape[0])

            end_time = time.time()
            elapsed_time = end_time - st_time
            elapsed_log = f"Rule Inspection Elapsed Time : {elapsed_time}s \n Best ROI: {best_roi_file_path}"
            # self.main_window.write_log(elapsed_log)
            print(elapsed_log)
            hole_inspection_result = True
        else:
            rule_result_image = drawed_image
            # self.main_window.write_log(f"No suitable ROI found or max_val is less than {self.rule_threshold}")
            hole_inspection_result = False
            print("False")

        # # draw bbox
        # # 1. 1920x1080
        # pt1 = (778, 320)
        # pt2 = (1078, 620)
        #
        # # 2. 3840x2160
        # pt1 = (1674, 760)
        # pt2 = (1974, 1060)
        x, y, w, h = region
        pt1 = x, y
        pt2 = x + w, y + h
        util_functions.draw_box(rule_result_image, pt1, pt2, color=(0, 255, 0))

        # self.progress.emit(rule_result_image, self.main_window.gview_image)

        region_image = image[y:y + h, x:x + w]

        self.completed.emit(rule_result_image, hole_inspection_result)

        # SAVE IMAGES
        self.save_result_images(image, rule_result_image, region_image)

        return rule_result_image, region_image, hole_inspection_result

    def save_result_images(self, image, rule_result_image, region_image):
        # 이미지 저장
        date = datetime.now().strftime("%Y%m%d")
        save_path = DefineGlobal.IMAGE_SAVE_PATH
        path = os.path.join(save_path, date, self.position)
        rule_result_path = os.path.join(save_path, date, self.position, "Rule")
        region_path = os.path.join(save_path, date, self.position, "Crop")

        if not os.path.exists(path) or not os.path.exists(rule_result_path) or not os.path.exists(region_path):
            os.makedirs(path, exist_ok=True)
            os.makedirs(rule_result_path, exist_ok=True)
            os.makedirs(region_path, exist_ok=True)

        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 일단 파일명 현재시간으로 동일하게.
        origin_image_fname = f"{current_time}.jpg"
        rule_result_image_fname = f"{current_time}.jpg"
        region_image_fname = f"{current_time}.jpg"

        origin_image_path = os.path.join(path, origin_image_fname)
        rule_result_image_path = os.path.join(rule_result_path, rule_result_image_fname)
        region_image_path = os.path.join(region_path, region_image_fname)

        cv2.imwrite(origin_image_path, image)
        cv2.imwrite(rule_result_image_path, rule_result_image)
        cv2.imwrite(region_image_path, region_image)
