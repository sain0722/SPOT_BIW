import os
import json
import threading
import time
import re
from datetime import datetime
from threading import Thread

from bosdyn.client import UnableToConnectToRobotError, ResponseError
from bosdyn.client.graph_nav import RobotImpairedError
from opcua import Client, ua

from PIL import Image

from PySide6 import QtCore
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QMessageBox

import DefineGlobal
import biw_utils.spot_functions
from Thread.ArmCorrection import ArmCorrector, ArmCorrectionData, arm_corrector_prepare
from Thread.CaptureThread import CaptureThread
from Thread.DockingThread import DockingThread
from Thread.SpotImageViewThread import SpotImageViewThread
from Thread.SpotStatusUpdateThread import SpotStatusUpdateThread
from Thread.WorkStatusUpdateThread import WorkStatusUpdateThread
from communication.OPC.opc_client import BIWOPCUAClient
from biw_utils import util_functions
from biw_utils.decorators import exception_decorator, spot_connection_check
from biw_utils.util_functions import *
import biw_utils.spot_functions as spot_functions
from DataManager.InspectionDataManager import InspectionDataManager
from DataManager.SpotDataManager import SpotDataManager
from Spot.SpotRobot import Robot
from widget.common.GraphicView import GraphicView
from widget.common.GraphicViewWithText import GraphicViewWithText


# from main_window import MainWindow


class MainOperator(QObject):
    config_path = "DataManager/config"
    fname_inspection_data_config = "inspection_data_config.json"
    fname_spot_data_config = DefineGlobal.SPOT_DATA_FILE_NAME

    # UI Events
    event_update_spot_status = Signal(str, str, str, int, str, bool, bool, str, str)
    event_update_depth_qpixmap = Signal(QPixmap)
    event_update_cycle_time = Signal(float)
    event_update_log_message = Signal(str)
    event_update_waypoints_list = Signal()
    event_update_work_status = Signal(DefineGlobal.WORK_STATUS)
    event_update_work_complete_status = Signal(bool)
    event_update_by_pass_status = Signal(bool)

    # OPC Events
    opc_connection_status_changed = Signal(bool)
    opc_data_changed = Signal(str, ua.Variant)
    opc_received_agv_signal = Signal(bool)
    opc_received_spec_data = Signal(str, str, str)
    opc_received_agv_no = Signal(str)

    # NavigationSettingWidget
    event_qr_setting_waypoints = Signal(list)
    event_update_spot_image = Signal(np.ndarray)
    event_update_spot_image_with_text = Signal(np.ndarray, str)
    event_update_hole_inspection_result = Signal(bool)

    # SEND WORK COMPLETE
    event_send_work_complete = Signal()

    # 차종 정보 데이터
    spec_data = None
    agv_no = None
    body_type = None
    hole_spec_type = None
    hole_ng_occurred = False

    def __init__(self):
        super().__init__()

        self.spot_robot = Robot()
        self.spot_manager = SpotDataManager()
        self.inspection_manager = InspectionDataManager()
        self.load_initial_data()

        # OPC
        self.opc_client = BIWOPCUAClient(DefineGlobal.SERVER_URL)
        self.opc_client.data_changed.connect(self.handle_data_changed)
        self.opc_client.received_spec_data.connect(self.handle_received_spec_data)
        self.opc_client.received_agv_signal.connect(self.handle_received_agv_signal)
        self.opc_client.received_agv_no.connect(self.handle_received_agv_no)

        # SPOT
        self.reconnect_thread = SpotReconnectThread(self.connect_robot)

        from Thread.ProcessThread import ProcessThread
        self.process_manager = ProcessThread(self, self.opc_client)

        # Heartbeat Thread
        # self.heartbeat_thread = HeartbeatThread(self)
        # self.heartbeat_thread.heartbeat_signal.connect(self.update_opc_connection_status)
        # self.heartbeat_thread.heartbeat_signal.connect(self.opc_client.is_connected)
        # self.start_heartbeat()

        # WORK STATUS Thread
        self.work_status_update_thread = WorkStatusUpdateThread(self.opc_client)
        self.work_status_update_thread.progress_update_work_status.connect(self.handle_progress_work_status)
        self.work_status_update_thread.progress_update_work_complete_status.connect(self.handle_progress_work_complete_status)

        # Program Start
        # self.opc_connect()
        # self.spot_connect()
        # self.process_manager.start()
        # self.work_status_update_thread.start()

        self.status_thread = None
        self.capture_rgb_thread = None
        self.capture_rgb_function = None

        # Demo Thread
        self.demo_thread = DemoThread(self)

    def get_spot_manager(self):
        return self.spot_manager

    def get_inspection_manager(self):
        return self.inspection_manager

    def spot_connect(self):
        spot_config = self.spot_manager.get_spot_setting("connection")
        robot_ip = spot_config["robot_ip"]
        username = spot_config["username"]
        password = spot_config["password"]
        dock_id  = DefineGlobal.SPOT_POSITION.value
        try:
            self.connect_robot(robot_ip, username, password, dock_id)
            self.toggle_lease()

        except UnableToConnectToRobotError as disconnect_error:
            self.write_log(disconnect_error)

    def connect_robot(self, robot_ip, username, password, dock_id):
        spot_connected, message = self.spot_robot.connect(robot_ip, username, password, dock_id)

        if spot_connected:
            # E-STOP (Cut Motor Power Authority)
            try:
                self.spot_robot.robot_estop_manager.start_estop()
            except Exception as e:
                print(f"[main_operator.py] - Raised Error Start Estop. \n{e}")

            # SPOT STATUS UPDATE THREAD
            self.status_thread = SpotStatusUpdateThread(self.spot_robot)
            self.status_thread.progress.connect(self.update_spot_status)
            self.status_thread.start()

            self.capture_rgb_function = self.spot_robot.robot_camera_manager.take_image
            self.capture_rgb_thread = CaptureThread(self.capture_rgb_function)
            # self.capture_rgb_thread.progress.connect(self._test_show_live_image)
            self.capture_rgb_thread.progress_log.connect(self.write_log)
            self.upload_navigation_map_to_spot()
            self.write_log(message)

        else:
            self.write_log(message)
            # self.main_window.body_widget.body_display_widget.update_spot_connection_status("disconnected.")

        return spot_connected

    def upload_navigation_map_to_spot(self):
        nav_manager = self.spot_robot.robot_graphnav_manager

        self.spot_robot.robot_recording_manager.clear_map()
        nav_manager.upload_graph_and_snapshots(DefineGlobal.SPOT_NAVIGATION_MAP)

        self.try_localize()

    def update_spot_status(self, lease, power, status, bar_val, time_left, connected, localized, estop_status, sw_estop_status):
        # @TODO: SPOT STATUS UPDATE
        try:
            self.event_update_spot_status.emit(lease, power, status, bar_val, time_left, connected, localized, estop_status, sw_estop_status)
        except Exception as e:
            print(f"[main_operator.py] - update_spot_status raised. \n{e}")

    def update_spot_control_params(self, body_speed, arm_speed, camera_params):
        control_params = {
            "body_speed": body_speed,
            "arm_speed": arm_speed,
            "camera_params": camera_params
        }
        self.spot_manager.set_control_params(control_params)
        # self.spot_manager.update_control_params(body_speed, arm_speed, camera_params)
        # self.save_config('spot_data_config.json', self.spot_manager.get_control_params())

    def update_spot_body_speed(self, body_speed):
        self.spot_robot.robot_move_manager.velocity_base_speed = body_speed
        self.spot_robot.robot_move_manager.VELOCITY_BASE_ANGULAR = body_speed
        self.spot_manager.set_spot_body_speed(body_speed)

    def update_spot_arm_speed(self, arm_speed):
        self.spot_robot.robot_arm_manager.VELOCITY_HAND_NORMALIZED = arm_speed
        self.spot_robot.robot_arm_manager.VELOCITY_ANGULAR_HAND = arm_speed
        self.spot_manager.set_spot_arm_speed(arm_speed)

    def update_qr_setting_waypoints(self):
        print("update qr setting waypoints")
        # @TODO: UPDATE WAYPOINT IN SETTING PAGE
        waypoints_list, _ = self.spot_robot.robot_graphnav_manager.list_graph_waypoint_and_edge_ids()
        # self.event_update_waypoints_list.emit(waypoints_list)

    def load_initial_data(self):
        control_params = self.spot_manager.get_control_params()
        inspection_settings = self.spot_manager.get_inspection_settings()
        depth_settings = self.spot_manager.get_depth_settings()

    def spot_capture_bgr(self):
        camera_manager = self.spot_robot.robot_camera_manager
        if self.spot_robot.robot is None:
            show_message(text="Spot is disconnected. Check SPOT Connection")
            return
        image = spot_functions.capture_bgr(camera_manager)
        return image

        # @TODO: UPDATE SPOT CAPTURE IMAGE ON MAIN LABEL
        # self.main_window.body_widget.body_display_widget.RH_image_view.set_bgr_image(image)

    def spot_joint_move_manual(self, params: list):
        robot_arm_manager = self.spot_robot.robot_arm_manager
        if self.spot_robot.robot is None:
            show_message(text="Spot is disconnected. Check SPOT Connection")
            return
        return robot_arm_manager.joint_move_manual(params)

    @exception_decorator
    def spot_move_to_waypoint(self, waypoint):
        graph_nav_manager = self.spot_robot.robot_graphnav_manager
        result = graph_nav_manager.navigate_to(waypoint)
        if not result:
            print("Navigation Failed. NavigateToResponse Error.\nCheck Spot Status.")
            self.write_log("Navigation Failed. NavigateToResponse Error. Check Spot Status.")

    def run_move_to_waypoint(self, waypoint):
        move_thread = Thread(target=self.spot_move_to_waypoint, args=[waypoint])
        move_thread.start()
        move_thread.join()

    # def run_move_forward_position2(self):

    def run_arm_correction(self):
        arm_corrector = ArmCorrector(self.spot_robot)
        master = ArmCorrectionData()
        arm_corrector_prepare(master, arm_corrector)

        master_position = master.hand_pose["position"]
        current_position = self.spot_robot.get_hand_position_dict()["position"]

        localized_waypoint = self.spot_robot.robot_graphnav_manager.find_localized_waypoint()
        _, corrected_position = self.spot_manager.get_hole_waypoint()

        is_arm_within_tolerance = spot_functions.is_position_within_tolerance(master_position, current_position, 10)
        is_corrected_waypoint = localized_waypoint == corrected_position
        # is_arm_within_tolerance = True
        # is_corrected_waypoint = True

        if is_corrected_waypoint and is_arm_within_tolerance:
            arm_correction_thread = threading.Thread(target=arm_corrector.run)
            arm_correction_thread.start()
        else:
            message = "Position 2 위치에서 Arm Reach 상태에서만 가능합니다."
            msg_box = QMessageBox()
            msg_box.setWindowFlags(Qt.WindowStaysOnTopHint)
            msg_box.information(None, "알림", message, QMessageBox.Ok)

    def update_spot_image(self, image):
        self.event_update_spot_image.emit(image)

    def update_spot_image_with_text(self, image, text: str):
        self.event_update_spot_image_with_text.emit(image, text)
        # pil_img = Image.fromarray(image)
        # pil_resized_img = pil_img.resize((922, 747), Image.LANCZOS)
        # gview.set_bgr_image_with_text(pil_resized_img, text)

    def update_hole_inspection_result(self, hole_inspection_result: bool):
        self.event_update_hole_inspection_result.emit(hole_inspection_result)

    def start_capture_thread(self):
        if self.capture_rgb_thread is None:
            print("capture_rgb_thread is None. spot disconnected.")
            return
        self.capture_rgb_thread.start()

    @exception_decorator
    def toggle_lease(self):
        return self.spot_robot.command_dictionary["lease"]()

    @exception_decorator
    def toggle_power(self):
        return self.spot_robot.command_dictionary["power"]()

    @exception_decorator
    def toggle_estop(self):
        return self.spot_robot.command_dictionary["estop"]()

    def get_estop(self):
        return self.spot_robot.command_dictionary["get_estop"]()

    def run_estop(self):
        self.spot_robot.robot_estop_manager.stop_estop()

    def run_release_estop(self):
        self.spot_robot.robot_estop_manager.release_estop()

    @exception_decorator
    def try_localize(self):
        state, _ = self.spot_robot.robot_graphnav_manager.get_localization_state()
        return self.spot_robot.robot_graphnav_manager.is_localized()

    @exception_decorator
    def docking(self):
        # TODO: move to dock prep and docking
        # TODO: docking thread
        if not self.spot_robot.is_connected:
            show_message(text="spot is disconnected.")
            return

        if not self.spot_robot.motors_powered:
            show_message(text="motor power status is off.")
            return

        self.spot_robot.robot_arm_manager.stow()

        dock_prep_waypoint = f"Dock {DefineGlobal.SPOT_POSITION.value} Prep Pose"
        self.run_move_to_waypoint(dock_prep_waypoint)

        dock_thread = threading.Thread(target=self.spot_robot.dock)
        dock_thread.start()

    def run_establish_timesync(self):
        self.spot_robot.establish_timesync()

    def confirm_spot_is_charging(self):
        return self.spot_robot.spot_is_charging()

    def height_change(self, height):
        self.spot_robot.robot_height_change(height)

    def write_qr_result(self, qr_result: str):
        print(qr_result)

        # @TODO: UPDATE QR CODE RESULT
        # label = self.main_window.body_widget.body_display_widget.RH_qr_code_1_info
        # label.setText(qr_result)

    def write_cycle_time(self, elapsed_time):
        print(elapsed_time)

        # TODO: UPDATE CYCLE TIME
        self.event_update_cycle_time.emit(elapsed_time)
        # label = self.main_window.body_widget.body_display_widget.lbl_tack_time_value
        # label.setText(str(elapsed_time))

    def write_log(self, log_message):
        # print(log_message)

        # TODO: WRITE LOG IN LOG PAGE
        self.event_update_log_message.emit(f"{log_message}")
        # log_widget = self.main_window.body_widget.body_admin_widget.page6.spot_control_log
        # log_widget.addItem(log_message)

    def hand_depth_test(self):
        camera_manager = self.spot_robot.robot_camera_manager
        image_client = camera_manager.image_client
        source = "hand_depth"
        depth_array = biw_utils.spot_functions.get_depth_data(image_client, source)

        # TODO: UPDATE DEPTH IMAGE
        depth_qpixmap = biw_utils.spot_functions.depth_array_to_qpximap(depth_array)
        self.event_update_depth_qpixmap.emit(depth_qpixmap)

        min_distance = biw_utils.spot_functions.measure_distance(depth_array)
        print(min_distance)

        is_within_range = biw_utils.spot_functions.is_within_range(min_distance, 0, 330)
        if is_within_range:
            print("move_back")

        return min_distance

    def front_left_depth_test(self):
        camera_manager = self.spot_robot.robot_camera_manager
        image_client = camera_manager.image_client
        source = "frontleft_depth"
        depth_array = biw_utils.spot_functions.get_depth_data(image_client, source)

        # TODO: UPDATE DEPTH IMAGE
        depth_qpixmap = biw_utils.spot_functions.depth_array_to_qpximap(depth_array)
        self.event_update_depth_qpixmap.emit(depth_qpixmap)

        min_distance = biw_utils.spot_functions.measure_distance(depth_array)
        print(min_distance)

        is_within_range = biw_utils.spot_functions.is_within_range(min_distance, 0, 330)
        if is_within_range:
            print("move_back")

        return min_distance

    def front_right_depth_test(self):
        camera_manager = self.spot_robot.robot_camera_manager
        image_client = camera_manager.image_client
        source = "frontright_depth"
        depth_array = biw_utils.spot_functions.get_depth_data(image_client, source)

        # TODO: UPDATE DEPTH IMAGE
        depth_qpixmap = biw_utils.spot_functions.depth_array_to_qpximap(depth_array)
        self.event_update_depth_qpixmap.emit(depth_qpixmap)

        min_distance = biw_utils.spot_functions.measure_distance(depth_array)
        print(min_distance)

        is_within_range = biw_utils.spot_functions.is_within_range(min_distance, 0, 330)
        if is_within_range:
            print("move_back")

        return min_distance

    def opc_connect(self):
        self.opc_client.opc_connect()
        self.opc_connection_status_changed.emit(self.opc_client.connected)

    def opc_disconnect(self):
        self.opc_client.disconnect()
        self.opc_connection_status_changed.emit(self.opc_client.connected)

    def handle_data_changed(self, tag, val):
        self.opc_data_changed.emit(tag, val)

    def handle_received_spec_data(self, data):
        self.spec_data = data
        self.body_type = DefineGlobal.BODY_TYPE.NONE
        self.hole_spec_type = DefineGlobal.HOLE_TYPE.NONE.name

        if self.spec_data:
            if len(self.spec_data) >= 1:
                body_type_data = self.spec_data[DefineGlobal.BODY_TYPE_DATA_INDEX]
                if body_type_data == DefineGlobal.BODY_TYPE.NE.value[0]:
                    self.body_type = DefineGlobal.BODY_TYPE.NE

                if body_type_data == DefineGlobal.BODY_TYPE.ME.value[0]:
                    self.body_type = DefineGlobal.BODY_TYPE.ME

            if len(self.spec_data) > DefineGlobal.SPEC_DATA_INDEX:
                hole_spec_data = self.spec_data[DefineGlobal.SPEC_DATA_INDEX]

                if hole_spec_data == DefineGlobal.HOLE_TYPE.NO_HOLE.value[0]:
                    self.hole_spec_type = DefineGlobal.HOLE_TYPE.NO_HOLE.name

                if hole_spec_data == DefineGlobal.HOLE_TYPE.HOLE.value[0]:
                    self.hole_spec_type = DefineGlobal.HOLE_TYPE.HOLE.name

        self.opc_received_spec_data.emit(data, self.body_type.name, self.hole_spec_type)

    def handle_received_agv_signal(self, agv_signal):
        self.opc_received_agv_signal.emit(agv_signal)

    def handle_received_agv_no(self, agv_no):
        self.agv_no = agv_no
        self.opc_received_agv_no.emit(agv_no)

    def handle_progress_work_status(self, status):
        self.event_update_work_status.emit(status)

    def handle_progress_work_complete_status(self, status):
        self.event_update_work_complete_status.emit(status)

    def update_opc_connection_status(self, connected):
        self.opc_connection_status_changed.emit(connected)

    def get_by_pass_status(self):
        # Read By-Pass Status
        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
            by_pass_status = self.opc_client.read_node_id(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON)
        else:
            by_pass_status = self.opc_client.read_node_id(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON)
        print(f"read by_pass status: {by_pass_status}")
        return by_pass_status

    def opc_tag_read_test(self, tag):
        # 0.8 ~ 0.9s
        root_node = self.opc_client.get_root_node()
        tag_node  = self.opc_client.browse_and_find_node(root_node, tag)
        tag_value = self.opc_client.read_tag(tag_node)
        print(tag_value)

    def opc_tag_read_path_test(self, path):
        # 0.001 ~ 0.003s
        tag_node  = self.opc_client.get_node_by_path(path)
        tag_value = self.opc_client.read_tag(tag_node)
        print(tag_value)

    def opc_tag_write_test(self, tag, value):
        value = int(value)
        self.opc_client.write_tag(tag, value)

    def send_ng_confirm(self):
        if not self.opc_client.connected:
            print(f"[{datetime.now()}] SEND_NG_CONFIRM - OPC IS NOT CONNECTED.")
            self.write_log("SEND_NG_CONFIRM - OPC IS NOT CONNECTED.")
            return False

        if self.agv_no is None:
            print(f"[{datetime.now()}] AGV NO is None.")
            return False

        # AGV NO에 맞는 Carrier Type에 신호 작성
        agv_status_tag = DefineGlobal.OPC_AGV_STATUS(self.agv_no)
        ng_signal_write_result = self.opc_client.write_node_id(agv_status_tag.AGV_I_MF_AGV_Status_Carrier_Type, 1)

        if ng_signal_write_result:
            print(f"[{datetime.now()}] {agv_status_tag.AGV_I_MF_AGV_Status_Carrier_Type} SEND TRUE COMPLETE.")
        else:
            print(f"[{datetime.now()}] {agv_status_tag.AGV_I_MF_AGV_Status_Carrier_Type} SEND TRUE FAIL.")

        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
            write_result = self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP, 1)
        else:
            write_result = self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP, 1)

        DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = True

        return write_result

    def send_work_complete(self):
        if not self.opc_client.connected:
            print(f"[{datetime.now()}] SEND WORK COMPLETE - OPC IS NOT CONNECTED.")
            return False

        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
            write_result = self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP, 1)
        else:
            write_result = self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP, 1)

        DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = True

        return write_result

    def send_by_pass_mode(self):
        if not self.opc_client.connected:
            print(f"[{datetime.now()}] SEND BY-PASS MODE - OPC IS NOT CONNECTED.")
            return False

        # TOGGLE BY PASS MODE
        DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS = not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS

        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
            write_result = self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON,
                                                         DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS)
            write_result |= self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP,
                                                          DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS)
        else:
            write_result = self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON,
                                                         DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS)
            write_result |= self.opc_client.write_node_id(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP,
                                                          DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS)

        return write_result

    def upload_map_into_spot(self, navigation_map_filepath):
        try:
            self.spot_robot.robot_recording_manager.clear_map()
            self.write_log("Complete Clear Map. Uploading new map...")
        except Exception as e:
            self.write_log(f"Clear Map Error Raised: {e}")
            return

        try:
            self.spot_robot.robot_graphnav_manager.upload_graph_and_snapshots(navigation_map_filepath)
            self.spot_robot.robot_graphnav_manager.get_localization_state()
            self.write_log("Complete Upload the new map.")
        except FileNotFoundError as e:
            self.write_log(f"{e} - {navigation_map_filepath}")

    def change_body_type_setting(self, body_type: DefineGlobal.BODY_TYPE):
        # Update Navigation Map

        before_selected_body_type = DefineGlobal.SELECTED_BODY_TYPE
        DefineGlobal.SELECTED_BODY_TYPE = body_type

        DefineGlobal.SPOT_DATA_PATH = f"D:/BIW/CONFIG/{DefineGlobal.SELECTED_BODY_TYPE.name}/{DefineGlobal.SPOT_POSITION.name}"
        DefineGlobal.SPOT_DATA_FILE_NAME = f"spot_data_config_{DefineGlobal.SELECTED_BODY_TYPE.name}_{DefineGlobal.SPOT_POSITION.name}.json"
        DefineGlobal.SPOT_NAVIGATION_MAP = f"{DefineGlobal.SPOT_DATA_PATH}/navigation_map_{DefineGlobal.SELECTED_BODY_TYPE.name}_{DefineGlobal.SPOT_POSITION.name}"

        self.upload_map_into_spot(DefineGlobal.SPOT_NAVIGATION_MAP)

        self.write_log(f"Change Body Type. {before_selected_body_type} -> {DefineGlobal.SELECTED_BODY_TYPE}")
        self.spot_manager.update_data()

    def run_spot_connect(self):
        connect_thread = Thread(target=self.spot_robot.connect)

    def run_spot_reconnect(self):
        if self.reconnect_thread.isRunning():
            return

        self.reconnect_thread.start()

    def run_start_full_demo(self):
        if not self.demo_thread.isRunning():
            self.demo_thread.start()

    def run_stop_full_demo(self):
        if self.demo_thread.isRunning():
            self.demo_thread.stop()

    def run_read_tag(self, tag_name):
        return self.opc_client.read_node_id(tag_name)

    def run_send_signal_on(self, tag_name):
        self.opc_client.write_node_id(tag_name, True)

    def run_send_signal_off(self, tag_name):
        self.opc_client.write_node_id(tag_name, False)

class SpotReconnectThread(QThread):
    hostname = DefineGlobal.SPOT_HOSTNAME
    username = DefineGlobal.SPOT_USERNAME
    password = DefineGlobal.SPOT_PASSWORD
    dock_id  = DefineGlobal.SPOT_DOCK_ID

    def __init__(self, reconnect_function):
        super().__init__()
        self.running = True
        self.reconnect_function = reconnect_function

    def run(self):
        while self.running:
            print("Thread Reconnect")
            is_connect = self.reconnect_function(self.hostname, self.username, self.password, self.dock_id)
            if is_connect:
                print("Reconnect Thread Complete")
                self.stop()
            time.sleep(2)

    def stop(self):
        self.running = False
        self.wait()
        self.quit()


class DemoThread(QThread):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.is_running = True

    def run(self):
        self.is_running = True
        while self.is_running:
            print("run_process_full start")
            self.main_operator.process_manager.run_biw_process()
            time.sleep(1)

    def stop(self):
        self.is_running = False
