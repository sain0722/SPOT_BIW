import re
import time

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, \
    QFileDialog, QApplication, QSpacerItem, QSizePolicy
from PySide6.QtGui import QFont

from main_operator import MainOperator
from biw_utils.decorators import spot_connection_check


class NavigationSettingWidget(QWidget):
    def __init__(self, main_operator: MainOperator):
        super().__init__()
        self.setObjectName("WidgetNavigation")

        self.main_operator = main_operator

        self.graph_nav_manager = self.main_operator.spot_robot.robot_graphnav_manager
        self.recording_manager = self.main_operator.spot_robot.robot_recording_manager

        self.navigation_thread = NavigationStatusChecker(self)
        self.navigation_thread.recording_status.connect(self.update_recording_status)
        self.navigation_thread.navigation_setting.connect(self.check_navigation_setting)
        self.navigation_thread.current_waypoints.connect(self.update_current_waypoints)

        # Main dialog setup
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("WidgetNavigation_central_widget")
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setObjectName("navigation_central_layout")
        self.central_layout.setSpacing(10)

        # Font setup
        # self.font = QtGui.QFont()
        # self.font.setFamily("현대하모니 M")
        # self.font.setPointSize(10)
        # self.setFont(self.font)

        # Header
        self.hlayout_header = QHBoxLayout()
        self.lbl_title = QLabel("■ Navigation")

        self.hlayout_recording_mode = QHBoxLayout()
        self.lbl_recording_str = QLabel("Recording Mode :")
        self.lbl_recording_str.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.lbl_recording_mode = QLabel("OFF")

        self.hlayout_recording_mode.addWidget(self.lbl_recording_str)
        self.hlayout_recording_mode.addWidget(self.lbl_recording_mode)
        self.hlayout_recording_mode.setStretch(0, 1)

        self.hlayout_header.addWidget(self.lbl_title)
        self.hlayout_header.addLayout(self.hlayout_recording_mode)
        self.hlayout_header.setStretch(0, 1)
        self.hlayout_header.setStretch(1, 1)

        self.central_layout.addLayout(self.hlayout_header)

        # Body
        self.hlayout_body = QHBoxLayout()
        self.vlayout_functions = QVBoxLayout()
        self.btn_get_list_graph = QPushButton("Get List Map", self)
        self.btn_get_localization_state = QPushButton("Localization", self)
        self.btn_upload_graph = QPushButton("Map Upload to SPOT", self)
        self.btn_download_full_graph = QPushButton("Map Download from SPOT", self)
        self.hlayout_navigate_to = QHBoxLayout()
        self.line_edit_waypoint = QLineEdit("waypoint_A", self)
        self.btn_navigate_to = QPushButton("MOVE", self)
        self.hlayout_navigate_to.addWidget(self.line_edit_waypoint)
        self.hlayout_navigate_to.addWidget(self.btn_navigate_to)

        self.vlayout_functions.addWidget(self.btn_get_list_graph)
        self.vlayout_functions.addWidget(self.btn_get_localization_state)
        self.vlayout_functions.addWidget(self.btn_upload_graph)
        self.vlayout_functions.addWidget(self.btn_download_full_graph)
        self.vlayout_functions.addLayout(self.hlayout_navigate_to)

        self.lbl_title_recording = QLabel("■ Recording", self)
        # self.lbl_title_recording.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.btn_clear_map = QPushButton("Map Clear", self)
        self.btn_start_recording = QPushButton("Recording Mode Start", self)
        self.btn_stop_recording = QPushButton("Recording Mode End", self)
        self.hlayout_create_waypoint = QHBoxLayout()
        self.line_edit_recording_waypoint = QLineEdit(self)
        self.hlayout_create_waypoint.addWidget(self.line_edit_recording_waypoint)
        self.btn_create_waypoint = QPushButton("Add Waypoint", self)
        self.hlayout_create_waypoint.addWidget(self.btn_create_waypoint)

        self.vlayout_functions.addWidget(self.lbl_title_recording)
        self.vlayout_functions.addWidget(self.btn_clear_map)
        self.vlayout_functions.addWidget(self.btn_start_recording)
        self.vlayout_functions.addWidget(self.btn_stop_recording)
        self.vlayout_functions.addLayout(self.hlayout_create_waypoint)

        # spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.vlayout_functions.addItem(spacerItem)

        self.hlayout_body.addLayout(self.vlayout_functions)

        self.navigation_log = QListWidget(self)
        self.navigation_log.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.navigation_log.setStyleSheet("background-color: dimgray")

        list_widget_font = QFont()
        list_widget_font.setFamily("맑은 고딕")
        list_widget_font.setPointSize(10)
        self.navigation_log.setFont(list_widget_font)

        self.hlayout_body.addWidget(self.navigation_log)

        self.hlayout_body.setStretch(0, 1)
        self.hlayout_body.setStretch(1, 2)

        self.central_layout.addLayout(self.hlayout_body)

        # Inspection Settings
        self.hlayout_inspection_setting = QHBoxLayout()
        self.hlayout_inspection_setting.setObjectName("hlayout_inspection_setting")
        self.hlayout_inspection_setting.setSpacing(10)

        self.vlayout_inspection_point1 = QVBoxLayout()
        self.vlayout_inspection_point2 = QVBoxLayout()
        self.vlayout_inspection_point3 = QVBoxLayout()

        # 검사포인트 #1
        self.lbl_title_target1 = QLabel("■ Inspection Point #1")
        self.lbl_set_nav_point_title1 = QLabel("Navigation Waypoint")
        self.lbl_set_nav_point_value1 = QLineEdit("1")
        self.lbl_inspection_status1 = QLabel("")
        self.btn_nav_point1 = QPushButton("Move")
        self.btn_nav_point1.clicked.connect(lambda: self.navigate_to_inspection_point(1))

        self.vlayout_inspection_point1.addWidget(self.lbl_title_target1)
        self.vlayout_inspection_point1.addWidget(self.lbl_set_nav_point_title1)
        self.vlayout_inspection_point1.addWidget(self.lbl_set_nav_point_value1)
        self.vlayout_inspection_point1.addWidget(self.lbl_inspection_status1)
        self.vlayout_inspection_point1.addWidget(self.btn_nav_point1)
        self.vlayout_inspection_point1.addStretch()

        self.lbl_title_target2 = QLabel("■ Inspection Point #2")
        self.lbl_set_nav_point_title2 = QLabel("Navigation Waypoint")
        self.lbl_set_nav_point_value2 = QLineEdit("2")
        self.lbl_inspection_status2 = QLabel("")
        self.btn_nav_point2 = QPushButton("Move")
        self.btn_nav_point2.clicked.connect(lambda: self.navigate_to_inspection_point(2))

        self.vlayout_inspection_point2.addWidget(self.lbl_title_target2)
        self.vlayout_inspection_point2.addWidget(self.lbl_set_nav_point_title2)
        self.vlayout_inspection_point2.addWidget(self.lbl_set_nav_point_value2)
        self.vlayout_inspection_point2.addWidget(self.lbl_inspection_status2)
        self.vlayout_inspection_point2.addWidget(self.btn_nav_point2)
        self.vlayout_inspection_point2.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.lbl_title_target3 = QLabel("■ Inspection Point #3")
        self.lbl_set_nav_point_title3 = QLabel("Navigation Waypoint")
        self.lbl_set_nav_point_value3 = QLineEdit("3")
        self.lbl_inspection_status3 = QLabel("")
        self.btn_nav_point3 = QPushButton("Move")
        self.btn_nav_point3.clicked.connect(lambda: self.navigate_to_inspection_point(3))

        self.vlayout_inspection_point3.addWidget(self.lbl_title_target3)
        self.vlayout_inspection_point3.addWidget(self.lbl_set_nav_point_title3)
        self.vlayout_inspection_point3.addWidget(self.lbl_set_nav_point_value3)
        self.vlayout_inspection_point3.addWidget(self.lbl_inspection_status3)
        self.vlayout_inspection_point3.addWidget(self.btn_nav_point3)

        self.vlayout_inspection_point3.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.hlayout_inspection_setting.addLayout(self.vlayout_inspection_point1)
        self.hlayout_inspection_setting.addLayout(self.vlayout_inspection_point2)
        self.hlayout_inspection_setting.addLayout(self.vlayout_inspection_point3)

        self.central_layout.addLayout(self.hlayout_inspection_setting)
        self.central_layout.addStretch()

        self.central_layout.setStretch(0, 0)
        self.central_layout.setStretch(1, 1)
        self.central_layout.setStretch(2, 2)

        self.setLayout(self.central_layout)

        self.init_signals()
        self.update_current_waypoints()

    def init_signals(self):
        self.btn_get_list_graph.clicked.connect(self.get_list_graph)
        self.btn_get_localization_state.clicked.connect(self.get_localization)
        self.btn_upload_graph.clicked.connect(self.upload_graph)
        self.btn_navigate_to.clicked.connect(self.navigate_to)

        self.btn_clear_map.clicked.connect(self.clear_map)
        self.btn_start_recording.clicked.connect(self.start_recording)
        self.btn_stop_recording.clicked.connect(self.stop_recording)
        self.btn_create_waypoint.clicked.connect(self.create_waypoint)
        self.btn_download_full_graph.clicked.connect(self.download_full_graph)

    def update_current_waypoints(self):
        # config = config_utils.get_config()
        waypoint_position1 = self.main_operator.spot_manager.get_waypoint("1")
        waypoint_position2_1, waypoint_position2_2 = self.main_operator.spot_manager.get_hole_waypoint()
        waypoint_position3 = self.main_operator.spot_manager.get_waypoint("3")

        self.lbl_set_nav_point_value1.setText(waypoint_position1)
        self.lbl_set_nav_point_value2.setText(f"{waypoint_position2_1}\n{waypoint_position2_2}")
        self.lbl_set_nav_point_value3.setText(waypoint_position3)

    def check_navigation_setting(self):
        # config = config_utils.get_config()
        waypoint1, waypoint2 = self.main_operator.spot_manager.get_hole_waypoint()

        waypoint_positions = [
            self.main_operator.spot_manager.get_waypoint("1"),
            waypoint1,
            waypoint2,
            self.main_operator.spot_manager.get_waypoint("3")
        ]

        # Localization 여부 확인
        is_localized = self.graph_nav_manager.is_localized()

        # QLabel 객체의 리스트
        status_labels = [self.lbl_inspection_status1, self.lbl_inspection_status2, self.lbl_inspection_status3]
        move_buttons = [self.btn_nav_point1, self.btn_nav_point2, self.btn_nav_point3]

        for waypoint, label, button in zip(waypoint_positions, status_labels, move_buttons):
            self.update_label_style(waypoint, label, is_localized, button)

    def update_label_style(self, waypoint, label, is_localized, button):
        valid_stylesheet = "QLabel { background-color: green; color: white; }"
        invalid_stylesheet = "QLabel { background-color: red; color: white; }"

        if self.main_window.robot.robot_graphnav_manager.exist_waypoint_in_map(waypoint) and is_localized:
            label.setText("유효한 waypoint")
            label.setStyleSheet(valid_stylesheet)
            button.setEnabled(True)
        else:
            if is_localized:
                label.setText("검사 불가능 (waypoint 확인 필요)")
            else:
                label.setText("검사 불가능 (Localization 확인 필요)")
            label.setStyleSheet(invalid_stylesheet)
            button.setEnabled(False)

    def start_navigation_thread(self):
        # Recording Thread
        self.navigation_thread.start()

    def stop_recording_thread(self):
        self.navigation_thread.stop()

    @spot_connection_check
    def get_list_graph(self):
        """
        그래프와 노드 정보를 가져옵니다.

        Args:
            is_clear (bool): 기존의 정보를 삭제할지 여부를 결정하는 플래그.
        """
        waypoints_list, edges_list = self.graph_nav_manager.list_graph_waypoint_and_edge_ids()

        # ListView 초기화
        self.navigation_log.clear()

        # waypoints_list와 edges_list를 log_navigation에 추가
        self.navigation_log.addItem("Waypoints List:")
        for waypoint in waypoints_list:
            self.navigation_log.addItem(waypoint)

        self.navigation_log.addItem("Edges List:")
        for edge in edges_list:
            self.navigation_log.addItem(edge)

        def copyToClipboard(item):
            clipboard = QApplication.clipboard()
            match = re.search(r'Waypoint name: (.*?) id:', item.text())

            if match:
                waypoint_name = match.group(1)
                clipboard.setText(waypoint_name)
                self.line_edit_waypoint.setText(waypoint_name)

        self.navigation_log.itemClicked.connect(copyToClipboard)

        # waypoint combobox update
        self.main_operator.event_qr_setting_waypoints.emit(waypoints_list)

    @spot_connection_check
    def get_localization(self):
        """
        로봇의 위치 정보를 가져오고, Localization을 합니다.
        """
        state, odom_tform_body = self.graph_nav_manager.get_localization_state()

        # ListView 초기화
        self.navigation_log.clear()

        # state 데이터 처리:
        state_str = str(state)  # state를 문자열로 변환합니다.
        state_lines = state_str.split('\n')  # 줄바꿈 문자를 기준으로 문자열을 분리합니다.

        self.navigation_log.addItem("State:")  # 분리된 각 줄을 listWidget에 추가합니다.
        for line in state_lines:
            self.navigation_log.addItem(line)  # 분리된 각 줄을 listWidget에 추가합니다.

        self.navigation_log.addItem("odom_tform_body:")  # 분리된 각 줄을 listWidget에 추가합니다.
        odom_tform_body_str = str(odom_tform_body)
        self.navigation_log.addItem(odom_tform_body_str)  # 분리된 각 줄을 listWidget에 추가합니다.

    @spot_connection_check
    def upload_graph(self):
        """
        그래프를 업로드합니다.
        """
        upload_filepath = QFileDialog.getExistingDirectory(None, 'Select Directory')
        if upload_filepath:
            self.graph_nav_manager.upload_graph_and_snapshots(upload_filepath)
            self.get_list_graph()

    @spot_connection_check
    def navigate_to(self):
        """
        주어진 노드로 로봇을 이동시킵니다.
        """
        waypoint = self.line_edit_waypoint.text()
        return self.graph_nav_manager.navigate_to(waypoint)

    @spot_connection_check
    def navigate_to_inspection_point(self, point):
        waypoint_labels = {
            1: self.lbl_set_nav_point_value1,
            2: self.lbl_set_nav_point_value2,
            3: self.lbl_set_nav_point_value3
        }
        waypoint = waypoint_labels.get(point).text()
        return self.graph_nav_manager.navigate_to(waypoint)

    @spot_connection_check
    def clear_map(self):
        """
        로봇에 저장된 map을 초기화합니다.
        """
        self.recording_manager.clear_map()

    @spot_connection_check
    def start_recording(self):
        """
        로봇을 Recording 모드로 변경합니다.
        """
        start_message = self.recording_manager.start_recording()

        self.navigation_log.clear()
        self.navigation_log.addItem(start_message)

    @spot_connection_check
    def stop_recording(self):
        """
        로봇의 Recording 모드를 중지합니다.
        """
        stop_message = self.recording_manager.stop_recording()

        self.navigation_log.clear()
        self.navigation_log.addItem(stop_message)

    @spot_connection_check
    def get_recording_status(self) -> bool:
        """
        현재 로봇의 Recording 상태를 확인합니다.
        """
        return self.recording_manager.get_recording_status()

    @spot_connection_check
    def update_recording_status(self, is_recording: bool):
        if is_recording:
            self.lbl_recording_mode.setText("ON")
            self.lbl_recording_mode.setStyleSheet("background-color: lime")
            self.lbl_recording_mode.setFont(self.font)
        else:
            self.lbl_recording_mode.setText("OFF")
            self.lbl_recording_mode.setStyleSheet("background-color: transparent")
            self.lbl_recording_mode.setFont(self.font)

    @spot_connection_check
    def create_waypoint(self):
        """
        Recording 상태일 때, 현재 위치에 Waypoint를 추가합니다.
        """
        waypoint_name = self.line_edit_recording_waypoint.text()
        message = self.recording_manager.create_waypoint(waypoint_name)

        self.navigation_log.clear()
        self.navigation_log.addItem(message)
        self.get_list_graph()

    @spot_connection_check
    def download_full_graph(self):
        """
        현재 로봇의 Map을 저장합니다.
        """
        download_filepath = QFileDialog.getExistingDirectory(None, 'Select Directory')
        if download_filepath:
            self.recording_manager.set_download_filepath(download_filepath)
            self.recording_manager.download_full_graph()


class NavigationStatusChecker(QThread):
    recording_status = Signal(bool)
    navigation_setting = Signal()
    current_waypoints = Signal()

    def __init__(self, widget: NavigationSettingWidget):
        super().__init__()
        self.widget = widget
        self.running = False

    def __del__(self):
        if self.running:
            self.stop()

    def run(self):
        self.running = True
        while self.running:
            recording_status = self.widget.get_recording_status()
            self.recording_status.emit(recording_status)
            self.navigation_setting.emit()
            self.current_waypoints.emit()
            time.sleep(0.15)

    def stop(self):
        self.running = False
        self.wait()
        self.quit()
