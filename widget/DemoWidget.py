import time
from threading import Thread

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QDialog, QHBoxLayout, QLineEdit, QLabel, QFormLayout, \
    QDoubleSpinBox, QSpinBox

from main_operator import MainOperator
from biw_utils import util_functions


class DemoDialog(QDialog):
    def __init__(self, main_operator):
        super().__init__()

        self.setWindowTitle("Demo Window")
        layout = QVBoxLayout()
        self.demo_widget = DemoWidget(main_operator)
        layout.addWidget(self.demo_widget)
        self.setLayout(layout)


class DemoWidget(QWidget):
    def __init__(self, main_operator: MainOperator):
        super().__init__()
        self.main_operator = main_operator
        self.data_acquisition_thread = DataAcquisitionThread(self.main_operator)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Position Home
        self.btn_move_home = QPushButton("Move Position Home")
        self.btn_move_home.clicked.connect(self.move_position_home)

        # Position 1
        self.btn_move_pos1 = QPushButton("Move Position 1")
        self.btn_arm_reach_pos1 = QPushButton("Arm Reach Position 1")
        self.btn_run_pos1 = QPushButton("Run Position 1")
        layout.addWidget(self.btn_move_pos1)
        layout.addWidget(self.btn_arm_reach_pos1)
        layout.addWidget(self.btn_run_pos1)

        # Position 2
        self.btn_move_pos2 = QPushButton("Move Position 2")

        flayout_setting = QFormLayout()
        self.lbl_robot_speed = QLabel("speed:")
        self.sbx_robot_speed = QDoubleSpinBox()
        self.sbx_robot_speed.setSingleStep(0.1)
        self.sbx_robot_speed.setMinimum(0)
        self.sbx_robot_speed.setMaximum(1.5)

        self.lbl_move_count = QLabel("move count:")
        self.sbx_move_count = QSpinBox()
        self.sbx_move_count.setSingleStep(1)
        self.sbx_move_count.setMaximum(20)

        flayout_setting.addRow(self.lbl_robot_speed, self.sbx_robot_speed)
        flayout_setting.addRow(self.lbl_move_count, self.sbx_move_count)

        self.btn_arm_reach_pos2 = QPushButton("Arm Reach Position 2")
        self.btn_arm_correct_pos2 = QPushButton("Arm Correct Position 2")
        self.btn_arm_teaching_pos2 = QPushButton("Arm Teaching Position 2")
        self.btn_run_pos2 = QPushButton("Run Position 2")
        layout.addWidget(self.btn_move_pos2)
        layout.addWidget(self.btn_arm_reach_pos2)
        layout.addWidget(self.btn_arm_teaching_pos2)
        layout.addLayout(flayout_setting)
        layout.addWidget(self.btn_arm_correct_pos2)
        layout.addWidget(self.btn_run_pos2)

        # Position 3
        self.btn_move_pos3 = QPushButton("Move Position 3")
        self.btn_arm_reach_pos3 = QPushButton("Arm Reach Position 3")
        self.btn_run_pos3 = QPushButton("Run Position 3")
        layout.addWidget(self.btn_move_pos3)
        layout.addWidget(self.btn_arm_reach_pos3)
        layout.addWidget(self.btn_run_pos3)

        self.btn_move_pos1.clicked.connect(self.move_position1)
        self.btn_move_pos2.clicked.connect(self.move_position2)
        self.btn_move_pos3.clicked.connect(self.move_position3)

        self.btn_arm_reach_pos1.clicked.connect(self.arm_reach_position1)
        self.btn_arm_reach_pos2.clicked.connect(self.arm_reach_position2)
        self.btn_arm_reach_pos3.clicked.connect(self.arm_reach_position3)
        self.btn_arm_correct_pos2.clicked.connect(self.arm_correct_position2)
        self.btn_arm_teaching_pos2.clicked.connect(self.run_position2_teaching_mode)

        self.btn_run_pos1.clicked.connect(self.run_position1)
        self.btn_run_pos2.clicked.connect(self.run_position2)
        self.btn_run_pos3.clicked.connect(self.run_position3)

        # Full Demo
        self.btn_run_demo = QPushButton("Run Full Demo")
        layout.addWidget(self.btn_run_demo)
        self.btn_run_demo.clicked.connect(self.run_full_demo)

        # Data Acq
        self.btn_run_position2_auto = QPushButton("RUN POSITION2 AUTO")
        layout.addWidget(self.btn_run_position2_auto)
        self.btn_run_position2_auto.clicked.connect(self.run_position2_thread)

        self.btn_go_home = QPushButton("Run Move to Home")
        self.btn_go_complete = QPushButton("Run Move to Complete")
        self.btn_go_home.clicked.connect(self.move_home)
        self.btn_go_complete.clicked.connect(self.move_complete)

        layout.addWidget(self.btn_go_home)
        layout.addWidget(self.btn_go_complete)

        # Depth Function Test
        self.btn_hand_depth_test = QPushButton("hand depth (distance)")
        self.btn_frontleft_depth_test = QPushButton("frontleft depth (distance)")
        self.btn_frontright_depth_test = QPushButton("frontright depth (distance)")

        self.lbl_min_distance = QLabel("distance")

        self.btn_opc_connect_test = QPushButton("opc connect")
        self.btn_opc_disconnect_test = QPushButton("opc disconnect")

        hlayout_opc_read = QHBoxLayout()
        hlayout_opc_read_path = QHBoxLayout()
        hlayout_opc_write = QHBoxLayout()
        self.line_edit_opc_read_tag = QLineEdit()
        self.line_edit_opc_read_tag_path = QLineEdit()
        self.line_edit_opc_write_tag = QLineEdit()
        self.line_edit_opc_write_value = QLineEdit()
        self.btn_opc_read_test = QPushButton("opc read (only tagname)")
        self.btn_opc_read_path_test = QPushButton("opc read (node path)")
        self.btn_opc_write_test = QPushButton("opc write")

        hlayout_opc_read.addWidget(self.line_edit_opc_read_tag)
        hlayout_opc_read.addWidget(self.btn_opc_read_test)

        hlayout_opc_read_path.addWidget(self.line_edit_opc_read_tag_path)
        hlayout_opc_read_path.addWidget(self.btn_opc_read_path_test)

        hlayout_opc_write.addWidget(self.line_edit_opc_write_tag)
        hlayout_opc_write.addWidget(self.line_edit_opc_write_value)
        hlayout_opc_write.addWidget(self.btn_opc_write_test)

        # layout.addWidget(self.btn_hand_depth_test)
        # layout.addWidget(self.btn_frontleft_depth_test)
        # layout.addWidget(self.btn_frontright_depth_test)
        # layout.addWidget(self.lbl_min_distance)
        # layout.addWidget(self.btn_opc_connect_test)
        # layout.addWidget(self.btn_opc_disconnect_test)
        # layout.addLayout(hlayout_opc_read)
        # layout.addLayout(hlayout_opc_read_path)
        # layout.addLayout(hlayout_opc_write)
        self.btn_hand_depth_test.clicked.connect(self.hand_depth_test)
        self.btn_frontleft_depth_test.clicked.connect(self.frontleft_depth_test)
        self.btn_frontright_depth_test.clicked.connect(self.frontright_depth_test)
        self.btn_opc_connect_test.clicked.connect(self.run_opc_connect)
        self.btn_opc_disconnect_test.clicked.connect(self.run_opc_disconnect)
        self.btn_opc_read_test.clicked.connect(self.run_opc_read_tag)
        self.btn_opc_read_path_test.clicked.connect(self.run_opc_read_tag_path)
        self.btn_opc_write_test.clicked.connect(self.run_opc_write_tag)

        self.setLayout(layout)

    def move_position_home(self):
        move_thread = Thread(target=self.main_operator.process_manager.move_spot_home_position)
        move_thread.start()
        print("move_position_home")

    def move_position(self, position):
        waypoint = self.main_operator.spot_manager.get_waypoint(position)

        move_thread = Thread(target=self.main_operator.run_move_to_waypoint, args=[waypoint])
        move_thread.start()
        print("move_position")

    def move_position1(self):
        self.move_position("1")

    def move_position2(self):
        waypoint1, waypoint2 = self.main_operator.spot_manager.get_hole_waypoint()
        move_thread = Thread(target=self.main_operator.run_move_to_waypoint, args=[waypoint1])
        move_thread.start()

    def move_position2_2(self):
        waypoint1, waypoint2 = self.main_operator.spot_manager.get_hole_waypoint()
        move_thread = Thread(target=self.main_operator.run_move_to_waypoint, args=[waypoint2])
        move_thread.start()

    def move_position3(self):
        self.move_position("3")

    def arm_reach_position1(self):
        arm_pose1 = self.main_operator.spot_manager.get_arm_setting("1")
        params = util_functions.read_spot_arm_position(arm_pose1)
        self.main_operator.spot_joint_move_manual(params)
        print("arm_reach_position1")

    def arm_reach_position2(self):
        arm_pose2 = self.main_operator.spot_manager.get_arm_setting("2")
        params = util_functions.read_spot_arm_position(arm_pose2)
        self.main_operator.spot_joint_move_manual(params)
        print("arm_reach_position2")

    def arm_reach_position3(self):
        arm_pose3 = self.main_operator.spot_manager.get_arm_setting("3")
        params = util_functions.read_spot_arm_position(arm_pose3)
        self.main_operator.spot_joint_move_manual(params)
        print("arm_reach_position3")

    def arm_correct_position2(self):
        self.main_operator.run_arm_correction()
        print("arm_correct_position2")

    def move_forward_position2(self):
        self.main_operator.height_change(0.3)
        self.main_operator.spot_robot.robot_move_manager.VELOCITY_BASE_SPEED = self.sbx_robot_speed.value()

        for _ in range(self.sbx_move_count.value()):
            self.main_operator.spot_robot.robot_move_manager.move_forward()
            time.sleep(.05)

        self.main_operator.spot_robot.robot_move_manager.VELOCITY_BASE_SPEED = 0.6

    def run_position1(self):
        self.main_operator.process_manager.run_process_1()
        print("run_position1")

    def run_position2(self):
        print("run_position2 start")
        self.main_operator.process_manager.run_process_2()
        print("run_position2 end")

    def run_position2_thread(self):
        if self.data_acquisition_thread.isRunning():
            self.data_acquisition_thread.stop()
            self.btn_run_position2_auto.setText("RUN POSITION2 AUTO")
        else:
            self.data_acquisition_thread.start()
            self.btn_run_position2_auto.setText("STOP")

    def run_position2_teaching_mode(self):
        self.main_operator.process_manager.run_process_2_teaching()
        print("run_position2_teaching")

    def run_position3(self):
        self.main_operator.process_manager.run_process_3()
        print("run_position3")

    def run_full_demo(self):
        self.main_operator.process_manager.run_process_full()
        print("run_full_demo")

    def move_home(self):
        waypoint_home = self.main_operator.spot_manager.get_waypoint_home()
        self.main_operator.run_move_to_waypoint(waypoint_home)

    def move_complete(self):
        waypoint_complete = self.main_operator.spot_manager.get_waypoint_complete()
        self.main_operator.run_move_to_waypoint(waypoint_complete)

    def hand_depth_test(self):
        min_distance = self.main_operator.hand_depth_test()
        self.lbl_min_distance.setText(str(min_distance))

    def frontleft_depth_test(self):
        min_distance = self.main_operator.front_left_depth_test()
        self.lbl_min_distance.setText(str(min_distance))

    def frontright_depth_test(self):
        min_distance = self.main_operator.front_right_depth_test()
        self.lbl_min_distance.setText(str(min_distance))

    def run_opc_connect(self):
        self.main_operator.opc_connect()

    def run_opc_disconnect(self):
        self.main_operator.opc_disconnect()

    def run_opc_read_tag(self):
        tag = self.line_edit_opc_read_tag.text()
        self.main_operator.opc_tag_read_test(tag)

    def run_opc_read_tag_path(self):
        path = self.line_edit_opc_read_tag_path.text()
        self.main_operator.opc_tag_read_path_test(path)

    def run_opc_write_tag(self):
        tag = self.line_edit_opc_write_tag.text()
        value = self.line_edit_opc_write_value.text()
        self.main_operator.opc_tag_write_test(tag, value)


class DataAcquisitionThread(QThread):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.is_running = True

    def run(self):
        while self.is_running:
            self.main_operator.process_manager.run_thread(self.main_operator.process_manager.process2_thread)
            print("run_position2")

            waypoint_home = self.main_operator.spot_manager.get_waypoint_home()
            self.main_operator.run_move_to_waypoint(waypoint_home)

            time.sleep(.5)

    def stop(self):
        self.is_running = False
