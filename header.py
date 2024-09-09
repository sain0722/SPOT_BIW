from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QProgressBar, QGridLayout, \
    QDialog, QLineEdit, QMessageBox, QDialogButtonBox
from PySide6.QtGui import QPixmap, QFont, QColor
from PySide6.QtCore import Qt

import DefineGlobal
from biw_utils import util_functions
from biw_utils.util_functions import show_message
from widget.LoginDialog import LoginDialog
from widget.common.OPCStatusWidget import OPCStatusWidget
from widget.common.SpotStatusWidget import SpotStatusWidget


class HeaderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.btn_toggle_body = None
        self.setObjectName("header")
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout(self)

        logo_label = QLabel()
        logo_label.setObjectName("logo")
        logo_label.setFixedWidth(300)
        # pixmap = QPixmap('resources/Hyundai_Motor_Company_logo.svg')
        pixmap = QPixmap('resources/HMGMA_Logo_FullColor_RGB-removebg-preview.png')
        scaled_pixmap = pixmap.scaled(logo_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignVCenter)

        self.btn_toggle_vip_mode = QPushButton(" ")
        self.btn_toggle_vip_mode.setObjectName("header")
        self.btn_toggle_vip_mode.setMinimumWidth(150)

        self.btn_toggle_confirm_mode = QPushButton("AUTO PASS MODE")
        self.btn_toggle_confirm_mode.setObjectName("header")
        self.btn_toggle_confirm_mode.clicked.connect(self.toggle_user_confirm_mode)

        self.btn_toggle_body = QPushButton("Display Mode")
        self.btn_toggle_body.setObjectName("header")

        self.btn_toggle_demo = QPushButton("Demo Start")
        self.btn_toggle_demo.setObjectName("header")

        self.btn_exit_program = QPushButton("Exit Program")
        self.btn_exit_program.setObjectName("header")

        self.hyundai_fontM = QFont("현대하모니 M", 24)

        self.btn_toggle_menu = QPushButton(" ", self)
        self.btn_toggle_menu.setFixedWidth(150)
        self.btn_toggle_menu.setFixedHeight(70)
        self.btn_toggle_menu.setFont(self.hyundai_fontM)
        self.btn_toggle_menu.clicked.connect(self.toggle_menu)

        self.menu_widget = QWidget()
        # self.menu_widget.setFixedWidth(200)
        self.menu_layout = QHBoxLayout(self.menu_widget)

        self.menu_layout.addStretch()
        self.menu_layout.addWidget(self.btn_toggle_vip_mode)
        self.menu_layout.addWidget(self.btn_toggle_confirm_mode)
        self.menu_layout.addWidget(self.btn_toggle_body)
        self.menu_layout.addWidget(self.btn_toggle_demo)
        self.menu_layout.addWidget(self.btn_exit_program)
        self.menu_widget.setVisible(False)

        self.btn_run_spot_estop = QPushButton("E-STOP")
        self.btn_run_spot_estop.setProperty("estop", True)

        self.vlayout_header_info = QVBoxLayout()
        self.timestamp_label = QLabel("0000-00-00 00:00:00")
        self.timestamp_label.setObjectName("header")
        self.timestamp_label.setAlignment(Qt.AlignRight)
        self.timestamp_label.setProperty("information", True)  # 속성 추가

        self.hlayout_program_info = QHBoxLayout()
        self.lbl_program_info = QLabel(f"{DefineGlobal.SPOT_POSITION.name}")
        self.lbl_program_info.setAlignment(Qt.AlignCenter)
        self.lbl_program_info.setObjectName("header")
        self.lbl_program_info.setProperty("information", True)  # 속성 추가

        self.lbl_program_version = QLabel("v0.100")
        self.lbl_program_version.setAlignment(Qt.AlignCenter)
        self.lbl_program_version.setObjectName("header")
        self.lbl_program_version.setProperty("information", True)  # 속성 추가

        self.hlayout_program_info.addWidget(self.lbl_program_info)
        self.hlayout_program_info.addWidget(self.lbl_program_version)

        self.vlayout_header_info.addWidget(self.timestamp_label)
        self.vlayout_header_info.addLayout(self.hlayout_program_info)

        layout.addWidget(logo_label)
        layout.addStretch()
        layout.addWidget(self.menu_widget)
        layout.addWidget(self.btn_toggle_menu)
        layout.addWidget(self.btn_run_spot_estop)
        layout.addLayout(self.vlayout_header_info)

    def toggle_menu(self):
        if not self.menu_widget.isVisible():
            login_dialog = LoginDialog()
            result = login_dialog.exec_()
            if not result:
                return

            input_password = login_dialog.get_password()
            if input_password != DefineGlobal.ADMIN_PASSWORD:
                util_functions.show_message("invalid password")
                return

        self.menu_widget.setVisible(not self.menu_widget.isVisible())

    def setToggleEvent(self, function):
        self.btn_toggle_body.clicked.connect(function)

    def updateButtonLabel(self, mode):
        if mode == 0:
            self.btn_toggle_body.setText("Display Mode")
        else:
            self.btn_toggle_body.setText("Admin Mode")

    def setDemoEvent(self, function):
        self.btn_toggle_demo.clicked.connect(function)

    def set_exit_program_event(self, function):
        self.btn_exit_program.clicked.connect(function)

    def toggle_user_confirm_mode(self):
        # USER CONFIRM MODE TOGGLE
        DefineGlobal.MODE_USER_CONFIRM = not DefineGlobal.MODE_USER_CONFIRM
        if DefineGlobal.MODE_USER_CONFIRM:
            self.btn_toggle_confirm_mode.setText("USER CONFIRM MODE")
        else:
            self.btn_toggle_confirm_mode.setText("AUTO PASS MODE")
            DefineGlobal.WORK_COMPLETE_WAIT_USER_COMMAND = False

    def set_run_estop_callback(self, function):
        self.btn_run_spot_estop.clicked.connect(function)

    def set_toggle_vip_mode(self, function):
        self.btn_toggle_vip_mode.clicked.connect(function)

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
