from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QPushButton, QProgressBar, \
    QListWidget, QSlider, QCheckBox
from PySide6.QtCore import Qt
from PySide6 import QtGui

from biw_utils.decorators import user_input_decorator, exception_decorator
from widget.Setting.SpotArmControlWidget import SpotArmControlWidget
from widget.Setting.SpotBodyControlWidget import SpotBodyControlWidget
from widget.Setting.SpotCameraParameterWidget import SpotCameraParameterWidget
from widget.common.GraphicViewWithText import GraphicViewWithText


class SpotControlWidget(QWidget):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.spot_robot    = main_operator.spot_robot
        self.spot_manager  = main_operator.spot_manager

        self.arm_control_widget  = SpotArmControlWidget(self.main_operator)
        self.body_control_widget = SpotBodyControlWidget(self.main_operator)
        self.camera_param_widget = SpotCameraParameterWidget(self.main_operator)

        self.vlayout_spot_connection = QVBoxLayout()
        self.spot_param_widget = QWidget()
        self.initUI()

    def initUI(self):
        self.hlayout_main = QHBoxLayout()

        # region: Spot Control Layout
        self.vlayout_spot_control = QVBoxLayout()

        self.lbl_connection_title = QLabel("Connection")
        self.lbl_connection_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_connection_title.setObjectName("subtitle")
        self.vlayout_spot_connection.addWidget(self.lbl_connection_title)

        # Connection input fields
        self.hlayout_robot_ip = QHBoxLayout()
        self.hlayout_username = QHBoxLayout()
        self.hlayout_password = QHBoxLayout()
        self.hlayout_dock_id = QHBoxLayout()

        self.robot_ip_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.dock_id_edit = QLineEdit()

        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)  # Set echo mode to hide password

        # Load default values from the connection_manager
        conn_info = self.spot_manager.get_spot_connection_info()
        self.robot_ip_edit.setText(conn_info['robot_ip'])
        self.username_edit.setText(conn_info['username'])
        self.password_edit.setText(conn_info['password'])
        self.dock_id_edit.setText(str(conn_info['dock_id']))

        # Add labels for the input fields
        robot_ip_label = QLabel("Robot IP:")
        username_label = QLabel("Username:")
        password_label = QLabel("Password:")
        dock_id_label = QLabel("Dock ID:")

        self.btn_connect_spot = QPushButton("Connect")
        self.btn_connect_spot.clicked.connect(self.update_connection_info)

        self.hlayout_robot_ip.addWidget(robot_ip_label)
        self.hlayout_robot_ip.addWidget(self.robot_ip_edit)
        self.hlayout_username.addWidget(username_label)
        self.hlayout_username.addWidget(self.username_edit)
        self.hlayout_password.addWidget(password_label)
        self.hlayout_password.addWidget(self.password_edit)
        self.hlayout_dock_id.addWidget(dock_id_label)
        self.hlayout_dock_id.addWidget(self.dock_id_edit)

        self.hlayout_robot_ip.setStretch(0, 1)
        self.hlayout_robot_ip.setStretch(1, 3)
        self.hlayout_username.setStretch(0, 1)
        self.hlayout_username.setStretch(1, 3)
        self.hlayout_password.setStretch(0, 1)
        self.hlayout_password.setStretch(1, 3)
        self.hlayout_dock_id.setStretch(0, 1)
        self.hlayout_dock_id.setStretch(1, 3)

        self.vlayout_spot_connection.addLayout(self.hlayout_robot_ip)
        self.vlayout_spot_connection.addLayout(self.hlayout_username)
        self.vlayout_spot_connection.addLayout(self.hlayout_password)
        self.vlayout_spot_connection.addLayout(self.hlayout_dock_id)
        self.vlayout_spot_connection.addWidget(self.btn_connect_spot)

        self.vlayout_spot_control.addLayout(self.vlayout_spot_connection)

        vlayout_spot_control = QVBoxLayout()
        hlayout_spot_control_buttons = QVBoxLayout()

        self.btn_lease = QPushButton("Lease")
        self.btn_power = QPushButton("Power")

        self.btn_docking = QPushButton("Docking")
        self.btn_docking.clicked.connect(self._dock)

        hlayout_spot_control_buttons.addWidget(self.btn_lease)
        hlayout_spot_control_buttons.addWidget(self.btn_power)
        hlayout_spot_control_buttons.addWidget(self.btn_docking)

        vlayout_spot_control.addLayout(hlayout_spot_control_buttons)

        self.btn_lease.clicked.connect(self._lease)
        self.btn_power.clicked.connect(self._power)

        self.vlayout_spot_control.addLayout(vlayout_spot_control)
        # self.vlayout_spot_control.addWidget(self.camera_param_widget)

        self.init_spot_param_widget()

        # Capture
        self.btn_capture_rgb = QPushButton("Capture")
        font = QtGui.QFont()
        font.setFamily("현대하모니 M")
        self.btn_capture_rgb.setFont(font)

        self.cbx_capture_live = QCheckBox("Live")

        self.vlayout_spot_control.addWidget(self.spot_param_widget)
        # self.vlayout_spot_control.addWidget(self.arm_control_widget)
        # self.vlayout_spot_control.addWidget(self.body_control_widget)
        self.vlayout_spot_control.addWidget(self.btn_capture_rgb)
        self.vlayout_spot_control.addWidget(self.cbx_capture_live)
        self.vlayout_spot_control.addStretch()

        # endregion

        # region: Spot Image View
        self.spot_image_view = GraphicViewWithText()

        # endregion

        self.hlayout_main.addLayout(self.vlayout_spot_control)
        self.hlayout_main.addWidget(self.spot_image_view)

        self.hlayout_main.setStretch(0, 3)
        self.hlayout_main.setStretch(1, 7)

        self.setLayout(self.hlayout_main)
    def init_spot_param_widget(self):
        self.vlayout_control_params = QVBoxLayout()

        self.lbl_control_params_title = QLabel("■ SPOT Parameters")
        self.lbl_control_params_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_control_params_title.setObjectName("subtitle")
        self.vlayout_control_params.addWidget(self.lbl_control_params_title)

        self.hlayout_body_speed = QHBoxLayout()
        self.hlayout_arm_speed = QHBoxLayout()

        self.body_speed_edit = QLineEdit()
        self.arm_speed_edit = QLineEdit()

        # Load default values from the control_param_manager
        control_params = self.main_operator.spot_manager.get_control_params()
        self.body_speed_edit.setText(str(control_params['body_speed']))
        self.arm_speed_edit.setText(str(control_params['arm_speed']))

        # Add labels for the input fields
        body_speed_label = QLabel("Body Speed:")
        arm_speed_label = QLabel("Arm Speed:")

        self.vslider_height = QSlider(Qt.Orientation.Vertical)
        self.vslider_height.setRange(-2, 2)
        self.vslider_height.setTickInterval(1)
        self.vslider_height.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.vslider_height.valueChanged.connect(self._height_change)

        self.hlayout_body_control = QHBoxLayout()

        self.hlayout_body_speed.addWidget(body_speed_label)
        self.hlayout_body_speed.addWidget(self.body_speed_edit)
        self.hlayout_arm_speed.addWidget(arm_speed_label)
        self.hlayout_arm_speed.addWidget(self.arm_speed_edit)

        self.hlayout_body_control.addWidget(self.vslider_height)
        self.hlayout_body_control.addLayout(self.hlayout_body_speed)
        self.hlayout_body_control.addLayout(self.hlayout_arm_speed)

        self.vlayout_control_params.addLayout(self.hlayout_body_control)

        self.btn_update_params = QPushButton("Update Params")
        self.btn_update_params.clicked.connect(self.update_params)

        self.vlayout_control_params.addWidget(self.btn_update_params)

        self.spot_param_widget.setLayout(self.vlayout_control_params)

    @exception_decorator
    def update_connection_info(self):
        robot_ip = self.robot_ip_edit.text()
        username = self.username_edit.text()
        password = self.password_edit.text()
        dock_id = self.dock_id_edit.text()
        self.main_operator.connect_robot(robot_ip, username, password, dock_id)
        # self.main_operator.run_spot_reconnect()

    @user_input_decorator
    def update_params(self):
        body_speed = float(self.body_speed_edit.text())
        arm_speed  = float(self.arm_speed_edit.text())
        self.main_operator.update_spot_body_speed(body_speed)
        self.main_operator.update_spot_arm_speed(arm_speed)

    def _lease(self):
        """
        로봇 제어권을 제어합니다.
        """
        return self.main_operator.toggle_lease()

    def _power(self):
        """
        로봇 파워를 제어합니다.
        """
        return self.main_operator.toggle_power()

    def _dock(self):
        """
        로봇 Docking을 수행합니다.
        """
        return self.main_operator.docking()

    def _height_change(self, value):
        value /= 10
        print(value)
        return self.main_operator.height_change(value)

    def set_capture_callback(self, function):
        self.btn_capture_rgb.clicked.connect(function)
