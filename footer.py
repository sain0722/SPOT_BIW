from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QProgressBar, QGridLayout

import DefineGlobal
from widget.common.SpotStatusWidget import SpotStatusWidget


class FooterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("footer")
        self.footer_layout = QHBoxLayout(self)
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
        self.initUI()

    def initUI(self):
        # TODO: SETTING stylesheet footer buttons
        # 1. System Running Section
        self.init_system_running_section()

        # 2. By-Pass Section
        self.init_by_pass_section()

        # SPOT LEASE, POWER, BATTERY
        self.spot_status_widget = SpotStatusWidget()
        self.spot_status_widget.setObjectName("SpotStatus")

        # SPOT E-STOP AUTHORITY

        # SPOT DOCKING
        self.btn_spot_docking = QPushButton("DOCKING")
        self.btn_spot_docking.setObjectName("header")

        self.footer_layout.addWidget(self.spot_status_widget)
        self.footer_layout.addWidget(self.btn_spot_docking)

        self.footer_layout.setStretch(0, 1)
        self.footer_layout.setStretch(1, 1)
        self.footer_layout.setStretch(2, 4)
        self.footer_layout.setStretch(3, 1)

        self.setLayout(self.footer_layout)

    def init_system_running_section(self):
        vlayout_system_running = QVBoxLayout()

        # SPOT STATUS 제목
        lbl_system_mode_title = QLabel("SYSTEM MODE")
        lbl_system_mode_title.setAlignment(Qt.AlignCenter)
        lbl_system_mode_title.setObjectName("subtitle")
        # lbl_system_running_title.setStyleSheet("""
        # font-family: '현대하모니 M';
        # font-size: 16pt;
        # font-weight: bold;
        # margin: 10px 0;
        # background-color: transparent
        # """)

        self.btn_toggle_system_mode = QPushButton("MANUAL")
        self.btn_toggle_system_mode.setFixedHeight(75)
        self.btn_toggle_system_mode.setObjectName("signal_off")
        self.btn_toggle_system_mode.clicked.connect(self.toggle_system_mode)

        vlayout_system_running.addWidget(lbl_system_mode_title)
        vlayout_system_running.addWidget(self.btn_toggle_system_mode)
        self.footer_layout.addLayout(vlayout_system_running)

    def init_by_pass_section(self):
        vlayout_by_pass = QVBoxLayout()

        # SPOT STATUS 제목
        lbl_by_pass_title = QLabel("BY-PASS MODE")
        lbl_by_pass_title.setAlignment(Qt.AlignCenter)
        lbl_by_pass_title.setObjectName("subtitle")
        # lbl_by_pass_title.setStyleSheet("""
        # font-family: '현대하모니 M';
        # font-size: 16pt;
        # font-weight: bold;
        # margin: 10px 0;
        # background-color: transparent
        # """)

        self.btn_toggle_by_pass = QPushButton("MANUAL\nBY-PASS OFF")
        self.btn_toggle_by_pass.setFixedHeight(75)
        self.btn_toggle_by_pass.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: red;
                padding: 16px;
                font-size: 16px;
                border-radius: 4px;
                """)
        # self.btn_toggle_by_pass.clicked.connect(self.toggle_by_pass)

        vlayout_by_pass.addWidget(lbl_by_pass_title)
        vlayout_by_pass.addWidget(self.btn_toggle_by_pass)
        self.footer_layout.addLayout(vlayout_by_pass)

    def updateButtonLabel(self, mode):
        if mode == 0:
            self.btn_toggle_body.setText("Display Mode")
        else:
            self.btn_toggle_body.setText("Admin Mode")

    def setToggleEvent(self, function):
        self.btn_toggle_body.clicked.connect(function)

    def setDemoEvent(self, function):
        self.btn_toggle_demo.clicked.connect(function)

    def toggle_system_mode(self):
        if DefineGlobal.PROCESS_THREAD_IS_RUNNING:
            DefineGlobal.PROCESS_THREAD_IS_RUNNING = False
            self.ui_update_system_manual()
        else:
            DefineGlobal.PROCESS_THREAD_IS_RUNNING = True
            self.ui_update_system_auto()

    def toggle_by_pass(self):
        if DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS:
            DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS = False
            self.ui_update_bypass_off()
            # self.btn_toggle_by_pass.setObjectName("signal_off")
        else:
            DefineGlobal.PROCESS_THREAD_MANUAL_BY_PASS = True
            self.ui_update_bypass_on()
            # self.btn_toggle_by_pass.setObjectName("signal_on")

    def ui_update_system_auto(self):
        self.btn_toggle_system_mode.setText("AUTO")
        self.btn_toggle_system_mode.setStyleSheet(self.stylesheet_on)

    def ui_update_system_manual(self):
        self.btn_toggle_system_mode.setText("MANUAL")
        self.btn_toggle_system_mode.setStyleSheet(self.stylesheet_off)

    def ui_update_bypass_on(self):
        self.btn_toggle_by_pass.setText("MANUAL\nBY-PASS ON")
        self.btn_toggle_by_pass.setStyleSheet(self.stylesheet_on)

    def ui_update_bypass_off(self):
        self.btn_toggle_by_pass.setText("MANUAL\nBY-PASS OFF")
        self.btn_toggle_by_pass.setStyleSheet(self.stylesheet_off)

    def set_spot_docking_callback(self, function):
        self.btn_spot_docking.clicked.connect(function)

    def set_send_work_complete(self, function):
        self.btn_send_work_complete.clicked.connect(function)
        self.btn_send_work_complete.clicked.connect(function)

    def set_send_by_pass_mode(self, function):
        self.btn_toggle_by_pass.clicked.connect(function)
