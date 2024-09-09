from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QProgressBar, QVBoxLayout, QGroupBox, QHBoxLayout, \
    QPushButton


class SpotStatusWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.stylesheet_on = """
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: lime; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 5px;
            """

        self.stylesheet_off = """
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: red; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """

        # self.setStyleSheet("background-color: rgba(102, 102, 102, 50)")
        # 메인 레이아웃 생성
        main_layout = QVBoxLayout()

        # SPOT STATUS 제목
        lbl_spot_title = QLabel("SPOT STATUS")
        lbl_spot_title.setAlignment(Qt.AlignCenter)
        # lbl_spot_title.setObjectName("subtitle")
        lbl_spot_title.setStyleSheet("""
            font-family: '현대하모니 M';
            font-size: 14pt;
            margin: 5px 0;
            background-color: transparent
        """)

        main_layout.addWidget(lbl_spot_title)

        # 수평 레이아웃 생성
        spot_layout = QHBoxLayout()

        # CONNECT 그룹
        self.connect_group = QGroupBox("CONNECT")
        connect_layout = QVBoxLayout()
        self.btn_connect_value = QPushButton("OFF")
        self.btn_connect_value.setStyleSheet("font-family: '현대하모니 L';")
        connect_layout.addWidget(self.btn_connect_value)
        self.connect_group.setLayout(connect_layout)
        spot_layout.addWidget(self.connect_group)

        # LEASE 그룹
        self.lease_group = QGroupBox("LEASE")
        lease_layout = QVBoxLayout()
        self.btn_lease_value = QPushButton("-")
        # self.btn_lease_value.setStyleSheet("font-family: '현대하모니 L';")
        lease_layout.addWidget(self.btn_lease_value)
        self.lease_group.setLayout(lease_layout)
        spot_layout.addWidget(self.lease_group)

        # POWER 그룹
        self.power_group = QGroupBox("POWER")
        power_layout = QVBoxLayout()
        self.btn_power_value = QPushButton("-")
        # self.btn_power_value.setStyleSheet("font-family: '현대하모니 L';")

        power_layout.addWidget(self.btn_power_value)
        self.power_group.setLayout(power_layout)
        spot_layout.addWidget(self.power_group)

        # BATTERY 그룹
        self.battery_group = QGroupBox("BATTERY")
        battery_layout = QVBoxLayout()
        self.progressBar_battery = QProgressBar()
        self.progressBar_battery.setFormat("%p%")
        self.progressBar_battery.setAlignment(Qt.AlignCenter)
        self.progressBar_battery.setStyleSheet("font-family: '현대하모니 L';")
        self.progressBar_battery.setValue(0)
        battery_layout.addWidget(self.progressBar_battery)
        self.battery_group.setLayout(battery_layout)
        spot_layout.addWidget(self.battery_group)

        # LOCALIZATION
        self.localization_group = QGroupBox("LOCALIZATION")
        localization_layout = QVBoxLayout()
        self.btn_localization_value = QPushButton("-")
        # self.btn_power_value.setStyleSheet("font-family: '현대하모니 L';")
        localization_layout.addWidget(self.btn_localization_value)
        self.localization_group.setLayout(localization_layout)
        spot_layout.addWidget(self.localization_group)

        # ESTOP
        self.estop_group = QGroupBox("E-STOP")
        estop_layout = QHBoxLayout()
        self.btn_estop_keepalive_value = QPushButton("-")
        self.btn_estop_status_value = QPushButton("-")

        self.btn_estop_keepalive_value.setMinimumWidth(100)
        self.btn_estop_status_value.setMinimumWidth(150)

        estop_layout.addWidget(self.btn_estop_keepalive_value)
        estop_layout.addWidget(self.btn_estop_status_value)
        self.estop_group.setLayout(estop_layout)
        spot_layout.addWidget(self.estop_group)

        spot_layout.setStretch(0, 1)    # CONNECTION
        spot_layout.setStretch(1, 1)    # LEASE
        spot_layout.setStretch(2, 1)    # POWER
        spot_layout.setStretch(3, 3)    # BATTERY
        spot_layout.setStretch(4, 1)    # LOCALIZATION
        spot_layout.setStretch(5, 1)    # ESTOP
        main_layout.addLayout(spot_layout)

        self.setLayout(main_layout)

        # Set Enabled False
        self.buttons_enabled(False)

        # 스타일 시트 적용
        self.setStyleSheet("""
            QGroupBox {
                font-family: '현대하모니 M';
                color: white;
                border: 0px solid silver;
                border-radius: 6px;
                margin: 5px;
            }
            QGroupBox::title {
                color: white;
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QLabel {
                font-family: '현대하모니 L';
                font-size: 14px;
                padding: 2px;
            }
        """)

    # def set_connection_status(self, status):
    #     self.lbl_connect_value.setText(status)
    #     if status == "ON":
    #         self.lbl_connect_value.setStyleSheet("""
    #             font-family: '현대하모니 L';
    #             color: white;
    #             background-color: lime;
    #             font-size: 16px;
    #             font-weight: bold;
    #             padding: 4px;
    #             border-radius: 4px;
    #         """)
    #     else:
    #         self.lbl_connect_value.setStyleSheet("""
    #             font-family: '현대하모니 L';
    #             color: white;
    #             background-color: red;
    #             font-size: 16px;
    #             font-weight: bold;
    #             padding: 4px;
    #             border-radius: 4px;
    #         """)

    def set_lease_status(self, status):
        self.btn_lease_value.setText(status)
        if status == "RUNNING":
            self.btn_lease_value.setStyleSheet("""
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: lime; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """)
        else:
            self.btn_lease_value.setStyleSheet("""
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: red; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """)

    def set_power_status(self, status):
        self.btn_power_value.setText(status)
        if status == "ON":
            self.btn_power_value.setStyleSheet("""
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: lime; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """)
        elif status == "POWERING_ON":
            self.btn_power_value.setStyleSheet("""
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: orange; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """)

        elif status == "POWERING_OFF":
            self.btn_power_value.setStyleSheet("""
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: orange;
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """)

        else:
            self.btn_power_value.setStyleSheet("""
                font-family: '현대하모니 L'; 
                color: white; 
                background-color: red; 
                font-size: 16px; 
                padding: 4px;
                border-radius: 4px;
            """)

    def set_battery_status(self, status, val, time_left):
        self.progressBar_battery.setValue(val)
        self.progressBar_battery.setFormat(f"{status} - %p% - {time_left}")

    def set_connection_status(self, status):
        if status:
            text = "CONNECTED"
            self.btn_connect_value.setText(text)
            self.btn_connect_value.setStyleSheet(self.stylesheet_on)
            self.buttons_enabled(True)

        else:
            text = "DISCONNECTED"
            self.btn_connect_value.setStyleSheet(self.stylesheet_off)
            self.set_disconnect()

    def set_localized_status(self, status):
        if status:
            text = "Localized"
            self.btn_localization_value.setStyleSheet(self.stylesheet_on)
        else:
            text = "NOT Localized"
            self.btn_localization_value.setStyleSheet(self.stylesheet_off)
        self.btn_localization_value.setText(text)

    def set_estop_status(self, status_str, sw_estop_status):
        # self.widget_estop.stop_button.setText(status_str)
        if status_str == "Alive":
            self.btn_estop_keepalive_value.setStyleSheet(self.stylesheet_on)
        elif status_str == "ERROR":
            self.btn_estop_keepalive_value.setStyleSheet(self.stylesheet_off)
        elif status_str == "OFF":
            self.btn_estop_keepalive_value.setStyleSheet(self.stylesheet_off)

        self.btn_estop_keepalive_value.setText(status_str)

        if sw_estop_status == "NOT E-STOPPED":
            self.btn_estop_status_value.setStyleSheet(self.stylesheet_on)
        elif sw_estop_status == "E-STOPPED":
            self.btn_estop_status_value.setStyleSheet(self.stylesheet_off)

        self.btn_estop_status_value.setText(sw_estop_status)

    def set_disconnect(self):
        self.btn_connect_value.setText("DISCONNECTED")
        self.btn_lease_value.setText("-")
        self.btn_power_value.setText("-")
        self.progressBar_battery.setValue(0)
        self.btn_localization_value.setText("-")
        self.btn_estop_keepalive_value.setText("-")
        self.btn_estop_status_value.setText("-")

        stylesheet = """
            font-family: '현대하모니 L'; 
            color: black; 
            background-color: dimgray; 
            font-size: 16px; 
            padding: 4px;
            border-radius: 4px;
        """

        self.btn_connect_value.setStyleSheet(stylesheet)
        self.btn_lease_value.setStyleSheet(stylesheet)
        self.btn_power_value.setStyleSheet(stylesheet)
        self.btn_localization_value.setStyleSheet(stylesheet)
        # self.progressBar_battery.setStyleSheet(stylesheet)
        self.btn_estop_keepalive_value.setStyleSheet(stylesheet)
        self.btn_estop_status_value.setStyleSheet(stylesheet)

        self.buttons_enabled(False)

    def buttons_enabled(self, is_enabled):
        self.btn_connect_value.setEnabled(is_enabled)
        self.btn_lease_value.setEnabled(is_enabled)
        self.btn_power_value.setEnabled(is_enabled)
        self.btn_localization_value.setEnabled(is_enabled)
        self.btn_estop_keepalive_value.setEnabled(is_enabled)
        self.btn_estop_status_value.setEnabled(is_enabled)

    # def event_update_spot_status(self, lease, power, bar_status, bar_val, time_left):
    #     self.set_lease_status(lease)
    #     self.set_power_status(power)
    #     self.set_battery_status(bar_status, bar_val, time_left)

    def set_toggle_btn_power(self, function):
        self.btn_power_value.clicked.connect(function)

    def set_toggle_btn_lease(self, function):
        self.btn_lease_value.clicked.connect(function)

    def set_toggle_btn_localize(self, function):
        self.btn_localization_value.clicked.connect(function)

    def set_toggle_btn_estop(self, function):
        self.btn_estop_keepalive_value.clicked.connect(function)

    def set_release_estop(self, function):
        self.btn_estop_status_value.clicked.connect(function)
