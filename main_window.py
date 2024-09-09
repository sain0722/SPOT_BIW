import re
import threading
import time
from datetime import datetime

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication, QMessageBox, QPushButton
from PySide6.QtGui import QPalette, QLinearGradient, QColor, QFont, QIcon, QPainter, QCloseEvent
from PySide6.QtCore import QTimer, QDateTime, QThread, Signal, Slot, Qt

import DefineGlobal
from footer import FooterWidget
from header import HeaderWidget
from body import BodyDisplayWidget, BodyWidget
from main_operator import MainOperator
from biw_utils import util_functions
from biw_utils.util_functions import show_message
from widget.DemoWidget import DemoDialog
from opcua import Client, ua

from widget.DisconnectDialog import DisconnectDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Hyundai BIW Inspection Display')
        self.setWindowIcon(QIcon('resources/BIW_logo.png'))
        self.showFullScreen()

        self.hyundai_fontM = QFont("현대하모니 M", 14)
        self.hyundai_fontL = QFont("현대하모니 L", 14)

        self.setFont(self.hyundai_fontM)

        self.main_operator = MainOperator()

        self.applyGradientBackground()
        self.initUI()
        self.initEvent()
        # self.apply_background()
        self.applyStylesheet()

        self.demo_dialog = DemoDialog(self.main_operator)

        # Initial By-Pass Status Check.
        self.update_ui_by_pass_status()

        self.initTimer()
        if self.main_operator.spot_robot.robot is not None:
            self.body_widget.body_admin_widget.page6.get_list_graph()

        self.spot_disconnect_dialog_shown = False

    def applyGradientBackground(self):
        palette = QPalette()
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        # gradient.setColorAt(0.0, QColor(0, 44, 95, 100))  # Hyundai blue
        # gradient.setColorAt(0.0, QColor('#f0f4f7'))  # Hyundai blue
        # gradient.setColorAt(0.5, QColor(0, 44, 95, 100))  # Hyundai blue
        # gradient.setColorAt(1.0, QColor(0, 44, 95, 200))  # 깊은 하늘색

        gradient.setColorAt(0.0, QColor(102, 102, 102))  # 밝은 색상
        # gradient.setColorAt(0.4, QColor(10, 41, 114))  # Hyundai blue (투명도 100)
        # gradient.setColorAt(1.0, QColor(0, 44, 44, 247))  # 깊은 하늘색 (투명도 200)

        palette.setBrush(QPalette.Window, gradient)
        self.setPalette(palette)

    def applyStylesheet(self):
        with open('style/styles.css', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def initUI(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        self.header_widget = HeaderWidget()
        self.body_widget = BodyWidget(self.main_operator)
        self.footer_widget = FooterWidget()
        self.footer_widget.setObjectName("footer")

        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.body_widget)
        main_layout.addWidget(self.footer_widget)
        main_layout.setStretch(0, 0)
        main_layout.setStretch(1, 1)
        main_layout.setStretch(2, 0)

    def initEvent(self):
        self.header_widget.setToggleEvent(self.toggleViewMode)
        self.header_widget.setDemoEvent(self.show_demo_dialog)
        self.header_widget.set_exit_program_event(self.show_exit_dialog)
        self.header_widget.set_toggle_vip_mode(self.toggle_vip_mode)
        self.header_widget.set_run_estop_callback(self.run_estop)

        # self.main_operator.event_update_spot_status.connect(self.update_spot_status)

        # Main Operator Event
        # 1. UI EVENTS
        self.main_operator.event_update_spot_status.connect(self.update_spot_status)
        self.main_operator.event_update_depth_qpixmap.connect(self.update_depth_qpixmap)
        self.main_operator.event_update_cycle_time.connect(self.update_cycle_time)
        self.main_operator.event_update_log_message.connect(self.update_log_message)
        self.main_operator.event_update_waypoints_list.connect(self.update_ui_waypoints_list)
        self.main_operator.event_update_work_status.connect(self.update_ui_work_status)
        self.main_operator.event_update_work_complete_status.connect(self.update_ui_work_complete_status)

        self.main_operator.opc_data_changed.connect(self.update_data_label)
        self.main_operator.opc_received_spec_data.connect(self.update_ui_spec_data)
        self.main_operator.opc_received_agv_signal.connect(self.update_ui_agv_status)
        self.main_operator.opc_received_agv_no.connect(self.update_ui_agv_no)
        self.main_operator.opc_connection_status_changed.connect(self.update_opc_connection_status)

        self.main_operator.event_qr_setting_waypoints.connect(self.update_ui_qr_setting_waypoints)
        self.main_operator.event_update_spot_image.connect(self.update_ui_spot_image)
        self.main_operator.event_update_spot_image_with_text.connect(self.update_ui_spot_image_with_text)
        self.main_operator.event_update_hole_inspection_result.connect(self.update_ui_hole_inspection_result)

        # Body Events
        self.body_widget.body_display_widget.set_send_agv_pass(self.run_send_agv_pass_signal)
        self.body_widget.body_display_widget.set_send_agv_real_ng(self.run_send_agv_real_ng_signal)
        self.body_widget.body_display_widget.set_click_position_home(self.run_event_position_home)
        self.body_widget.body_display_widget.set_click_position1(self.run_event_position1)
        self.body_widget.body_display_widget.set_click_position2(self.run_event_position2)
        self.body_widget.body_display_widget.set_click_position3(self.run_event_position3)
        self.body_widget.body_display_widget.set_click_position_step_back(self.run_event_position_step_back)

        # Body Admin Events
        self.body_widget.body_admin_widget.page4.set_capture_callback(self.run_capture_rgb)

        # Footer Events
        self.footer_widget.set_spot_docking_callback(self.run_spot_docking_callback)
        # self.footer_widget.set_send_work_complete(self.run_send_work_complete)    # remove send work complete.
        self.footer_widget.set_send_by_pass_mode(self.run_send_by_pass)
        self.footer_widget.spot_status_widget.set_toggle_btn_power(self.run_footer_toggle_power)
        self.footer_widget.spot_status_widget.set_toggle_btn_lease(self.run_footer_toggle_lease)
        self.footer_widget.spot_status_widget.set_toggle_btn_localize(self.run_footer_localize)
        self.footer_widget.spot_status_widget.set_toggle_btn_estop(self.run_toggle_estop_auth_callback)
        self.footer_widget.spot_status_widget.set_release_estop(self.run_release_estop)

        # ProcessThread Events
        self.main_operator.process_manager.bypass_signal.connect(self.update_ui_bypass_button)

    def update_spot_status(self, lease, power, bar_status, bar_val, time_left, connected, localized, estop_status, sw_estop_status):
        self.footer_widget.spot_status_widget.set_lease_status(lease)
        self.footer_widget.spot_status_widget.set_power_status(power)
        self.footer_widget.spot_status_widget.set_battery_status(bar_status, bar_val, time_left)
        self.footer_widget.spot_status_widget.set_connection_status(connected)
        self.footer_widget.spot_status_widget.set_localized_status(localized)
        self.footer_widget.spot_status_widget.set_estop_status(estop_status, sw_estop_status)

        auto_reconnected_message = "SPOT is auto reconnected.\nCheck the Lease and Power."
        if connected and self.spot_disconnect_dialog_shown:
            if self.disconnected_popup.isVisible():
                self.disconnected_popup.close()
            self.spot_disconnect_dialog_shown = False
            util_functions.show_message(text=auto_reconnected_message)

        if not connected and not self.spot_disconnect_dialog_shown:
            self.spot_disconnect_dialog_shown = True
            DefineGlobal.PROCESS_THREAD_IS_RUNNING = False
            self.footer_widget.ui_update_system_manual()

            disconnected_message = ("SPOT is disconnected because of network status.\n"
                                    "Try to reconnect...\n"
                                    "Change to MANUAL Mode.\n"
                                    "SPOT should be far from the AGV.\n")

            self.disconnected_popup = util_functions.get_critical_box(text=disconnected_message)
            result = self.disconnected_popup.exec_()
            # if result:
            #     util_functions.show_message(auto_reconnected_message)

    def update_opc_connection_status(self, connected):
        if connected:
            status = "CONNECTED"
        else:
            status = "DISCONNECTED"

        self.body_widget.body_admin_widget.page7.set_connection_status(status)

    def update_depth_qpixmap(self, depth_qpixmap):
        self.body_widget.body_display_widget.image_gview.set_image(depth_qpixmap)

    def update_cycle_time(self, cycle_time):
        self.body_widget.body_display_widget.lbl_cycle_time_value.setText(f"{cycle_time:.2f}s")

    def update_log_message(self, log_message):
        log_widget = self.body_widget.body_admin_widget.spot_control_log
        year = datetime.now().year
        month = datetime.now().month
        day = datetime.now().day

        hour = datetime.now().hour
        minute = datetime.now().minute
        second = datetime.now().second

        microsecond = datetime.now().microsecond

        now = f"{year}{month}{day} {hour}:{minute}:{second:02d}.{microsecond:.2f}"

        log_widget.addItem(f"[{datetime.now()}] {log_message}")
        current_count = log_widget.count()
        if current_count >= 50:
            # 최대 항목 수를 초과하는 경우 가장 오래된 항목을 제거
            log_widget.takeItem(0)

    def event_disconnect(self):
        self.header_widget.spot_status_widget.set_disconnect()

    @Slot(str, ua.Variant)
    def update_data_label(self, tag, value):
        if tag in self.demo_dialog.demo_widget.data_labels:
            self.demo_dialog.demo_widget.data_labels[tag].setText(f"{tag}: {value}")

    def update_ui_qr_setting_waypoints(self, waypoints):
        print("main_window - update waypoints")
        cbx_waypoint1 = self.body_widget.body_admin_widget.page1.cbx_inspection_waypoint
        cbx_waypoint2_1 = self.body_widget.body_admin_widget.page2.cbx_inspection_waypoint1
        cbx_waypoint2_2 = self.body_widget.body_admin_widget.page2.cbx_inspection_waypoint2
        cbx_waypoint3 = self.body_widget.body_admin_widget.page3.cbx_inspection_waypoint

        cbx_waypoint1.clear()
        cbx_waypoint2_1.clear()
        cbx_waypoint2_2.clear()
        cbx_waypoint3.clear()

        for waypoint in waypoints[1:]:
            match = re.search(r'Waypoint name: (.*?) id:', waypoint)
            waypoint_name = match.group(1)
            cbx_waypoint1.addItem(waypoint_name)
            cbx_waypoint2_1.addItem(waypoint_name)
            cbx_waypoint2_2.addItem(waypoint_name)
            cbx_waypoint3.addItem(waypoint_name)

        # config set waypoint
        current_waypoint1 = self.main_operator.spot_manager.get_waypoint("1")
        current_waypoint2_1, current_waypoint2_2 = self.main_operator.spot_manager.get_hole_waypoint()
        current_waypoint3 = self.main_operator.spot_manager.get_waypoint("3")

        cbx_waypoint1.setCurrentText(current_waypoint1)
        cbx_waypoint2_1.setCurrentText(current_waypoint2_1)
        cbx_waypoint2_2.setCurrentText(current_waypoint2_2)
        cbx_waypoint3.setCurrentText(current_waypoint3)

    def update_ui_waypoints_list(self):
        print("main_window - update waypoints")
        self.body_widget.body_admin_widget.page6.get_list_graph()

    def update_ui_work_status(self, work_status):
        self.body_widget.body_display_widget.update_work_status(work_status)

        # DELETE:

    def update_ui_spot_image(self, image):
        gview = self.body_widget.body_display_widget.image_gview
        gview.set_image(image)

    def update_ui_spot_image_with_text(self, image, text):
        gview = self.body_widget.body_display_widget.image_gview
        gview.set_image(image)
        gview.set_text("INSPECTION INFO", text)

    def update_ui_hole_inspection_result(self, hole_inspection_result: bool):
        label = self.body_widget.body_display_widget.lbl_hole_inspection_value
        label.setText(str(hole_inspection_result))

        if self.main_operator.hole_spec_type == DefineGlobal.HOLE_TYPE.HOLE.name:
            b_hole_spec = True
        else:
            b_hole_spec = False

        # If different, ng occurred.
        self.main_operator.hole_ng_occurred = hole_inspection_result != b_hole_spec

        # b_hole_spec = True
        # self.main_operator.hole_ng_occurred = True

        self.main_operator.write_log(f"HOLE INSPECTION RESLUT: {hole_inspection_result}, HOLE SPEC: {b_hole_spec}")
        if self.main_operator.hole_ng_occurred:
            DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = True
            self.body_widget.body_display_widget.widget_hole_inspection_buttons.setEnabled(True)
            self.body_widget.body_display_widget.hole_inspection_button_enabled()

    def update_ui_agv_status(self, agv_status):
        label = self.body_widget.body_display_widget.lbl_agv_status
        if agv_status:
            text = "AGV POS ON"
        else:
            text = "AGV POS OFF"
            # WIDGET HIDE IF AGV OUT.
            self.body_widget.body_display_widget.widget_hole_inspection_buttons.setEnabled(False)
            self.body_widget.body_display_widget.hole_inspection_button_disabled()
            DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = False

        self.set_toggle_status(agv_status, text, label)

    def update_ui_spec_data(self, data, body_type, hole_spec_type):
        spec_data_label = self.body_widget.body_display_widget.lbl_spec_data_value
        body_type_label = self.body_widget.body_display_widget.lbl_body_type_value
        hole_spec_label = self.body_widget.body_display_widget.lbl_hole_spec_value

        spec_data_label.setText(f"{data}")
        body_type_label.setText(f"{body_type}")
        hole_spec_label.setText(f"{hole_spec_type}")

    def update_ui_agv_no(self, agv_no):
        label = self.body_widget.body_display_widget.lbl_agv_no_value
        label.setText(str(agv_no))

    def update_ui_work_complete_status(self, work_complete_status):
        label = self.body_widget.body_display_widget.lbl_work_complete_status
        if work_complete_status:
            text = "WORK COMPLETE ON"
        else:
            text = "WORK COMPLETE OFF"

        self.set_toggle_status(work_complete_status, text, label)

    def update_ui_by_pass_status(self):
        by_pass_status = self.main_operator.get_by_pass_status()
        DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS = by_pass_status

        if by_pass_status:
            self.footer_widget.ui_update_bypass_on()
        else:
            self.footer_widget.ui_update_bypass_off()

    @staticmethod
    def set_toggle_status(status, text, label):
        label.setText(text)
        label.setAlignment(Qt.AlignCenter)
        if status:
            label.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: lime;
                font-size: 16px;
                padding: 20px;
                border-radius: 10px;
            """)
        else:
            label.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: red;
                font-size: 16px;
                padding: 20px;
                border-radius: 10px;
            """)

    def toggleViewMode(self):
        new_mode = self.body_widget.viewModeChange()
        self.header_widget.updateButtonLabel(new_mode)

    def set_array_mainview(self, image):
        self.body_widget.body_display_widget.image_gview.set_image(image)

    def show_demo_dialog(self):
        self.demo_dialog.exec_()

    def show_exit_dialog(self):
        self.close()

    # BODY SETTINGS
    def run_send_agv_pass_signal(self):
        text = "SEND WORK COMPLETE?"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            write_result = self.main_operator.send_work_complete()
            if write_result:
                show_message(text="Send Complete.")
            else:
                show_message(text="Send Fail.")

            DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = False

    def run_send_agv_real_ng_signal(self):
        text = f"SEND NG SIGNAL?\nAGV NO: {self.main_operator.agv_no}"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            write_result = self.main_operator.send_ng_confirm()
            if write_result:
                show_message(text="COMPLETE.")
            else:
                show_message(text="FAIL.")

            DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = False

    def run_event_position_home(self):
        waypoint = self.main_operator.spot_manager.get_waypoint_home()
        text = f"Go Home Position? \nWaypoint: [{waypoint}]"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            if DefineGlobal.PROCESS_THREAD_IS_RUNNING:
                util_functions.show_message(text="Can move only manual mode.")
                return

            DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.HOME
            move_thread = threading.Thread(target=self.main_operator.run_move_to_waypoint, args=[waypoint])
            move_thread.start()

    def run_event_position_step_back(self):
        waypoint = self.main_operator.spot_manager.get_waypoint_complete()
        text = f"Go Step Back Position? \nWaypoint: [{waypoint}]"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            if DefineGlobal.PROCESS_THREAD_IS_RUNNING:
                util_functions.show_message(text="Can move only manual mode.")
                return
            DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.COMPLETE
            move_thread = threading.Thread(target=self.main_operator.run_move_to_waypoint, args=[waypoint])
            move_thread.start()

    def run_event_position1(self):
        image = self.main_operator.inspection_manager.get_inspection_image(1)
        data  = self.main_operator.inspection_manager.get_inspection_data(1)

        if image is None:
            show_message("No Image")
            return

        if data is None:
            data = "No Data"

        self.update_ui_spot_image_with_text(image, data)

    def run_event_position2(self):
        image = self.main_operator.inspection_manager.get_inspection_image(2)
        data  = self.main_operator.inspection_manager.get_inspection_data(2)

        if image is None:
            show_message("No Image")
            return

        if data is None:
            data = "No Data"

        self.update_ui_spot_image(image)
        self.update_ui_hole_inspection_result(data)

    def run_event_position3(self):
        image = self.main_operator.inspection_manager.get_inspection_image(3)
        data  = self.main_operator.inspection_manager.get_inspection_data(3)

        if image is None:
            show_message("No Image")
            return

        if data is None:
            data = "No Data"

        self.update_ui_spot_image_with_text(image, data)

    # VIP MODE
    def toggle_vip_mode(self):
        # check lease and power
        connection = self.main_operator.process_manager.check_spot_connection()
        if not connection:
            show_message("Check SPOT Lease and Power.")
            return

        if DefineGlobal.PROCESS_THREAD_IS_RUNNING:
            show_message("Check system mode. Should be manual mode.")
            return

        DefineGlobal.MODE_VIP = not DefineGlobal.MODE_VIP
        if DefineGlobal.MODE_VIP:
            self.header_widget.btn_toggle_vip_mode.setText("AUTO WALK")
            self.main_operator.run_start_full_demo()
        else:
            self.header_widget.btn_toggle_vip_mode.setText(" ")
            self.main_operator.run_stop_full_demo()

    # BODY ADMIN SETTINGS
    def run_capture_rgb(self):
        if not self.body_widget.body_admin_widget.page4.cbx_capture_live.isChecked():
            # self.capture_rgb_thread.capture_rgb()
            image = self.main_operator.spot_capture_bgr()
            gview = self.body_widget.body_admin_widget.page4.spot_image_view
            gview.set_image(image)
            return

        button = self.body_widget.body_admin_widget.page4.btn_capture_rgb
        button.setFont(QFont("현대하모니 M", 12))
        # Capture Thread 가 실행중인 경우
        if self.main_operator.capture_rgb_thread.isRunning():
            self.main_operator.capture_rgb_thread.stop()
            button.setProperty("running", False)
            button.setText("Capture")

        else:
            self.main_operator.capture_rgb_thread.start()
            button.setProperty("running", True)
            button.setText("STOP")

        button.style().unpolish(button)
        button.style().polish(button)

    # FOOTER SETTINGS
    def run_spot_docking_callback(self):
        # RUN DOCKING
        result = util_functions.show_confirm_box(text=f"SPOT DOCKING?")

        if result == QMessageBox.Yes:
            self.main_operator.docking()
        else:
            self.body_widget.body_display_widget.widget_hole_inspection_buttons.setEnabled(False)
            self.body_widget.body_display_widget.hole_inspection_button_disabled()

    def run_toggle_estop_auth_callback(self):
        # TODO: TOGGLE ESTOP AUTH FUNCTION
        text = "ARE YOU SURE TOGGLE SPOT E-STOP AUTHORITY?"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            self.main_operator.toggle_estop()

    def run_estop(self):
        self.main_operator.run_estop()

    def run_release_estop(self):
        self.main_operator.run_release_estop()

    def run_send_ng_confirm(self):
        if not self.main_operator.agv_no:
            show_message(text="AGV NO is empty.")
            return

        result = util_functions.show_confirm_box(text=f"Are you sure NG Confirm?\nAGV NO: {self.main_operator.agv_no}")

        if result == QMessageBox.Yes:
            write_result = self.main_operator.send_ng_confirm()
            if write_result:
                show_message(text="Send Complete.")
            else:
                show_message(text="Send Fail.")

    def run_send_work_complete(self):
        result = util_functions.show_confirm_box(text=f"Are you sure Work Complete?")

        if result == QMessageBox.Yes:
            write_result = self.main_operator.send_work_complete()
            if write_result:
                show_message(text="Send Complete.")
            else:
                show_message(text="Send Fail.")

    def run_send_by_pass(self):
        self.stylesheet_on = """
                font-family: '현대하모니 L';
                color: white;
                background-color: lime;
                padding: 16px;
                font-size: 16px;
                border-radius: 4px;
            """

        self.stylesheet_off = """
                font-family: '현대하모니 L';
                color: white;
                background-color: red;
                padding: 16px;
                font-size: 16px;
                border-radius: 4px;
            """

        write_result = self.main_operator.send_by_pass_mode()
        if write_result:
            if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
                tag_name = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON
            else:
                tag_name = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON

            if DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                self.footer_widget.btn_toggle_by_pass.setText("MANUAL\nBY-PASS ON")
                self.footer_widget.btn_toggle_by_pass.setStyleSheet(self.stylesheet_on)
                self.main_operator.run_send_signal_on(tag_name)
            else:
                self.footer_widget.btn_toggle_by_pass.setText("MANUAL\nBY-PASS OFF")
                self.footer_widget.btn_toggle_by_pass.setStyleSheet(self.stylesheet_off)
                self.main_operator.run_send_signal_off(tag_name)
        else:
            show_message(text="FAIL.\nCHECK THE OPC CONNECTION")

    def run_footer_toggle_power(self):
        text = "ARE YOU SURE TOGGLE SPOT POWER?"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            if self.main_operator.spot_robot.is_connected:
                self.main_operator.toggle_power()
            else:
                util_functions.show_message(text="spot is disconnected.")

    def run_footer_toggle_lease(self):
        text = "ARE YOU SURE TOGGLE SPOT LEASE?"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            self.main_operator.toggle_lease()

    def run_footer_localize(self):
        text = "Try to localize here?"
        result = util_functions.show_confirm_box(text=text)

        if result == QMessageBox.Yes:
            is_localized = self.main_operator.try_localize()
            if is_localized:
                message = "Localized."
            else:
                message = "Robot navigation is lost. Check the navigation map or move via tablet."

            util_functions.show_message(text=message)

    # PROCESS THREAD EVENTS
    def update_ui_bypass_button(self, bypass_signal):
        if bypass_signal:
            self.footer_widget.ui_update_bypass_on()
        else:
            self.footer_widget.ui_update_bypass_off()

    @staticmethod
    def handle_toggle_button_clicked(button: QPushButton, text="STOP"):
        color = QColor("#E74C3C")
        background_color = QColor("#969696")
        button.setStyleSheet(
            "color: {0}; background-color: {1};".format(color.name(), background_color.name())
        )

        button.setText(text)

    @staticmethod
    def handle_toggle_button_unclicked(button, text="RUN"):
        button.setStyleSheet(
            "color: #eff0f1; \
             background-color: rgb(32, 32, 32);"
        )

        button.setText(text)

    def initTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimestamp)
        self.timer.start(1000)  # 1초마다 타임스탬프 업데이트

    def updateTimestamp(self):
        current_time = QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
        self.header_widget.timestamp_label.setText(current_time)

    def closeEvent(self, event):
        close = QMessageBox()
        close.resize(1080, 720)
        close.setWindowFlags(Qt.WindowStaysOnTopHint)
        close.setIcon(QMessageBox.Icon.Critical)
        close.setWindowTitle("Alarm")
        close.setText("Exit the Program?")
        close.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        close = close.exec()
        if close == QMessageBox.Yes:
            util_functions.show_message(text="BY-PASS will be turned on automatically not to block the AGV circulation.")

            if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
                self.main_operator.run_send_signal_on(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON)
                self.main_operator.run_send_signal_on(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP)
            else:
                self.main_operator.run_send_signal_on(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON)
                self.main_operator.run_send_signal_on(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP)

            self.timer.stop()

            # self.body_widget.body_admin_widget.page8.quit()

            if self.main_operator.status_thread and self.main_operator.status_thread.isRunning():
                self.main_operator.status_thread.stop()
                self.main_operator.status_thread.wait()

            if self.main_operator.process_manager.isRunning():
                self.main_operator.process_manager.stop()

            # self.body_widget.body_admin_widget.page5.navigation_thread.stop()
            self.body_widget.body_admin_widget.page5.midnight_timer.stop()
            self.main_operator.opc_client.thread_receive_data.stop()
            self.main_operator.work_status_update_thread.stop()
            self.main_operator.opc_client.disconnect()
            # self.main_operator.spot_robot.update_task_timer.stop()

            event.accept()
        else:
            event.ignore()
