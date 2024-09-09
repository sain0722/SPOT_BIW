import threading
from datetime import datetime

from PySide6.QtCore import QThread, Signal, QMutex
import time

from bosdyn.client.graph_nav import RobotLostError

import DefineGlobal
from Thread.HoleInspectionProcessThread import HoleInspectionProcess
from Thread.QRCodeProcessThread import QRCodeProcess
from communication.OPC.opc_client import BIWOPCUAClient
from main_operator import MainOperator
from biw_utils import util_functions


class ProcessThread(QThread):
    completed = Signal()

    bypass_signal = Signal(bool)

    def __init__(self, main_operator: MainOperator, opc_client: BIWOPCUAClient):
        super().__init__()
        self.main_operator = main_operator
        self.opc_client = opc_client

        self.set_tag_name()

        self.process1_thread = QRCodeProcess(self.main_operator, "1")
        self.process2_thread = HoleInspectionProcess(self.main_operator, "2")
        self.process3_thread = QRCodeProcess(self.main_operator, "3")

        self.process1_thread.read_success.connect(self.on_progress1_read_success)
        self.process1_thread.read_fail.connect(self.on_progress1_read_fail)

        self.process2_thread.completed.connect(self.on_progress2_completed)

        self.process3_thread.read_success.connect(self.on_progress3_read_success)
        self.process3_thread.read_fail.connect(self.on_progress3_read_fail)

        self.process1_thread.process_error.connect(self.on_progress1_error_occurred)
        self.process2_thread.process_error.connect(self.on_progress2_error_occurred)
        self.process3_thread.process_error.connect(self.on_progress3_error_occurred)

        # self.m_comm_plc_client = OpcClient()
        # self.m_comm_plc_client.SetReadDataCallback(self.RecvPlcData)
        # self.m_comm_plc_client.connect("1asd")
        self.list_remote_data = []
        self.list_plc_data = []
        self.mutex = QMutex()

        self.running = True

        self.debug = False
        # 1. 정위치신호
        self.agv_pos_ok = False
        # 2. 작업완료 신호
        # 3. 도크 충전시 바이패스

    def run(self):
        print("Process Thread Start")
        while self.running:
            try:
                print("Process Thread Running...")
                # 0. Program Running 모드 체크
                if not DefineGlobal.PROCESS_THREAD_IS_RUNNING:
                    time.sleep(.5)
                    continue

                # 0. OPC CONNECT 체크
                if not self.check_opc_connection():
                    time.sleep(.1)
                    continue

                # 0. SPOT status check
                # print(f"[{datetime.now()}] Check Spot Connection.")
                if not self.check_spot_connection():
                    # TODO: NOTICE SPOT STATUS TO USER. (etc NEED POWER-ON, NEED LEASE, NEED E-STOP AUTHORITY..)
                    # TODO: TRY RECONNECT.
                    if not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                        self.try_spot_reset()
                    time.sleep(.1)
                    continue

                if self.is_battery_low(DefineGlobal.BATTERY_LOW_THRESHOLD):
                    # If Spot is not charging, go to dock and set bypass
                    if not self.main_operator.confirm_spot_is_charging():
                        self.main_operator.write_log(f"Battery Low. SET BY PASS AND GO TO DOCK.")
                        self.by_pass_on(is_docking=True)

                # Check only SPOT is charging.
                if self.is_battery_enough(DefineGlobal.BATTERY_ENOUGH_THRESHOLD):
                    # If Spot is charged enough, wait the agv signal.
                    # by_pass off.
                    if self.main_operator.spot_robot.spot_is_charging() and self.main_operator.spot_robot.motors_powered:
                        self.by_pass_off()
                        self.move_spot_home_position()
                        self.main_operator.write_log(f"Battery is charged about {DefineGlobal.BATTERY_ENOUGH_THRESHOLD}%. OFF BYPASS MODE AND WAIT THE AGV.")

                # 0. CHECK BY-PASS MODE
                if DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                    # TODO: 만약, SPOT이 충전중이 아니라면, Docking 하고 나서 by-pass on.
                    # ENTER THE BY PASS MODE, CHECK
                    if not self.receive_agv_arrival_signal():
                        continue

                    self.by_pass_on()

                    time.sleep(.1)
                    continue

                # 0. Check Auto BY-PASS
                if not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                    # 0. Check Status THREAD IS RUNNING?
                    if not DefineGlobal.CURRENT_WORK_COMPLETE_STATUS:
                        # 1. AGV 정위치 도착 신호 수신
                        # print(f"[{datetime.now()}] Waiting for Position Arrival Signal...")
                        if not self.receive_agv_arrival_signal():
                            time.sleep(0.1)
                            continue

                        # self.wait_for_signal('S600_AGV_O_POS_OK')
                        # self.wait_for_signal(DefineGlobal)

                    if not DefineGlobal.CURRENT_WORK_COMPLETE_STATUS:
                        # Delete previous data memory
                        self.main_operator.inspection_manager.clear()

                        # 2. AGV 진입 OK / 차종 정보 수신 확인
                        if not self.check_body_type():
                            print(f"[{datetime.now()}] Unsupported Body Type.")

                            # SEND WORK COMPLETE
                            self.send_signal(self.WORK_COMP_TAG)

                            # WAIT AGV OUT
                            agv_out = self.wait_for_agv_out()
                            # 6. AGV OUT. Work Complete. Clear data
                            if agv_out:
                                print(f"[{datetime.now()}] RECEIVE AGV OUT SIGNAL. CLEAR DATA")
                                self.clear_data()

                            time.sleep(1)
                            continue

                        # Move SPOT to HOME Position
                        print(f"[{datetime.now()}] SPOT Move to Home Position.")

                        if self.move_spot_home_position():
                            print(f"[{datetime.now()}] Complete move to Home Position.")
                        else:
                            print(f"[{datetime.now()}] Error Raised. Robot Lost?")
                            continue

                        print(f"[{datetime.now()}] Send Signal {DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_HOME_POSI}.")
                        print(f"[{datetime.now()}] Send Signal {DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_HOME_POSI}.")
                        self.send_signal(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_HOME_POSI)
                        self.send_signal(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_HOME_POSI)

                    if not DefineGlobal.CURRENT_WORK_COMPLETE_STATUS:
                        # 3. SPOT 작업 진행.
                        print(f"[{datetime.now()}] RUN PROCESS")
                        self.run_biw_process()

                    if not DefineGlobal.CURRENT_WORK_COMPLETE_STATUS:
                        # Move SPOT to COMPLETE Position
                        self.move_spot_complete_position()

                        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
                            tag_name = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP
                        else:
                            tag_name = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP

                        # 4. (If NG occurred, Wait User Command.)
                        if DefineGlobal.MODE_USER_CONFIRM:
                            if self.main_operator.hole_ng_occurred:
                                self.wait_user_command()
                        else:
                            # 4-1. AUTO PASS MODE
                            self.send_signal(tag_name)

                        # 5. Move SPOT to HOME Position
                        self.move_spot_home_position()

                        # 6. AGV OUT 신호 수신
                        agv_out = self.wait_for_agv_out()

                        # 7. AGV OUT. Work Complete. Clear data
                        if agv_out:
                            print(f"[{datetime.now()}] RECEIVE AGV OUT SIGNAL. CLEAR DATA")
                            self.clear_data()

                    if DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                        # 8. Move SPOT to HOME Position directly if by-pass mode.
                        if DefineGlobal.CURRENT_WORK_STATUS != DefineGlobal.WORK_STATUS.HOME:
                            print(f"[{datetime.now()}] BY PASS MODE. GO HOME POSITION.")
                            self.move_spot_home_position()

                        # 9. Wait AGV OUT SIGNAL.
                        agv_out = self.wait_for_agv_out()

                        # 10. AGV OUT. Work Complete. Clear data
                        if agv_out:
                            print(f"[{datetime.now()}] RECEIVE AGV OUT SIGNAL IN BY PASS MODE. CLEAR DATA")
                            self.clear_data()

                    # 8. Wait
                    # self.opc_client.write_node_id(DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_POS_OK, False)
                    # time.sleep(3)

                time.sleep(.1)

            except Exception as e:
                print(f"[{datetime.now()}] ProcessThread.py - Exception Raised. {e}")

    def stop(self):
        DefineGlobal.PROCESS_THREAD_IS_RUNNING = False
        self.running = False
        self.quit()
        self.wait()

    def set_tag_name(self):
        self.AGV_POS_OK_TAG = DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_POS_OK
        self.AGV_POS_OUT_TAG = DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_Workcompl_Feedback

        if util_functions.is_position_RH():
            OPC_TAG = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA
            self.WORK_COMP_TAG = OPC_TAG.S600_SPOT_RB1_I_LAST_WORK_COMP
            self.WORK_1ST_COMP_TAG = OPC_TAG.S600_SPOT_RB1_I_1ST_WORK_COMP
            self.WORK_2ND_COMP_TAG = OPC_TAG.S600_SPOT_RB1_I_2ND_WORK_COMP
            self.WORK_3RD_COMP_TAG = OPC_TAG.S600_SPOT_RB1_I_3RD_WORK_COMP

            self.WORK_1ST_ERR_TAG = OPC_TAG.S600_SPOT_RB1_I_CHK1_ERR
            self.WORK_2ND_ERR_TAG = OPC_TAG.S600_SPOT_RB1_I_CHK2_ERR
            self.WORK_3RD_ERR_TAG = OPC_TAG.S600_SPOT_RB1_I_CHK3_ERR

            self.BATTERY_LOW_TAG = OPC_TAG.S600_SPOT_RB1_I_BATTERY_LOW
            self.BY_PASS_TAG = OPC_TAG.S600_SPOT_RB1_I_BYPASS_ON

        else:
            OPC_TAG = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA
            self.WORK_COMP_TAG = OPC_TAG.S600_SPOT_RB2_I_LAST_WORK_COMP
            self.WORK_1ST_COMP_TAG = OPC_TAG.S600_SPOT_RB2_I_1ST_WORK_COMP
            self.WORK_2ND_COMP_TAG = OPC_TAG.S600_SPOT_RB2_I_2ND_WORK_COMP
            self.WORK_3RD_COMP_TAG = OPC_TAG.S600_SPOT_RB2_I_3RD_WORK_COMP

            self.WORK_1ST_ERR_TAG = OPC_TAG.S600_SPOT_RB2_I_CHK1_ERR
            self.WORK_2ND_ERR_TAG = OPC_TAG.S600_SPOT_RB2_I_CHK2_ERR
            self.WORK_3RD_ERR_TAG = OPC_TAG.S600_SPOT_RB2_I_CHK3_ERR

            self.BATTERY_LOW_TAG = OPC_TAG.S600_SPOT_RB2_I_BATTERY_LOW
            self.BY_PASS_TAG = OPC_TAG.S600_SPOT_RB2_I_BYPASS_ON

    def receive_agv_arrival_signal(self):
        if self.opc_client.read_node_id(DefineGlobal.OPC_AGV_I_TAG.S600_AGV_I_POS_OK):
            # self.main_operator.write_log("AGV POS OK RECEIVE.")
            return True
        return False

    def check_opc_connection(self):
        return self.opc_client.connected

    def check_spot_connection(self):
        # TODO: SPOT STATUS CHECK
        spot_connected = True
        if not self.main_operator.spot_robot.robot:
            return False

        # Power  ON
        # Lease  ON
        # E-stop ON

        spot_connected &= self.main_operator.spot_robot.motors_powered
        spot_connected &= self.main_operator.spot_robot.has_robot_control

        return spot_connected

    def try_spot_reset(self):
        # TODO: GET ESTOP AUTHORITY
        # TODO: There are many exceptional situations
        pass
        # if self.main_operator.spot_robot.robot_is_power_off():
        #     self.main_operator.toggle_power()

        # if not self.main_operator.spot_robot.has_robot_control:
        #     self.main_operator.toggle_lease()

    def check_body_type(self):
        body_type = self.main_operator.body_type

        if body_type == DefineGlobal.BODY_TYPE.NE:
            # setting NE
            self.main_operator.change_body_type_setting(body_type)
            return True

        if body_type == DefineGlobal.BODY_TYPE.ME:
            # setting ME
            self.main_operator.change_body_type_setting(body_type)
            return True

        return False

    def move_spot_home_position(self):
        # home_waypoint = self.main_operator.spot_manager.get_waypoint_home()

        # Home waypoint is Position #1 ?
        # Default is "HOME" Waypoint.
        # if "NE" Body, we set home to position 1

        DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.HOME
        home_waypoint = self.main_operator.spot_manager.get_waypoint_home()

        if DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.NE:
            home_waypoint = self.main_operator.spot_manager.get_waypoint("1")

        nav_manager = self.main_operator.spot_robot.robot_graphnav_manager
        try:
            navigate_result = nav_manager.navigate_to(home_waypoint)
            if navigate_result:
                if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
                    self.send_signal(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_HOME_POSI)
                else:
                    self.send_signal(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_HOME_POSI)

            return navigate_result

        except RobotLostError as e:
            print(f"[{datetime.now()}] SpotGraphNav.py - Robot Lost?")
            print(e)
            return False

        except Exception as e:
            print(f"[{datetime.now()}] ProcessThread -> SpotGraphNav.py - Exception Raised.")
            print(e)
            return False

    def run_biw_process(self):
        # Camera Resolution Check.
        self.main_operator.spot_robot.robot_camera_param_manager.set_resolution(s_resolution="3840x2160")

        # BODY TYPE CHECK.
        if DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.NE:
            self.run_biw_process_body_NE()
        elif DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.ME:
            self.run_biw_process_body_ME()

    def run_biw_process_body_NE(self):
        st_time = time.time()

        # @Todo: 각 프로세스 ERROR 상황 처리
        DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.POSITION1
        print(f"[{datetime.now()}] RUN PROCESS 1")
        if not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
            self.run_thread(self.process1_thread)

        DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.POSITION2
        print(f"[{datetime.now()}] RUN PROCESS 2")
        if not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
            self.run_thread(self.process2_thread)

        DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.POSITION3
        print(f"[{datetime.now()}] RUN PROCESS 3")
        if not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
            self.run_thread(self.process3_thread)

        end_time = time.time()
        elapsed_time = end_time - st_time

        print(f"[{datetime.now()}] Progress Elapsed Time : {elapsed_time}s")
        self.main_operator.write_cycle_time(elapsed_time)

    def run_biw_process_body_ME(self):
        st_time = time.time()

        # @Todo: 각 프로세스 ERROR 상황 처리
        DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.POSITION1
        print(f"[{datetime.now()}] RUN PROCESS 1")
        if not DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
            self.run_thread(self.process1_thread)

        end_time = time.time()
        elapsed_time = end_time - st_time

        print(f"[{datetime.now()}] Progress Elapsed Time : {elapsed_time}s")
        self.main_operator.write_cycle_time(elapsed_time)

    def move_spot_complete_position(self):
        complete_waypoint = self.main_operator.spot_manager.get_waypoint_complete()
        nav_manager = self.main_operator.spot_robot.robot_graphnav_manager
        nav_manager.navigate_to(complete_waypoint)

        # 4. Send Work Complete Signal
        DefineGlobal.CURRENT_WORK_STATUS = DefineGlobal.WORK_STATUS.COMPLETE

        # tag_name_rb1 = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP
        # tag_name_rb2 = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP
        # self.send_signal(tag_name_rb1)
        # self.send_signal(tag_name_rb2)
        # print(f"[{datetime.now()}] SEND SIGNAL: {tag_name_rb1}")
        # print(f"[{datetime.now()}] SEND SIGNAL: {tag_name_rb2}")

        # if DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND:
        #     print(f"[{datetime.now()}] WAIT USER INPUT. DO NOT SEND WORK COMPLETE.")
        #     return

        if not DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND:
            self.send_signal(self.WORK_COMP_TAG)
            # DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = True
            print(f"[{datetime.now()}] MOVE COMPLETE POSITION. SEND SIGNAL: {self.WORK_COMP_TAG}")

    def wait_user_command(self):
        DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = True
        while DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND:
            print(f"[{datetime.now()}] WAIT USER COMMAND...")
            time.sleep(1)
            if DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                break

        self.main_operator.hole_ng_occurred = False
        DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = False
        return True

    def wait_for_agv_out(self):
        while DefineGlobal.PROCESS_THREAD_IS_RUNNING:
            if self.opc_client.read_node_id(self.AGV_POS_OUT_TAG):
                return True

            if DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
                return False

            time.sleep(0.5)
        return False

    def clear_data(self):
        # S600_SPOT_RB1_I_1ST_WORK_COMP
        # S600_SPOT_RB1_I_2ND_WORK_COMP
        # S600_SPOT_RB1_I_3RD_WORK_COMP
        # S600_SPOT_RB1_I_EM_STOP
        # S600_SPOT_RB1_I_HOME_POSI
        # S600_SPOT_RB1_I_LAST_WORK_COMP
        if util_functions.is_position_RH():
            total_tags = [
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_1ST_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_2ND_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_3RD_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_CHK1_ERR,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_CHK2_ERR,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_CHK3_ERR,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_TOTAL_ERR,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_EM_STOP,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_HOME_POSI,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON
            ]
        else:
            total_tags = [
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_1ST_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_2ND_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_3RD_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_CHK1_ERR,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_CHK2_ERR,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_CHK3_ERR,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_TOTAL_ERR,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_EM_STOP,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_HOME_POSI,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP,
                DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON
            ]

        for tag_name in total_tags:
            self.send_signal_off(tag_name)

        self.main_operator.event_update_hole_inspection_result

    def run_thread(self, thread: QThread):
        st_time = time.time()
        thread.start()
        thread.running = True
        thread.wait()

        end_time = time.time()
        elapsed_time = end_time - st_time
        elapsed_log = f"#{thread.position} Elapsed Time : {elapsed_time}s"
        # self.main_window.write_log(elapsed_log)
        print(elapsed_log)

    def run_process_1(self):
        self.process1_thread.start()

    def run_process_2(self):
        # widget_hole_inspection = self.main_window.widget_setting_page.widget_hole_inspection
        # rule_threshold, focus_absolute = widget_hole_inspection.get_hole_inspection_parameter()
        # self.process2_thread.set_parameter(rule_threshold, focus_absolute)
        self.process2_thread.start()

    def run_process_2_teaching(self):
        self.process2_thread.run_for_teaching()

    def run_process_3(self):
        self.process3_thread.start()

    def run_process_full(self):
        thread_biw_process = threading.Thread(target=self.run_biw_process)
        thread_biw_process.start()

    def on_progress1_completed(self):
        # Send Signal Work 1 Complete.
        self.send_signal(self.WORK_1ST_COMP_TAG)

    def on_progress1_read_success(self, image, qr_image, qr_context):
        self.send_signal(self.WORK_1ST_COMP_TAG)

        message = f"QR Code Reading: \n{qr_context}"
        self.main_operator.write_qr_result(message)
        self.main_operator.update_spot_image_with_text(image, qr_context)

        # Save Inspection Data to InspectionDataManager
        self.main_operator.inspection_manager.set_position1_data(image, qr_context)

    def on_progress1_read_fail(self, image, text):
        # 1ST WORK ERROR?
        self.send_signal(self.WORK_1ST_COMP_TAG)

        message = f"QR Code Reading: \n{text}"
        self.main_operator.write_qr_result(message)
        self.main_operator.update_spot_image_with_text(image, text)

        # Save Inspection Data to InspectionDataManager
        self.main_operator.inspection_manager.set_position1_data(image, text)

    def on_progress2_completed(self, roi_image, inspection_result: bool):
        # Send Signal Work 2 Complete.
        self.send_signal(self.WORK_2ND_COMP_TAG)

        # DISPLAY INSPECTION RESULT
        self.main_operator.update_hole_inspection_result(inspection_result)

        # 차종과 다른 결과일 경우
        # 차종데이터:
        hole_spec_type = self.main_operator.hole_spec_type

        # 1) Hole 검사 결과 OK일 경우
        if inspection_result:
            has_hole_spec = hole_spec_type == DefineGlobal.HOLE_TYPE.HOLE

        # graphic_view = self.main_operator.main_window.body_widget.body_display_widget.image_gview
        self.main_operator.update_spot_image(roi_image)
        # self.main_operator.update_spot_image_with_text(roi_image, graphic_view, result)

        # Save Inspection Data to InspectionDataManager
        self.main_operator.inspection_manager.set_position2_data(roi_image, inspection_result)

    def on_progress3_read_success(self, image, qr_image, qr_context):
        self.send_signal(self.WORK_3RD_COMP_TAG)

        message = f"QR Code Reading: \n{qr_context}"
        self.main_operator.write_qr_result(message)
        self.main_operator.update_spot_image_with_text(image, qr_context)
        # TODO: QR IMAGE DISPLAY

        # Save Inspection Data to InspectionDataManager
        self.main_operator.inspection_manager.set_position3_data(image, qr_context)

    def on_progress3_read_fail(self, image, text):
        # 3RD WORK ERROR?
        self.send_signal(self.WORK_3RD_COMP_TAG)

        message = f"QR Code Reading: \n{text}"
        self.main_operator.write_qr_result(message)
        self.main_operator.update_spot_image_with_text(image, text)

        # Save Inspection Data to InspectionDataManager
        self.main_operator.inspection_manager.set_position3_data(image, text)

    def on_progress1_error_occurred(self):
        # Send Signal Work 1 Error.
        self.send_signal(self.WORK_1ST_ERR_TAG)

    def on_progress2_error_occurred(self):
        # Send Signal Work 2 Error.
        self.send_signal(self.WORK_2ND_ERR_TAG)

    def on_progress3_error_occurred(self):
        # Send Signal Work 3 Error.
        self.send_signal(self.WORK_3RD_ERR_TAG)

    def is_battery_low(self, threshold) -> bool:
        battery_val = self.main_operator.spot_robot.get_battery_value()
        return battery_val <= threshold

    def is_battery_enough(self, threshold) -> bool:
        battery_val = self.main_operator.spot_robot.get_battery_value()
        return battery_val >= threshold

    def by_pass_on(self, is_docking=False):
        # TODO: Temporary RB1 RB2 total bypass
        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
            self.send_signal(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON)
            self.send_signal(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP)
        else:
            self.send_signal(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON)
            self.send_signal(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP)

        self.bypass_signal.emit(True)

        if is_docking:
            self.main_operator.docking()

    def by_pass_off(self):
        if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
            by_pass_tag_name = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON
            work_complete_tag_name = DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON
        else:
            by_pass_tag_name = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON
            work_complete_tag_name = DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP

        if self.opc_client.read_node_id(by_pass_tag_name):
            self.send_signal_off(by_pass_tag_name)
            self.send_signal_off(work_complete_tag_name)

        DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS = False
        self.bypass_signal.emit(False)

        # if DefineGlobal.SPOT_POSITION == DefineGlobal.BIW_POSITION.RH:
        #     self.send_signal_off(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_BYPASS_ON)
        #     self.send_signal_off(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP)
        # else:
        #     self.send_signal_off(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_BYPASS_ON)
        #     self.send_signal_off(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP)

    def send_signal(self, tag_name: str):
        self.opc_client.write_node_id(tag_name, True)

        if tag_name == DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP:
            if not DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND:
                DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = True

        if tag_name == DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP:
            if not DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND:
                DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = True

    def send_signal_off(self, tag_name: str):
        self.opc_client.write_node_id(tag_name, False)

        if tag_name == DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP:
            DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = False

        if tag_name == DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP:
            DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = False

    # def RecvPlcData(self, data: OpcClientReadData):
    #     """
    #     recv plc opc tag data,...
    #     """
    #     self.mutex.lock()
    #     self.list_plc_data.append(data)
    #     self.mutex.unlock()
