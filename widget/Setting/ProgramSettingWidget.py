import os
import shutil
from datetime import datetime, timedelta

import psutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFormLayout, QSpinBox, QFileDialog, \
    QPushButton, QSlider, QCheckBox, QProgressBar
from PySide6.QtCore import Qt, QTimer

import DefineGlobal
from main_operator import MainOperator
from biw_utils import util_functions
from widget.Setting.SpotCameraParameterWidget import SpotCameraParameterWidget


class ProgramSettingWidget(QWidget):
    def __init__(self, main_operator: MainOperator):
        super().__init__()
        self.main_operator = main_operator

        self.vlayout_position1 = QVBoxLayout()
        self.vlayout_position2 = QVBoxLayout()
        self.vlayout_position3 = QVBoxLayout()

        self.load_data()
        self.initUI()

        self.midnight_timer = QTimer()
        self.midnight_timer.timeout.connect(self.cleanup_old_images)
        self.init_midnight_timer()

    def initUI(self):
        self.main_layout = QVBoxLayout()
        self.vlayout_left  = QVBoxLayout()
        self.vlayout_right = QVBoxLayout()
        self.hlayout_main = QHBoxLayout()

        self.lbl_title = QLabel("Setting")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setObjectName("title")

        self.main_layout.addWidget(self.lbl_title)

        # Setup title
        waypoint_title_label = QLabel("WAYPOINT SETTING")
        waypoint_title_label.setObjectName("subtitle")
        waypoint_title_label.setAlignment(Qt.AlignCenter)
        self.vlayout_left.addWidget(waypoint_title_label)

        self.setup_position1()
        self.vlayout_left.addStretch()
        self.setup_position2()
        self.vlayout_left.addStretch()
        self.setup_position3()
        self.vlayout_left.addStretch()
        self.setup_image_setting()

        self.vlayout_left.addStretch()

        # Setup title
        spot_title_label = QLabel("SPOT SETTING")
        spot_title_label.setObjectName("subtitle")
        spot_title_label.setAlignment(Qt.AlignCenter)
        self.vlayout_right.addWidget(spot_title_label)

        self.setup_spot_setting()

        self.update_program_setting_data()

        self.hlayout_main.addLayout(self.vlayout_left)
        self.hlayout_main.addLayout(self.vlayout_right)
        self.main_layout.addLayout(self.hlayout_main)
        self.setLayout(self.main_layout)

    def load_data(self):
        self.position1_setting = self.main_operator.spot_manager.get_position_setting("1")
        self.position2_setting = self.main_operator.spot_manager.get_position_setting("2")
        self.position3_setting = self.main_operator.spot_manager.get_position_setting("3")
        self.robot_connection_data = self.main_operator.spot_manager.get_spot_connection_info()
        self.robot_control_params = self.main_operator.spot_manager.get_control_params()
        self.robot_camera_params = self.robot_control_params.get('camera_params', {})

    def update_program_setting_data(self):
        self.load_data()
        if DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.NE:
            self.update_position1()
            self.update_position2()
            self.update_position3()
            self.update_spot_setting()

        elif DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.ME:
            self.update_position1()
            self.update_position2()
            self.update_position3()
            self.update_spot_setting()

    def setup_position1(self):
        waypoint = self.position1_setting.get('waypoint', "-")
        resolution = self.position1_setting.get('resolution', "-")
        focus_absolute = self.position1_setting.get('focus_absolute', "-")

        flayout_position1 = QFormLayout()
        lbl_waypoint = QLabel("Waypoint")
        self.line_edit_waypoint1 = QLineEdit(f"{waypoint}")
        self.line_edit_waypoint1.setReadOnly(True)

        lbl_resolution = QLabel("Resolution")
        self.line_edit_resolution1 = QLineEdit(f"{resolution}")
        self.line_edit_resolution1.setReadOnly(True)

        lbl_focus_absolute = QLabel("Camera Focus")
        self.line_edit_focus_absolute1 = QLineEdit(f"{focus_absolute}")
        self.line_edit_focus_absolute1.setReadOnly(True)

        flayout_position1.addRow(lbl_waypoint, self.line_edit_waypoint1)
        flayout_position1.addRow(lbl_resolution, self.line_edit_resolution1)
        flayout_position1.addRow(lbl_focus_absolute, self.line_edit_focus_absolute1)

        self.vlayout_left.addLayout(flayout_position1)

    def setup_position2(self):
        waypoint1 = self.position2_setting.get('waypoint1', "-")
        waypoint2 = self.position2_setting.get('waypoint2', "-")
        resolution = self.position2_setting.get('resolution', "-")
        focus_absolute = self.position2_setting.get('focus_absolute', "-")

        flayout_position2 = QFormLayout()
        lbl_waypoint1 = QLabel("Waypoint - 1")
        lbl_waypoint2 = QLabel("Waypoint - 2")
        self.line_edit_waypoint2_1 = QLineEdit(f"{waypoint1}")
        self.line_edit_waypoint2_1.setReadOnly(True)
        self.line_edit_waypoint2_2 = QLineEdit(f"{waypoint2}")
        self.line_edit_waypoint2_2.setReadOnly(True)

        lbl_resolution = QLabel("Resolution")
        self.line_edit_resolution2 = QLineEdit(f"{resolution}")
        self.line_edit_resolution2.setReadOnly(True)

        lbl_focus_absolute = QLabel("Camera Focus")
        self.line_edit_focus_absolute2 = QLineEdit(f"{focus_absolute}")
        self.line_edit_focus_absolute2.setReadOnly(True)

        flayout_position2.addRow(lbl_waypoint1, self.line_edit_waypoint2_1)
        flayout_position2.addRow(lbl_waypoint2, self.line_edit_waypoint2_2)
        flayout_position2.addRow(lbl_resolution, self.line_edit_resolution2)
        flayout_position2.addRow(lbl_focus_absolute, self.line_edit_focus_absolute2)

        self.vlayout_left.addLayout(flayout_position2)

    def setup_position3(self):
        waypoint = self.position3_setting.get('waypoint', "-")
        resolution = self.position3_setting.get('resolution', "-")
        focus_absolute = self.position3_setting.get('focus_absolute', "-")

        flayout_position3 = QFormLayout()
        lbl_waypoint = QLabel("Waypoint")
        self.line_edit_waypoint3 = QLineEdit(f"{waypoint}")
        self.line_edit_waypoint3.setReadOnly(True)

        lbl_resolution = QLabel("Resolution")
        self.line_edit_resolution3 = QLineEdit(f"{resolution}")
        self.line_edit_resolution3.setReadOnly(True)

        lbl_focus_absolute = QLabel("Camera Focus")
        self.line_edit_focus_absolute3 = QLineEdit(f"{focus_absolute}")
        self.line_edit_focus_absolute3.setReadOnly(True)

        flayout_position3.addRow(lbl_waypoint, self.line_edit_waypoint3)
        flayout_position3.addRow(lbl_resolution, self.line_edit_resolution3)
        flayout_position3.addRow(lbl_focus_absolute, self.line_edit_focus_absolute3)

        self.vlayout_left.addLayout(flayout_position3)

    def setup_spot_setting(self):
        flayout_spot = QFormLayout()

        lbl_robot_ip = QLabel("SPOT IP")
        self.line_edit_robot_ip = QLineEdit(self.robot_connection_data['robot_ip'])

        lbl_body_speed = QLabel("Body Speed")
        self.line_edit_body_speed = QLineEdit(str(self.robot_control_params['body_speed']))

        lbl_arm_speed = QLabel("Arm Speed")
        self.line_edit_arm_speed = QLineEdit(str(self.robot_control_params['arm_speed']))

        lbl_battery_threshold_low = QLabel("Battery Threshold (Low)")
        self.sbx_battery_threshold_low = QSpinBox()
        self.sbx_battery_threshold_low.setMinimum(10)
        self.sbx_battery_threshold_low.setMaximum(100)
        self.sbx_battery_threshold_low.setValue(DefineGlobal.BATTERY_LOW_THRESHOLD)
        self.sbx_battery_threshold_low.valueChanged.connect(self.change_battery_threshold_low)

        lbl_battery_threshold_high = QLabel("Battery Threshold (High)")
        self.sbx_battery_threshold_high = QSpinBox()
        self.sbx_battery_threshold_high.setMinimum(10)
        self.sbx_battery_threshold_high.setMaximum(100)
        self.sbx_battery_threshold_high.setValue(DefineGlobal.BATTERY_ENOUGH_THRESHOLD)
        self.sbx_battery_threshold_high.valueChanged.connect(self.change_battery_threshold_high)

        flayout_spot.addRow(lbl_robot_ip, self.line_edit_robot_ip)
        flayout_spot.addRow(lbl_body_speed, self.line_edit_body_speed)
        flayout_spot.addRow(lbl_arm_speed, self.line_edit_arm_speed)
        flayout_spot.addRow(lbl_battery_threshold_low, self.sbx_battery_threshold_low)
        flayout_spot.addRow(lbl_battery_threshold_high, self.sbx_battery_threshold_high)

        self.camera_param_widget = SpotCameraParameterWidget(self.main_operator)

        self.vlayout_right.addLayout(flayout_spot)
        self.vlayout_right.addWidget(self.camera_param_widget)
        self.vlayout_right.addStretch()

    def change_battery_threshold_low(self, value):
        if value > DefineGlobal.BATTERY_ENOUGH_THRESHOLD:
            util_functions.show_message(text="Do not setting over enough threshold")
            self.sbx_battery_threshold_low.setValue(value - 1)
            return

        DefineGlobal.BATTERY_LOW_THRESHOLD = value

    def change_battery_threshold_high(self, value):
        if value < DefineGlobal.BATTERY_LOW_THRESHOLD:
            util_functions.show_message(text="Do not setting under low threshold")
            self.sbx_battery_threshold_high.setValue(value + 1)
            return

        DefineGlobal.BATTERY_ENOUGH_THRESHOLD = value

    def update_position1(self):
        waypoint   = self.position1_setting.get('waypoint', "-")
        resolution = self.position1_setting.get('resolution', "-")
        focus_absolute = self.position1_setting.get('focus_absolute', "-")

        self.line_edit_waypoint1.setText(waypoint)
        self.line_edit_resolution1.setText(resolution)
        self.line_edit_focus_absolute1.setText(f"{focus_absolute}")

    def update_position2(self):
        waypoint1       = ""
        waypoint2       = ""
        resolution      = ""
        focus_absolute  = ""

        if DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.NE:
            waypoint1      = self.position2_setting.get('waypoint1', "-")
            waypoint2      = self.position2_setting.get('waypoint2', "-")
            resolution     = self.position2_setting.get('resolution', "-")
            focus_absolute = self.position2_setting.get('focus_absolute', "-")

        self.line_edit_waypoint2_1.setText(waypoint1)
        self.line_edit_waypoint2_2.setText(waypoint2)
        self.line_edit_resolution2.setText(resolution)
        self.line_edit_focus_absolute2.setText(f"{focus_absolute}")

    def update_position3(self):
        waypoint       = ""
        resolution     = ""
        focus_absolute = ""

        if DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.NE:
            waypoint       = self.position3_setting.get('waypoint', "-")
            resolution     = self.position3_setting.get('resolution', "-")
            focus_absolute = self.position3_setting.get('focus_absolute', "-")

        self.line_edit_waypoint3.setText(waypoint)
        self.line_edit_resolution3.setText(resolution)
        self.line_edit_focus_absolute3.setText(f"{focus_absolute}")

    def update_spot_setting(self):
        # TODO
        pass

    def setup_image_setting(self):
        layout = QVBoxLayout()
        # Setup title
        title_label = QLabel("IMAGE SETTING")
        title_label.setObjectName("subtitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Setup path configuration
        path_layout = QHBoxLayout()
        self.path_label = QLabel('Save path:')
        self.path_input = QLineEdit(DefineGlobal.IMAGE_SAVE_PATH)
        self.path_button = QPushButton('Select Path')
        self.path_button.clicked.connect(self.select_folder)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.path_button)
        layout.addLayout(path_layout)

        # Compression setting configuration
        compression_layout = QHBoxLayout()
        self.compression_label = QLabel('Compression Setting (1-100):')
        self.compression_slider = QSlider(Qt.Horizontal)
        self.compression_slider.setRange(1, 100)
        self.compression_slider.setValue(85)
        self.compression_slider.valueChanged.connect(self.updateCompressionLabel)
        compression_layout.addWidget(self.compression_label)
        compression_layout.addWidget(self.compression_slider)
        # layout.addLayout(compression_layout)

        # Automatic cleanup configuration
        cleanup_layout = QHBoxLayout()
        self.cleanup_checkbox = QCheckBox("Enable Automatic Cleanup")
        self.cleanup_checkbox.toggled.connect(self.toggleCleanupSettings)
        self.cleanup_time_spinbox = QSpinBox()
        self.cleanup_time_spinbox.setRange(30, 180)
        self.cleanup_time_spinbox.setSuffix(" days after")
        self.cleanup_time_spinbox.setEnabled(True)
        cleanup_layout.addWidget(self.cleanup_checkbox)
        cleanup_layout.addWidget(self.cleanup_time_spinbox)
        layout.addLayout(cleanup_layout)

        # HDD space display
        disk_layout = QHBoxLayout()
        self.disk_label = QLabel('Remaining HDD space:')
        self.disk_info = QLabel(self.get_disk_space())
        disk_layout.addWidget(self.disk_label)
        disk_layout.addWidget(self.disk_info)
        layout.addLayout(disk_layout)

        self.d_disk_bar = QProgressBar()
        self.e_disk_bar = QProgressBar()

        self.vlayout_left.addLayout(layout)

    def select_folder(self):
        dir = QFileDialog.getExistingDirectory(self, "Select Folder", "./")
        if dir:
            self.path_input.setText(dir)
            self.folder_path = dir

    def updateCompressionLabel(self, value):
        self.compression_label.setText(f'Compression Setting ({value}):')

    def toggleCleanupSettings(self, checked):
        self.cleanup_time_spinbox.setEnabled(checked)

    def get_disk_space(self):
        try:
            d_disk_usage = psutil.disk_usage('D:/')
            d_total_gb = d_disk_usage.total / (2**30)
            d_free_gb = d_disk_usage.free / (2**30)
        except Exception as e:
            d_total_gb = 0
            d_free_gb = 0

        try:
            e_disk_usage = psutil.disk_usage('E:/')
            e_total_gb = e_disk_usage.total / (2**30)
            e_free_gb = e_disk_usage.free / (2**30)
        except Exception as e:
            e_total_gb = 0
            e_free_gb = 0

        disk_space_str = f'D: Drive Space: {d_free_gb:.2f} GB / {d_total_gb:.2f} GB'
        disk_space_str += f'\nE: Drive Space: {e_free_gb:.2f} GB / {e_total_gb:.2f} GB'

        return disk_space_str

    def init_midnight_timer(self):
        # Calculate the time until midnight
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        millis_till_midnight = int((midnight - now).total_seconds() * 1000)
        # millis_till_midnight = 0

        # Set the timer to trigger at midnight
        self.midnight_timer.start(millis_till_midnight)
        # self.midnight_timer.start(10000)

    def cleanup_old_images(self):
        cutoff_date = datetime.now() - timedelta(days=self.cleanup_time_spinbox.value())
        try:
            for folder_name in os.listdir(DefineGlobal.IMAGE_SAVE_PATH):
                try:
                    folder_date = datetime.strptime(folder_name, '%Y%m%d')
                    folder_path = os.path.join(DefineGlobal.IMAGE_SAVE_PATH, folder_name)
                    if folder_date < cutoff_date:
                        shutil.rmtree(folder_path)
                        log_message = f"Deleted Old Images Folder: {folder_path}"
                        self.main_operator.write_log(log_message)
                except ValueError:
                    log_message = f"Skipping non-date folder: {folder_name}"
                    self.main_operator.write_log(log_message)
                except Exception as e:
                    log_message = f"Cleanup Data Exception: {e}"
                    self.main_operator.write_log(log_message)
        except FileNotFoundError as e:
            log_message = f"Error Exception: {e}"
            self.main_operator.write_log(log_message)
