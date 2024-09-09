from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QGridLayout, QFrame, \
    QListWidget, QStackedWidget, QFormLayout, QComboBox
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QFont, QKeySequence, QShortcut
from PySide6.QtCore import Qt
from functools import partial

import DefineGlobal
from HoleDetect_Yolo.AISettingWidget import AISettingWidget
from main_operator import MainOperator
from biw_utils.decorators import arm_control_exception_decorator, exception_decorator
from widget.Setting.CommunicationCheckWidget import OPCWidget
from widget.common.GraphicView import GraphicView
from widget.common.GraphicViewWithText import GraphicViewWithText
from widget.HoleInspection.HoleInspectionWidget import HoleInspectionWidget
from widget.Setting.NavigationSettingWidget import NavigationSettingWidget
from widget.Setting.ProgramSettingWidget import ProgramSettingWidget
from widget.QRCode.QRCodeInspectionWidget import QRCodeInspectionWidget
from widget.Setting.SpotControlWidget import SpotControlWidget
from widget.icp_pointcloud_widget import ICPPointCloudVisualizer


class BodyWidget(QStackedWidget):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        # self.setObjectName("body")
        self.view_mode = 0

        self.body_display_widget = BodyDisplayWidget()
        self.body_admin_widget = BodyAdminWidget(self.main_operator)

        self.addWidget(self.body_display_widget)
        self.addWidget(self.body_admin_widget)

    def viewModeChange(self):
        if self.view_mode == 0:
            self.view_mode = 1
        else:
            self.view_mode = 0

        self.setCurrentIndex(self.view_mode)
        return self.view_mode


class BodyDisplayWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("body")
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

        self.stylesheet_inspection_button_off = """
            background-color: rgb(179, 179, 179);
            color: gray;
            border-radius: 10px;
            padding: 10px;
            font-size: 14px;
        """

        self.stylesheet_inspection_button_on = """
            background-color: rgb(220, 220, 220);
            color: black;
            border-radius: 10px;
            padding: 10px;
            font-size: 14px;
        """

        self.initUI()

    def initUI(self):
        self.main_layout = QHBoxLayout(self)

        self.left_layout = QVBoxLayout()
        self.right_layout = QVBoxLayout()

        self.left_layout.addStretch(1)
        self.initImageSection()
        self.main_layout.addLayout(self.right_layout)

        # Set column stretch to 3:7 ratio
        # self.main_layout.setStretch(0, 1)
        # self.main_layout.setStretch(1, 0)

        self.main_layout.setSpacing(6)

    def update_work_status(self, work_status):
        # 모든 레이블에 unselected 스타일 적용
        self.position_home.setStyleSheet("background-color: darkgray; color: white;")
        self.position1.setStyleSheet("background-color: darkgray; color: white;")
        self.position2.setStyleSheet("background-color: darkgray; color: white;")
        self.position3.setStyleSheet("background-color: darkgray; color: white;")
        self.position_complete.setStyleSheet("background-color: darkgray; color: white; border-radius: 10px")

        self.position_home.setFont(QFont("현대하모니 M", 11))
        self.position1.setFont(QFont("현대하모니 M", 11))
        self.position2.setFont(QFont("현대하모니 M", 11))
        self.position3.setFont(QFont("현대하모니 M", 11))
        self.position_complete.setFont(QFont("현대하모니 M", 11))

        if work_status == DefineGlobal.WORK_STATUS.HOME:
            self.position_home.setObjectName("position_dock")
            self.position_home.setStyleSheet("color: black; background-color: lightslategray;")

        elif work_status == DefineGlobal.WORK_STATUS.POSITION1:
            self.position1.setObjectName("position1")
            self.position1.setStyleSheet("color: black; background-color: lightcoral;")

        elif work_status == DefineGlobal.WORK_STATUS.POSITION2:
            self.position2.setObjectName("position2")
            self.position2.setStyleSheet("color: black; background-color: beige;")

        elif work_status == DefineGlobal.WORK_STATUS.POSITION3:
            self.position3.setObjectName("position3")
            self.position3.setStyleSheet("color: black; background-color: lightblue;")

        elif work_status == DefineGlobal.WORK_STATUS.COMPLETE:
            self.position_complete.setObjectName("position_complete")
            self.position_complete.setStyleSheet("color: black; background-color: lime")

        else:
            pass

    def initImageSection(self):
        hlayout_image_section = QHBoxLayout()

        # LEFT DISPLAY WIDGET
        vlayout_display_data = QVBoxLayout()

        status_widget = QWidget()
        hlayout_status = QHBoxLayout()
        self.lbl_agv_status = QLabel("AGV POS OFF")
        self.lbl_agv_status.setStyleSheet("""
            font-family: '현대하모니 L';
            color: white;
            background-color: red;
            font-size: 16px;
            padding: 20px;
            border-radius: 10px;
        """)
        self.lbl_agv_status.setAlignment(Qt.AlignCenter)
        # self.lbl_agv_status.setObjectName("subtitle")
        # self.lbl_agv_status.setStyleSheet(self.stylesheet_off)

        # TODO: WORK COMPLETE STATUS
        self.lbl_work_complete_status = QLabel("WORK COMPLETE OFF")
        self.lbl_work_complete_status.setStyleSheet("""
            font-family: '현대하모니 L';
            color: white;
            background-color: red;
            font-size: 16px;
            padding: 20px;
            border-radius: 10px;
        """)
        self.lbl_work_complete_status.setAlignment(Qt.AlignCenter)

        hlayout_status.addWidget(self.lbl_agv_status)
        hlayout_status.addWidget(self.lbl_work_complete_status)

        status_widget.setLayout(hlayout_status)
        status_widget.setStyleSheet("background-color: rgba(179, 179, 179, 0.5)")
        lbl_spec_data_title = QLabel("SPEC")
        lbl_spec_data_title.setObjectName("subtitle")
        self.lbl_spec_data_value = QLabel("")
        hlayout_spec_data = QHBoxLayout()
        hlayout_spec_data.addWidget(lbl_spec_data_title)
        hlayout_spec_data.addWidget(self.lbl_spec_data_value)

        lbl_body_type_title = QLabel("BODY TYPE")
        lbl_body_type_title.setObjectName("subtitle")
        self.lbl_body_type_value = QLabel("")
        hlayout_body_type = QHBoxLayout()
        hlayout_body_type.addWidget(lbl_body_type_title)
        hlayout_body_type.addWidget(self.lbl_body_type_value)

        lbl_agv_no_title = QLabel("AGV NO")
        lbl_agv_no_title.setObjectName("subtitle")
        self.lbl_agv_no_value = QLabel("")
        hlayout_agv_no = QHBoxLayout()
        hlayout_agv_no.addWidget(lbl_agv_no_title)
        hlayout_agv_no.addWidget(self.lbl_agv_no_value)

        lbl_hole_spec_title = QLabel("CURTAIN HOLE TYPE")
        lbl_hole_spec_title.setObjectName("subtitle")
        self.lbl_hole_spec_value = QLabel("")
        hlayout_hole_spec = QHBoxLayout()
        hlayout_hole_spec.addWidget(lbl_hole_spec_title)
        hlayout_hole_spec.addWidget(self.lbl_hole_spec_value)

        lbl_hole_inspection_title = QLabel("HOLE INSPECT RESULT")
        lbl_hole_inspection_title.setObjectName("subtitle")
        self.lbl_hole_inspection_value = QLabel("")
        hlayout_hole_inspection = QHBoxLayout()
        hlayout_hole_inspection.addWidget(lbl_hole_inspection_title)
        hlayout_hole_inspection.addWidget(self.lbl_hole_inspection_value)

        self.widget_hole_inspection_buttons = QWidget()
        self.widget_hole_inspection_buttons.setObjectName("hole_inspection_button")

        self.btn_hole_inspection_pass = QPushButton("PASS")
        self.btn_hole_inspection_real_ng = QPushButton("Send to Heavy Repair")

        self.btn_hole_inspection_pass.setMinimumHeight(125)
        self.btn_hole_inspection_real_ng.setMinimumHeight(125)

        self.widget_hole_inspection_buttons.setEnabled(False)
        self.hole_inspection_button_disabled()
        hlayout_hole_inspection_btn = QHBoxLayout()
        hlayout_hole_inspection_btn.addWidget(self.btn_hole_inspection_pass)
        hlayout_hole_inspection_btn.addWidget(self.btn_hole_inspection_real_ng)

        self.widget_hole_inspection_buttons.setLayout(hlayout_hole_inspection_btn)

        lbl_cycle_time = QLabel("Cycle Time")
        lbl_cycle_time.setObjectName("subtitle")
        self.lbl_cycle_time_value = QLabel("00.00 s")
        self.lbl_cycle_time_value.setObjectName("body")
        hlayout_cycle_time = QHBoxLayout()
        hlayout_cycle_time.addWidget(lbl_cycle_time)
        hlayout_cycle_time.addWidget(self.lbl_cycle_time_value)

        vlayout_display_data.addWidget(status_widget)

        vlayout_display_data.addLayout(hlayout_spec_data)
        vlayout_display_data.addLayout(hlayout_body_type)
        vlayout_display_data.addLayout(hlayout_agv_no)
        vlayout_display_data.addLayout(hlayout_hole_spec)
        vlayout_display_data.addLayout(hlayout_hole_inspection)
        vlayout_display_data.addWidget(self.widget_hole_inspection_buttons)
        # vlayout_display_data.addWidget(lbl_hole_inspection_title)
        # vlayout_display_data.addWidget(self.lbl_hole_inspection_value)
        # vlayout_display_data.addWidget(self.lbl_spec_hole_compare)

        # TODO: REMOVE NG CONFIRM.
        # hlayout_hole_inspection_buttons = QHBoxLayout()
        # self.btn_send_work_complete = QPushButton("Work Complete")
        # self.btn_send_ng_confirm = QPushButton("NG Confirm")
        # self.btn_send_work_complete.setMinimumHeight(100)
        # self.btn_send_ng_confirm.setMinimumHeight(100)
        #
        # hlayout_hole_inspection_buttons.addWidget(self.btn_send_work_complete)
        # hlayout_hole_inspection_buttons.addWidget(self.btn_send_ng_confirm)
        # vlayout_display_data.addLayout(hlayout_hole_inspection_buttons)

        # @Todo: Display Spot position info
        # Position: Dock, Position #1, Position #2, Position #3
        # Status: Docking, Moving, Inspecting, Waiting
        self.spot_layout = QVBoxLayout()
        self.hlayout_spot_position = QHBoxLayout()
        self.position_home = QPushButton("HOME")
        self.position_home.setObjectName("position_dock")
        self.position1 = QPushButton("Position #1")
        self.position2 = QPushButton("Position #2")
        self.position3 = QPushButton("Position #3")
        self.position1.setObjectName("position1")
        self.position2.setObjectName("position2")
        self.position3.setObjectName("position3")
        self.position_complete = QPushButton("STEP BACK")
        self.position_complete.setObjectName("position_complete")

        self.hlayout_spot_position.addWidget(self.position_home)
        self.hlayout_spot_position.addWidget(self.position1)
        self.hlayout_spot_position.addWidget(self.position2)
        self.hlayout_spot_position.addWidget(self.position3)
        self.hlayout_spot_position.addWidget(self.position_complete)

        self.spot_layout.addLayout(self.hlayout_spot_position)
        # self.spot_layout.addWidget(self.button)
        # self.spot_layout.addLayout(self.hlayout_biw_status)
        # self.spot_layout.addWidget(self.button_biw_status)

        vlayout_display_data.addLayout(self.spot_layout)

        vlayout_display_data.addStretch()
        vlayout_display_data.addLayout(hlayout_cycle_time)

        # hlayout_spot_video.addLayout(glayout_spot_video)
        self.image_gview = GraphicViewWithText()
        self.image_gview.setObjectName("image")
        self.image_gview.setProperty("main_view", True)  # 속성 추가
        self.image_gview.setFrameStyle(QFrame.Box)

        hlayout_image_section.addLayout(vlayout_display_data)
        hlayout_image_section.addWidget(self.image_gview)

        hlayout_image_section.setStretch(0, 1)
        hlayout_image_section.setStretch(1, 4)
        self.right_layout.addLayout(hlayout_image_section)

    def initSpotVideoSection(self):
        self.flayout_spot_video = QFormLayout()

    def toggle_display_section(self):
        current_index = self.display_section.currentIndex()
        new_index = 1 if current_index == 0 else 0
        self.display_section.setCurrentIndex(new_index)

    def createLabel(self, title, value):
        title_label = QLabel(title)
        value_label = QLabel(value)
        return title_label, value_label

    # 임시 코드
    # @Todo: 배경 없는 SPOT 이미지 구해서 적용하면 필요없는 코드
    def update_pixmap(self, image_path, logo: QLabel):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print("Error: Unable to load image")
            return

        scaled_pixmap = pixmap.scaled(logo.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded_pixmap = self.create_round_pixmap(scaled_pixmap, logo)
        logo.setPixmap(rounded_pixmap)
        logo.setMask(rounded_pixmap.mask())  # 마스크 설정으로 동그란 모양을 만듦

    def create_round_pixmap(self, pixmap, logo: QLabel):
        size = logo.size()
        rounded_pixmap = QPixmap(size)
        rounded_pixmap.fill(Qt.transparent)

        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)

        # 이미지가 QLabel의 중앙에 위치하도록 계산
        x_offset = (pixmap.width() - size.width()) // 2
        y_offset = (pixmap.height() - size.height()) // 2
        painter.drawPixmap(-x_offset, -y_offset, pixmap)
        painter.end()

        return rounded_pixmap

    def update_spot_connection_status(self, status):
        pass
        # self.spot_connection_status.setText(f'{status}')
        # self.spot_connection_status.setStyleSheet("""
        #     font-family: '현대하모니 M';
        #     font-size: 12pt;
        #     background-color: green; border-radius: 5px; margin: 20px;
        # """)

    def update_spot_power_status(self, status):
        pass
        # self.spot_power_status.setText(f'{status}')
        # self.spot_power_status.setStyleSheet("""
        #     font-family: '현대하모니 M';
        #     font-size: 12pt;
        #     background-color: green; border-radius: 5px; margin: 20px;
        # """)

    def set_send_agv_pass(self, function):
        self.btn_hole_inspection_pass.clicked.connect(function)

    def set_send_agv_real_ng(self, function):
        self.btn_hole_inspection_real_ng.clicked.connect(function)

    def set_click_position_home(self, function):
        self.position_home.clicked.connect(function)

    def set_click_position1(self, function):
        self.position1.clicked.connect(function)

    def set_click_position2(self, function):
        self.position2.clicked.connect(function)

    def set_click_position3(self, function):
        self.position3.clicked.connect(function)

    def set_click_position_step_back(self, function):
        self.position_complete.clicked.connect(function)


    def hole_inspection_button_enabled(self):
        # self.widget_hole_inspection_buttons.setProperty("is_active", True)

        self.btn_hole_inspection_pass.setStyleSheet(self.stylesheet_inspection_button_on)
        self.btn_hole_inspection_real_ng.setStyleSheet(self.stylesheet_inspection_button_on)

        self.btn_hole_inspection_pass.setFont(QFont("현대하모니 L", 14))
        self.btn_hole_inspection_real_ng.setFont(QFont("현대하모니 L", 14))

    def hole_inspection_button_disabled(self):
        # self.widget_hole_inspection_buttons.setProperty("is_active", False)

        self.widget_hole_inspection_buttons.setStyleSheet("background-color: dimgray")
        self.btn_hole_inspection_pass.setStyleSheet(self.stylesheet_inspection_button_off)
        self.btn_hole_inspection_real_ng.setStyleSheet(self.stylesheet_inspection_button_off)

        self.btn_hole_inspection_pass.setFont(QFont("현대하모니 L", 14))
        self.btn_hole_inspection_real_ng.setFont(QFont("현대하모니 L", 14))

    # def set_event_ng_confirm(self, function):
    #     self.btn_send_ng_confirm.clicked.connect(function)


class BodyAdminWidget(QWidget):
    def __init__(self, main_operator: MainOperator):
        super().__init__()
        self.main_operator = main_operator
        self.arm_manager = self.main_operator.spot_robot.robot_arm_manager
        self.move_manager = self.main_operator.spot_robot.robot_move_manager

        self.setObjectName("body_admin")
        self.initUI()

    def initUI(self):
        self.main_layout = QHBoxLayout(self)

        self.left_layout = QVBoxLayout()
        self.left_widget = QWidget()
        self.left_widget.setLayout(self.left_layout)
        self.left_widget.setObjectName("admin_left_panel")

        self.right_layout = QVBoxLayout()

        self.setup_body_type()
        self.setupButtons()
        self.setupPages()

        # Log
        self.spot_control_log = QListWidget()
        self.left_layout.addWidget(self.spot_control_log)

        self.main_layout.addWidget(self.left_widget)
        self.main_layout.addLayout(self.right_layout)

        self.main_layout.setStretch(0, 2)
        self.main_layout.setStretch(1, 8)
        self.init_arm_shortcut()
        self.init_body_shortcut()

    def init_arm_shortcut(self):
        # 기본 기능
        shortcut_stow = QShortcut(QKeySequence("n"), self)
        shortcut_unstow = QShortcut(QKeySequence("y"), self)
        shortcut_gripper_open = QShortcut(QKeySequence("o"), self)
        shortcut_gripper_close = QShortcut(QKeySequence("p"), self)

        # Arm 제어
        shortcut_arm_move_forward = QShortcut(QKeySequence("+"), self)
        shortcut_arm_move_backward = QShortcut(QKeySequence("-"), self)
        shortcut_arm_move_left = QShortcut(QKeySequence("4"), self)
        shortcut_arm_move_right = QShortcut(QKeySequence("6"), self)
        shortcut_arm_move_up = QShortcut(QKeySequence("8"), self)
        shortcut_arm_move_down = QShortcut(QKeySequence("5"), self)

        shortcut_rotate_roll_right = QShortcut(QKeySequence("9"), self)
        shortcut_rotate_roll_left = QShortcut(QKeySequence("7"), self)
        shortcut_rotate_down = QShortcut(QKeySequence("Ctrl+5"), self)
        shortcut_rotate_up = QShortcut(QKeySequence("Ctrl+8"), self)
        shortcut_rotate_yaw_right = QShortcut(QKeySequence("Ctrl+4"), self)
        shortcut_rotate_yaw_left = QShortcut(QKeySequence("Ctrl+6"), self)

        shortcut_stow.activated.connect(self.stow)
        shortcut_unstow.activated.connect(self.unstow)
        shortcut_gripper_open.activated.connect(self.gripper_open)
        shortcut_gripper_close.activated.connect(self.gripper_close)

        shortcut_arm_move_forward.activated. connect(self.move_forward)
        shortcut_arm_move_backward.activated.connect(self.move_backward)
        shortcut_arm_move_left.activated.    connect(self.move_left)
        shortcut_arm_move_right.activated.   connect(self.move_right)
        shortcut_arm_move_up.activated.      connect(self.move_up)
        shortcut_arm_move_down.activated.    connect(self.move_down)
        shortcut_rotate_roll_right.activated.connect(self.rotate_plus_rx)
        shortcut_rotate_roll_left.activated. connect(self.rotate_minus_rx)
        shortcut_rotate_down.activated.      connect(self.rotate_plus_ry)
        shortcut_rotate_up.activated.        connect(self.rotate_minus_ry)
        shortcut_rotate_yaw_right.activated. connect(self.rotate_plus_rz)
        shortcut_rotate_yaw_left.activated.  connect(self.rotate_minus_rz)

    def init_body_shortcut(self):
        # 단축키 설정
        shortcut_move_forward = QShortcut(QKeySequence("W"), self)
        shortcut_move_backward = QShortcut(QKeySequence("S"), self)
        shortcut_strafe_left = QShortcut(QKeySequence("A"), self)
        shortcut_strafe_right = QShortcut(QKeySequence("D"), self)
        shortcut_turn_left = QShortcut(QKeySequence("Q"), self)
        shortcut_turn_right = QShortcut(QKeySequence("E"), self)
        # shortcut_move_forward_left = QShortcut(QKeySequence("W+A"), self.main_window)

        # 각 단축키에 해당하는 기능 연결
        shortcut_move_forward.activated .connect(self.body_move_forward)
        shortcut_move_backward.activated.connect(self.body_move_backward)
        shortcut_strafe_left.activated  .connect(self.body_move_left)
        shortcut_strafe_right.activated .connect(self.body_move_right)
        shortcut_turn_left.activated    .connect(self.body_move_turn_left)
        shortcut_turn_right.activated   .connect(self.body_move_turn_right)
        # shortcut_move_forward_left.activated.connect(self.move_forward_left)

    def setup_body_type(self):
        self.cbx_select_body_type = QComboBox()
        self.cbx_select_body_type.addItem('NE')
        self.cbx_select_body_type.addItem('ME')
        self.cbx_select_body_type.setCurrentText(DefineGlobal.SELECTED_BODY_TYPE.name)
        self.cbx_select_body_type.currentTextChanged.connect(self.update_body_type_change)
        self.left_layout.addWidget(self.cbx_select_body_type)

    def setupButtons(self):
        self.widget_setting_NE = QWidget()
        self.widget_setting_ME = QWidget()
        layout_NE = QVBoxLayout()
        layout_ME = QVBoxLayout()

        self.btn1_NE = QPushButton("Inspection Position #1")
        self.btn2_NE = QPushButton("Inspection Position #2")
        self.btn3_NE = QPushButton("Inspection Position #3")
        self.btn4_NE = QPushButton("SPOT Control Page")
        self.btn5_NE = QPushButton("Inspection Settings")
        self.btn6_NE = QPushButton("SPOT Navigation Settings")
        self.btn7_NE = QPushButton("Communication Settings")

        self.btn1_ME = QPushButton("Inspection Position #1")
        self.btn4_ME = QPushButton("SPOT Control Page")
        self.btn5_ME = QPushButton("Inspection Settings")
        self.btn6_ME = QPushButton("SPOT Navigation Settings")
        self.btn7_ME = QPushButton("Communication Settings")

        self.btn_ai_setting_page_NE = QPushButton("AI Setting Page")
        self.btn_ai_setting_page_ME = QPushButton("AI Setting Page")

        self.buttons_NE = [self.btn1_NE, self.btn2_NE, self.btn3_NE, self.btn4_NE, self.btn5_NE, self.btn6_NE, self.btn7_NE, self.btn_ai_setting_page_NE]
        self.buttons_ME = [self.btn1_ME, self.btn4_ME, self.btn5_ME, self.btn6_ME, self.btn7_ME, self.btn_ai_setting_page_ME]

        for index, button in enumerate(self.buttons_NE):
            button.clicked.connect(partial(self.change_NE_Page, index))
            # self.left_layout.addWidget(button)

        self.btn1_ME.clicked.connect(partial(self.change_ME_Page, 0, 0))
        self.btn4_ME.clicked.connect(partial(self.change_ME_Page, 1, 3))
        self.btn5_ME.clicked.connect(partial(self.change_ME_Page, 2, 4))
        self.btn6_ME.clicked.connect(partial(self.change_ME_Page, 3, 5))
        self.btn7_ME.clicked.connect(partial(self.change_ME_Page, 4, 6))
        self.btn7_ME.clicked.connect(partial(self.change_ME_Page, 5, 7))

        layout_NE.addWidget(self.btn1_NE)
        layout_NE.addWidget(self.btn2_NE)
        layout_NE.addWidget(self.btn3_NE)
        layout_NE.addWidget(self.btn4_NE)
        layout_NE.addWidget(self.btn5_NE)
        layout_NE.addWidget(self.btn6_NE)
        layout_NE.addWidget(self.btn7_NE)
        layout_NE.addWidget(self.btn_ai_setting_page_NE)

        layout_ME.addWidget(self.btn1_ME)
        layout_ME.addWidget(self.btn4_ME)
        layout_ME.addWidget(self.btn5_ME)
        layout_ME.addWidget(self.btn6_ME)
        layout_ME.addWidget(self.btn7_ME)
        layout_ME.addWidget(self.btn_ai_setting_page_ME)

        self.widget_setting_NE.setLayout(layout_NE)
        self.widget_setting_ME.setLayout(layout_ME)

        self.left_layout.addWidget(self.widget_setting_NE)
        self.left_layout.addWidget(self.widget_setting_ME)

        self.widget_setting_ME.hide()

        # 초기 선택 버튼 설정
        self.buttons = self.buttons_NE
        self.update_NE_ButtonStyles(0)
        self.update_ME_ButtonStyles(0)

    def setupPages(self):
        self.stacked_widget = QStackedWidget()

        self.page1 = QRCodeInspectionWidget(self.main_operator, "1")
        self.page2 = HoleInspectionWidget(self.main_operator, "2")
        self.page3 = QRCodeInspectionWidget(self.main_operator, "3")
        self.page4 = SpotControlWidget(self.main_operator)
        self.page5 = ProgramSettingWidget(self.main_operator)
        self.page6 = NavigationSettingWidget(self.main_operator)
        self.page7 = OPCWidget(self.main_operator)
        self.page_ai_setting = AISettingWidget()

        self.stacked_widget.addWidget(self.page1)
        self.stacked_widget.addWidget(self.page2)
        self.stacked_widget.addWidget(self.page3)
        self.stacked_widget.addWidget(self.page4)
        self.stacked_widget.addWidget(self.page5)
        self.stacked_widget.addWidget(self.page6)
        self.stacked_widget.addWidget(self.page7)
        self.stacked_widget.addWidget(self.page_ai_setting)
        self.stacked_widget.setObjectName("body_admin")
        self.right_layout.addWidget(self.stacked_widget)

    def change_NE_Page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.update_NE_ButtonStyles(index)
        self.selected_index_NE = index

    def change_ME_Page(self, btn_index, page_index):
        self.stacked_widget.setCurrentIndex(page_index)
        self.update_ME_ButtonStyles(btn_index)
        self.selected_index_ME = page_index

    def update_NE_ButtonStyles(self, selected_index):
        for index, button in enumerate(self.buttons_NE):
            if index == selected_index:
                button.setProperty("selected", True)
            else:
                button.setProperty("selected", False)

            button.setFont(QFont("현대하모니 L", 14))
            button.style().unpolish(button)
            button.style().polish(button)

    def update_ME_ButtonStyles(self, selected_index):
        for index, button in enumerate(self.buttons_ME):
            if index == selected_index:
                button.setProperty("selected", True)
            else:
                button.setProperty("selected", False)

            button.setFont(QFont("현대하모니 L", 14))
            button.style().unpolish(button)
            button.style().polish(button)

    def update_body_type_change(self):
        current_body_type = self.cbx_select_body_type.currentText()

        # TODO:
        # 1. change navigation map
        # 2. change config file
        if current_body_type == "NE":
            self.main_operator.change_body_type_setting(DefineGlobal.BODY_TYPE.NE)

            self.widget_setting_NE.show()
            self.widget_setting_ME.hide()

        elif current_body_type == "ME":
            self.main_operator.change_body_type_setting(DefineGlobal.BODY_TYPE.ME)

            self.widget_setting_NE.hide()
            self.widget_setting_ME.show()

        self.page1.load_setting()
        self.page2.load_setting()
        self.page3.load_setting()
        self.page5.update_program_setting_data()
        self.page6.get_list_graph()

    @arm_control_exception_decorator
    def move_forward(self):
        result = self.arm_manager.move_out()

    @arm_control_exception_decorator
    def move_backward(self):
        result = self.arm_manager.move_in()

    @arm_control_exception_decorator
    def move_left(self):
        result = self.arm_manager.rotate_ccw()

    @arm_control_exception_decorator
    def move_right(self):
        result = self.arm_manager.rotate_cw()

    @arm_control_exception_decorator
    def move_up(self):
        result = self.arm_manager.move_up()

    @arm_control_exception_decorator
    def move_down(self):
        result = self.arm_manager.move_down()

    @arm_control_exception_decorator
    def stow(self):
        result = self.arm_manager.stow()

    @arm_control_exception_decorator
    def unstow(self):
        result = self.arm_manager.unstow()

    @arm_control_exception_decorator
    def gripper_open(self):
        result = self.arm_manager.gripper_open()

    @arm_control_exception_decorator
    def gripper_close(self):
        result = self.arm_manager.gripper_close()

    @arm_control_exception_decorator
    def rotate_plus_rx(self):
        result = self.arm_manager.rotate_plus_rx()

    @arm_control_exception_decorator
    def rotate_minus_rx(self):
        result = self.arm_manager.rotate_minus_rx()

    @arm_control_exception_decorator
    def rotate_plus_ry(self):
        result = self.arm_manager.rotate_plus_ry()

    @arm_control_exception_decorator
    def rotate_minus_ry(self):
        result = self.arm_manager.rotate_minus_ry()

    @arm_control_exception_decorator
    def rotate_plus_rz(self):
        result = self.arm_manager.rotate_plus_rz()

    @arm_control_exception_decorator
    def rotate_minus_rz(self):
        result = self.arm_manager.rotate_minus_rz()

    @exception_decorator
    def body_move_forward(self):
        result = self.move_manager.move_forward()
        # self.body_control_thread.set_axis("forward")
        # self.body_control_thread.run()

    @exception_decorator
    def body_move_backward(self):
        self.move_manager.move_backward()
        # self.body_control_thread.set_axis("backward")
        # self.body_control_thread.run()

    @exception_decorator
    def body_move_left(self):
        self.move_manager.strafe_left()
        # self.body_control_thread.set_axis("left")
        # self.body_control_thread.run()

    @exception_decorator
    def body_move_right(self):
        self.move_manager.strafe_right()
        # self.body_control_thread.set_axis("right")
        # self.body_control_thread.run()

    @exception_decorator
    def body_move_turn_left(self):
        self.move_manager.turn_left()
        # self.body_control_thread.set_axis("turn_left")
        # self.body_control_thread.run()

    @exception_decorator
    def body_move_turn_right(self):
        self.move_manager.turn_right()
        # self.body_control_thread.set_axis("turn_right")
        # self.body_control_thread.run()

