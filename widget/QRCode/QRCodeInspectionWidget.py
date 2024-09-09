import json

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, \
    QMessageBox, QDoubleSpinBox, QScrollArea, QFileDialog, QFormLayout

from PySide6.QtCore import Qt

from main_operator import MainOperator
from biw_utils import qr_functions, util_functions
from biw_utils.decorators import user_input_decorator, spot_connection_check
from widget.common.ArmPositionSettingWidget import ArmPositionSettingWidget
from widget.common.GraphicView import GraphicView


class QRCodeInspectionWidget(QWidget):
    def __init__(self, main_operator: MainOperator, position: str):
        super().__init__()
        self.main_operator = main_operator
        self.position = position
        self.initUI()
        self.load_setting()

    def initUI(self):
        self.main_layout = QVBoxLayout()

        self.hlayout_main = QHBoxLayout()
        self.vlayout_left = QVBoxLayout()
        self.vlayout_right = QVBoxLayout()

        flayout_spot_setting = QFormLayout()
        self.lbl_inspection_settings = QLabel("Inspection Settings")
        self.vlayout_inspection_settings = QVBoxLayout()

        self.hlayout_waypoint = QHBoxLayout()
        self.lbl_inspection_waypoint = QLabel("Waypoint")
        self.cbx_inspection_waypoint = QComboBox()
        self.cbx_inspection_waypoint.setObjectName("combobox")

        self.hlayout_waypoint.addWidget(self.lbl_inspection_waypoint)
        # self.hlayout_position.addWidget(self.line_edit_inspection_position)
        self.hlayout_waypoint.addWidget(self.cbx_inspection_waypoint)
        self.hlayout_waypoint.setStretch(0, 1)
        self.hlayout_waypoint.setStretch(1, 1)

        self.hlayout_resolution = QHBoxLayout()
        self.lbl_resolution = QLabel("Resolution")
        self.cbx_resolution = QComboBox()
        self.cbx_resolution.setObjectName("combobox")

        self.cbx_resolution.addItem("640x480")
        self.cbx_resolution.addItem("1280x720")
        self.cbx_resolution.addItem("1920x1080")
        self.cbx_resolution.addItem("3840x2160")
        self.cbx_resolution.addItem("4096x2160")
        self.cbx_resolution.addItem("4208x3120")

        self.hlayout_resolution.addWidget(self.lbl_resolution)
        self.hlayout_resolution.addWidget(self.cbx_resolution)
        self.hlayout_resolution.setStretch(0, 1)
        self.hlayout_resolution.setStretch(1, 1)

        self.hlayout_duration_time = QHBoxLayout()
        self.lbl_duration_time = QLabel("duration_time")
        self.sbx_duration_time = QSpinBox()
        self.sbx_duration_time.setMinimum(0)
        self.sbx_duration_time.setMaximum(5)

        self.hlayout_duration_time.addWidget(self.lbl_duration_time)
        self.hlayout_duration_time.addWidget(self.sbx_duration_time)

        self.hlayout_focus_absolute = QHBoxLayout()
        self.lbl_focus_absolute = QLabel("focus absolute")
        self.sbx_focus_absolute = QDoubleSpinBox()
        self.sbx_focus_absolute.setDecimals(2)
        self.sbx_focus_absolute.setMinimum(0)
        self.sbx_focus_absolute.setMaximum(1)
        self.sbx_focus_absolute.setSingleStep(0.01)

        self.hlayout_focus_absolute.addWidget(self.lbl_focus_absolute)
        self.hlayout_focus_absolute.addWidget(self.sbx_focus_absolute)

        self.hlayout_apply_button = QHBoxLayout()
        self.btn_load_settings = QPushButton("Load")
        self.btn_apply_settings = QPushButton("Apply")

        self.btn_load_settings.clicked.connect(self.load_setting)
        self.btn_apply_settings.clicked.connect(self.apply_setting)

        self.hlayout_apply_button.addStretch(1)
        self.hlayout_apply_button.addWidget(self.btn_load_settings)
        self.hlayout_apply_button.addWidget(self.btn_apply_settings)

        self.vlayout_inspection_settings.addLayout(self.hlayout_waypoint)
        self.vlayout_inspection_settings.addLayout(self.hlayout_resolution)
        # self.vlayout_inspection_settings.addLayout(self.hlayout_duration_time)
        self.vlayout_inspection_settings.addLayout(self.hlayout_focus_absolute)
        self.vlayout_inspection_settings.addLayout(self.hlayout_apply_button)

        self.vlayout_left.addLayout(self.vlayout_inspection_settings)

        self.arm_teaching_widget = ArmPositionSettingWidget()
        self.define_arm_teaching_events()

        self.vlayout_left.addWidget(self.arm_teaching_widget)

        # Manual QR Code Read
        self.btn_read_qr_image = QPushButton("READ")
        self.btn_read_qr_image.clicked.connect(self.read_qr_image)
        self.vlayout_left.addWidget(self.btn_read_qr_image)

        self.vlayout_left.addStretch(1)

        self.gview_image = GraphicView()
        self.gview_image.setObjectName("image")

        self.vlayout_right.addWidget(self.gview_image)

        self.hlayout_main.addLayout(self.vlayout_left)
        self.hlayout_main.addLayout(self.vlayout_right)

        self.hlayout_main.setStretch(0, 2)
        self.hlayout_main.setStretch(1, 5)

        self.main_layout.addLayout(self.hlayout_main)

        self.setLayout(self.main_layout)

    def load_setting(self):
        inspection_settings = self.main_operator.spot_manager.get_position_setting(self.position)

        waypoint = inspection_settings.get("waypoint", "-")
        resolution = inspection_settings.get("resolution", "-")
        arm_position = inspection_settings.get("arm_position", None)
        focus_absolute = inspection_settings.get("focus_absolute", 0)

        # Apply UI
        self.cbx_inspection_waypoint.setCurrentText(waypoint)
        self.cbx_resolution.setCurrentText(resolution)
        self.sbx_focus_absolute.setValue(focus_absolute)
        if arm_position is None:
            return

        self.arm_teaching_widget.line_edit_sh0_value.setText(str(arm_position['sh0']))
        self.arm_teaching_widget.line_edit_sh1_value.setText(str(arm_position['sh1']))
        self.arm_teaching_widget.line_edit_el0_value.setText(str(arm_position['el0']))
        self.arm_teaching_widget.line_edit_el1_value.setText(str(arm_position['el1']))
        self.arm_teaching_widget.line_edit_wr0_value.setText(str(arm_position['wr0']))
        self.arm_teaching_widget.line_edit_wr1_value.setText(str(arm_position['wr1']))

    def test_qrcode_reading(self):
        self.main_operator.start_capture_thread()

    def define_arm_teaching_events(self):
        self.arm_teaching_widget.apply_current_position(self.get_current_arm_pose)
        self.arm_teaching_widget.execute_joint_move(self.move_current_arm_pose)
        self.arm_teaching_widget.execute_stow(self.spot_arm_stow)
        self.arm_teaching_widget.execute_capture(self.capture)
        self.arm_teaching_widget.execute_load_arm_status(self.load_arm_status)
        self.arm_teaching_widget.execute_save_arm_status(self.save_arm_status)

    @user_input_decorator
    def apply_setting(self):
        setting = {
            "waypoint": self.cbx_inspection_waypoint.currentText(),
            "resolution": self.cbx_resolution.currentText(),
            "focus_absolute": self.sbx_focus_absolute.value(),
            "arm_position": {
                "sh0": float(self.arm_teaching_widget.line_edit_sh0_value.text()),
                "sh1": float(self.arm_teaching_widget.line_edit_sh1_value.text()),
                "el0": float(self.arm_teaching_widget.line_edit_el0_value.text()),
                "el1": float(self.arm_teaching_widget.line_edit_el1_value.text()),
                "wr0": float(self.arm_teaching_widget.line_edit_wr0_value.text()),
                "wr1": float(self.arm_teaching_widget.line_edit_wr1_value.text())
            }
        }

        self.main_operator.spot_manager.set_position_settings(setting, self.position)
        # if self.position == "1":
        #     self.main_operator.spot_manager.set_position1_settings(setting)
        # elif self.position == "3":
        #     self.main_operator.spot_manager.set_position3_settings(setting)

    def save_arm_status(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Arm Status", "", "JSON Files (*.json)", options=options)

        if not file_path:
            return
        try:
            joint_params_dict = self.main_operator.spot_manager.get_arm_setting(self.position)

            # 입력된 파일 경로의 확장자 검사
            if not file_path.endswith(".json"):
                file_path += '.json'

            with open(file_path, 'w') as file:
                json.dump(joint_params_dict, file, indent=4)

            util_functions.show_message(text="Complete.")
        except Exception as e:
            util_functions.show_message(text=str(e))

    @spot_connection_check
    def get_current_arm_pose(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText("Apply current arm pose values?")
        msg_box.setWindowTitle("Confirm Registration")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msg_box.exec_()

        if result == QMessageBox.Yes:
            hand_pose = self.main_operator.spot_robot.get_hand_position_dict()
            joint_state = self.main_operator.spot_robot.get_current_joint_state()

            self.arm_teaching_widget.line_edit_sh0_value.setText(str(joint_state['sh0']))
            self.arm_teaching_widget.line_edit_sh1_value.setText(str(joint_state['sh1']))
            self.arm_teaching_widget.line_edit_el0_value.setText(str(joint_state['el0']))
            self.arm_teaching_widget.line_edit_el1_value.setText(str(joint_state['el1']))
            self.arm_teaching_widget.line_edit_wr0_value.setText(str(joint_state['wr0']))
            self.arm_teaching_widget.line_edit_wr1_value.setText(str(joint_state['wr1']))

    def move_current_arm_pose(self):
        sh0 = float(self.arm_teaching_widget.line_edit_sh0_value.text())
        sh1 = float(self.arm_teaching_widget.line_edit_sh1_value.text())
        el0 = float(self.arm_teaching_widget.line_edit_el0_value.text())
        el1 = float(self.arm_teaching_widget.line_edit_el1_value.text())
        wr0 = float(self.arm_teaching_widget.line_edit_wr0_value.text())
        wr1 = float(self.arm_teaching_widget.line_edit_wr1_value.text())
        params = [sh0, sh1, el0, el1, wr0, wr1]
        result = self.main_operator.spot_joint_move_manual(params)
        self.main_operator.write_log(result)

    @spot_connection_check
    def spot_arm_stow(self):
        result = self.main_operator.spot_robot.robot_arm_manager.stow()
        self.main_operator.write_log(result)

    def load_arm_status(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("JSON Files (*.json)")
        joint_pos_dict = None
        if dialog.exec_():
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                with open(file_path, 'r') as file:
                    joint_pos_dict = json.load(file)

        if not joint_pos_dict:
            return

        # self.main_operator.spot_manager.set_arm_pose_setting(joint_pos_dict, self.position)
        self.setup_arm_values(joint_pos_dict.values())

    def setup_arm_values(self, values):
        labels = ["sh0", "sh1", "el0", "el1", "wr0", "wr1"]

        for label, value in zip(labels, values):
            label_name = f"line_edit_{label}_value"
            label_widget = getattr(self.arm_teaching_widget, label_name, None)
            label_widget.setText(str(value))

    def capture(self):
        image = self.main_operator.spot_capture_bgr()
        if image is not None:
            self.gview_image.set_bgr_image(image)

    def read_qr_image(self):
        image = self.main_operator.spot_capture_bgr()
        frame_image, barcode_info, barcode_image = qr_functions.read_datamatrix(image)

        if barcode_info:
            self.gview_image.set_bgr_image(frame_image)
            print(barcode_info)
        else:
            print("Read Failed.")
