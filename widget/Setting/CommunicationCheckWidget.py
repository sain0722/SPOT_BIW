import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, \
    QTextEdit, QCheckBox, QComboBox
from PySide6.QtCore import QTimer

import DefineGlobal
from main_operator import MainOperator


class OPCWidget(QWidget):
    def __init__(self, main_operator: MainOperator):
        super().__init__()

        self.main_operator = main_operator
        self.opc_client = self.main_operator.opc_client

        # self.setWindowTitle("OPC Tag Manager")
        # self.setGeometry(100, 100, 800, 600)

        self.layout = QHBoxLayout()

        self.vlayout_left = QVBoxLayout()
        self.vlayout_right = QVBoxLayout()

        self.layout.addLayout(self.vlayout_left)
        self.layout.addLayout(self.vlayout_right)
        self.layout.setSpacing(6)

        self.setLayout(self.layout)

        # Create UI Components
        self.create_class_selection()
        self.create_tag_display()
        self.create_read_write_controls()
        self.create_update_toggle()

        # 최초 실행 시 업데이트 기능을 OFF
        self.update_checkbox.setChecked(False)
        self.update_timer.stop()

        # Left Layout
        # self.create_address_section()
        self.create_connection_section()

        self.vlayout_left.addStretch()

    def create_class_selection(self):
        self.class_selection_layout = QHBoxLayout()
        self.class_label = QLabel("Select Class:")
        self.class_combo = QComboBox()
        self.class_combo.addItems(["OPC_AGV_I_TAG", "OPC_O_TAG", "OPC_SPOT_AGV_BT_Data", "OPC_SPOT_I_RST",
                                   "OPC_SPOT_Heart_Bit", "OPC_SPOT_RB1_WRITE_DATA", "OPC_SPOT_RB2_WRITE_DATA",
                                   "OPC_S600_T_Reset", "OPC_SPOT_AGV_OUT_timer", "OPC_SPOT_I_AGV",
                                   "OPC_SPOT_I_RB", "OPC_SPOT_TEST_TIMER"])
        self.class_combo.setCurrentIndex(-1)
        self.class_combo.currentTextChanged.connect(self.update_tag_display)

        self.class_selection_layout.addWidget(self.class_label)
        self.class_selection_layout.addWidget(self.class_combo)
        self.vlayout_right.addLayout(self.class_selection_layout)

    def create_tag_display(self):
        self.tag_display = QTextEdit()

        tag_display_stylesheet = """
            background-color: rgba(102, 102, 102, 0.5);
            font-family: 'Consolas';
            font-size: 16pt;
        """

        self.tag_display.setStyleSheet(tag_display_stylesheet)
        self.tag_display.setReadOnly(True)
        self.vlayout_right.addWidget(self.tag_display)
        # self.update_tag_display()

    def create_read_write_controls(self):
        self.read_write_layout = QHBoxLayout()

        self.cbx_tag_input = QComboBox()
        self.cbx_tag_input.setMinimumWidth(300)
        self.read_button = QPushButton("Read Tag")
        self.write_button = QPushButton("Write Tag")
        self.value_input = QLineEdit()

        self.read_button.clicked.connect(self.read_tag)
        self.write_button.clicked.connect(self.write_tag)

        self.lbl_read_write_log = QLabel("")

        self.read_write_layout.addWidget(QLabel("Tag:"))
        self.read_write_layout.addWidget(self.cbx_tag_input)
        self.read_write_layout.addWidget(self.read_button)
        self.read_write_layout.addWidget(QLabel("Value:"))
        self.read_write_layout.addWidget(self.value_input)
        self.read_write_layout.addWidget(self.write_button)

        self.vlayout_right.addLayout(self.read_write_layout)
        self.vlayout_right.addWidget(self.lbl_read_write_log)

    def create_update_toggle(self):
        self.update_layout = QHBoxLayout()
        self.update_checkbox = QCheckBox("Auto Update")
        self.update_checkbox.stateChanged.connect(self.toggle_update)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_tag_display)

        self.update_layout.addWidget(self.update_checkbox)
        self.vlayout_right.addLayout(self.update_layout)

    def update_tag_display(self):
        current_class = self.class_combo.currentText()
        if not current_class:
            return

        cls = globals()[current_class]
        tags = [attr for attr in dir(cls) if not callable(getattr(cls, attr)) and not attr.startswith("__")]

        # READ TAG NAME ComboBox Update
        if not self.update_timer.isActive():
            self.cbx_tag_input.clear()

        tag_values = []
        tag_name_title = "TAG NAME"
        value_title = "VALUE"
        tag_values.append(f"{tag_name_title:^35}| \t{value_title}")
        tag_values.append(f"-"*50)
        for tag in tags:
            tag_full_name = getattr(cls, tag)
            value = self.opc_client.read_node_id(tag_full_name)
            tag_values.append(f"{tag:<35}| \t{value}")
            if not self.update_timer.isActive():
                self.cbx_tag_input.addItem(tag_full_name)

        self.tag_display.setPlainText("\n".join(tag_values))

    def read_tag(self):
        tag_name = self.cbx_tag_input.currentText()

        tag_full_name = tag_name
        value = self.opc_client.read_node_id(tag_full_name)
        self.value_input.setText(str(value))
        self.lbl_read_write_log.setText(f"Read Tag {tag_full_name}: {value}")

    def write_tag(self):
        tag_name = self.cbx_tag_input.currentText()
        # Todo: [MF] -> change to real server name
        tag_full_name = tag_name
        value = self.value_input.text()
        try:
            value = eval(value)
            self.opc_client.write_node_id(tag_full_name, value)
            self.lbl_read_write_log.setText(f"Written value: {value} Tag: {tag_full_name}")

        except Exception as e:
            self.lbl_read_write_log.setText(f"Error: {e}")

    def toggle_update(self):
        if self.update_checkbox.isChecked():
            self.update_timer.start(1000)  # 1초마다 갱신
        else:
            self.update_timer.stop()

    def create_address_section(self):
        vlayout_address = QVBoxLayout()
        lbl_address_title = QLabel("IP")
        lbl_address_title.setObjectName("subtitle")

        self.lbl_address_value = QTextEdit("192.168.1.84")
        self.lbl_address_value.setReadOnly(True)
        vlayout_address.addWidget(lbl_address_title)
        vlayout_address.addWidget(self.lbl_address_value)

        self.vlayout_left.addLayout(vlayout_address)

    def create_connection_section(self):
        # 통신 URL
        url_layout = QVBoxLayout()
        self.url_title = QLabel("OPC Endpoint URL")
        self.url_title.setObjectName("subtitle")
        self.url_value = QLabel(DefineGlobal.SERVER_URL)
        url_layout.addWidget(self.url_title)
        url_layout.addWidget(self.url_value)
        self.vlayout_left.addLayout(url_layout)

        # 통신 IP
        ip_layout = QVBoxLayout()
        self.ip_title = QLabel("IP Address")
        self.ip_title.setObjectName("subtitle")
        self.ip_value = QLabel("192.168.1.83")
        ip_layout.addWidget(self.ip_title)
        ip_layout.addWidget(self.ip_value)
        self.vlayout_left.addLayout(ip_layout)

        # 연결 상태
        connect_layout = QVBoxLayout()
        self.lbl_connection_title = QLabel("CONNECT")
        self.lbl_connection_title.setObjectName("subtitle")
        self.lbl_connection_status = QLabel("DISCONNECTED")
        connect_layout.addWidget(self.lbl_connection_title)
        connect_layout.addWidget(self.lbl_connection_status)
        self.vlayout_left.addLayout(connect_layout)

        # Connection Button
        self.btn_opc_connect    = QPushButton("Connect")
        self.btn_opc_disconnect = QPushButton("Disconnect")
        self.btn_opc_connect.clicked.connect(self.check_opc_connect)
        self.btn_opc_disconnect.clicked.connect(self.check_opc_disconnect)

        self.vlayout_left.addWidget(self.btn_opc_connect)
        self.vlayout_left.addWidget(self.btn_opc_disconnect)

    def check_opc_connect(self):
        self.main_operator.opc_connect()

    def check_opc_disconnect(self):
        self.main_operator.opc_disconnect()

    def set_connection_status(self, status):
        self.lbl_connection_status.setText(status)
        if status == "CONNECTED":
            self.lbl_connection_status.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: lime;
                font-size: 16px;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
            """)
        else:
            self.lbl_connection_status.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: red;
                font-size: 16px;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
            """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_widget = OPCWidget()
    main_widget.show()
    sys.exit(app.exec_())


# NEW WIDGET

# from PySide2.QtCore import Qt
# from PySide2.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QGroupBox, QSplitter, QLineEdit, QComboBox, QPushButton, QTextEdit, QCheckBox
#
# import DefineGlobal
#
#
# class OPCWidget(QWidget):
#     def __init__(self, main_operator):
#         super().__init__()
#         self.main_operator = main_operator
#
#         # 메인 레이아웃 생성
#         main_layout = QVBoxLayout()
#
#         # OPC STATUS 제목
#         lbl_opc_title = QLabel("OPC STATUS")
#         lbl_opc_title.setAlignment(Qt.AlignCenter)
#
#         main_layout.addWidget(lbl_opc_title)
#
#         # QSplitter로 5:5 비율로 나누기
#         splitter = QSplitter(Qt.Horizontal)
#
#         # 왼쪽 레이아웃
#         left_layout = QVBoxLayout()
#
#         # 통신 URL
#         url_layout = QVBoxLayout()
#         self.url_title = QLabel("OPC Endpoint URL")
#         self.url_title.setObjectName("subtitle")
#         self.url_value = QLabel(DefineGlobal.SERVER_URL)
#         url_layout.addWidget(self.url_title)
#         url_layout.addWidget(self.url_value)
#         left_layout.addLayout(url_layout)
#
#         # 통신 IP
#         ip_layout = QVBoxLayout()
#         self.ip_title = QLabel("IP Address")
#         self.ip_title.setObjectName("subtitle")
#         self.ip_value = QLabel("192.168.1.83")
#         ip_layout.addWidget(self.ip_title)
#         ip_layout.addWidget(self.ip_value)
#         left_layout.addLayout(ip_layout)
#
#         # 연결 상태
#         connect_layout = QVBoxLayout()
#         self.connect_title = QLabel("CONNECT")
#         self.connect_title.setObjectName("subtitle")
#         self.lbl_connect_value = QLabel("DISCONNECTED")
#         connect_layout.addWidget(self.connect_title)
#         connect_layout.addWidget(self.lbl_connect_value)
#         left_layout.addLayout(connect_layout)
#
#         # 태그 리스트
#         tag_layout = QVBoxLayout()
#         self.tag_list_title = QLabel("Tag List")
#         self.tag_list_title.setObjectName("subtitle")
#         self.tag_combobox = QComboBox()
#         tag_layout.addWidget(self.tag_list_title)
#         tag_layout.addWidget(self.tag_combobox)
#         left_layout.addLayout(tag_layout)
#
#         # TAG 읽기 기능
#         self.read_button = QPushButton("Read Tag")
#         left_layout.addWidget(self.read_button)
#
#         # TAG 쓰기 기능
#         self.write_button = QPushButton("Write Tag")
#         left_layout.addWidget(self.write_button)
#         left_layout.addStretch()
#
#         # 왼쪽 레이아웃을 QWidget에 설정
#         left_widget = QWidget()
#         left_widget.setLayout(left_layout)
#         splitter.addWidget(left_widget)
#
#         # 오른쪽 레이아웃
#         right_layout = QVBoxLayout()
#
#         # 결과 창
#         result_layout = QVBoxLayout()
#         self.lbl_result_title = QLabel("Results")
#         self.lbl_result_title.setObjectName("subtitle")
#         self.result_text = QTextEdit()
#         result_layout.addWidget(self.lbl_result_title)
#         result_layout.addWidget(self.result_text)
#         right_layout.addLayout(result_layout)
#
#         # 실시간 갱신 창
#         realtime_layout = QVBoxLayout()
#         self.realtime_title = QLabel("Real-Time Updates")
#         self.realtime_title.setObjectName("subtitle")
#         self.realtime_text = QTextEdit()
#         realtime_layout.addWidget(self.realtime_title)
#         realtime_layout.addWidget(self.realtime_text)
#         right_layout.addLayout(realtime_layout)
#
#         # 실시간 갱신 선택
#         self.realtime_checkbox = QCheckBox("Enable Real-Time Updates")
#         right_layout.addWidget(self.realtime_checkbox)
#
#         # 로그 창
#         log_layout = QVBoxLayout()
#         self.lbl_log_title = QLabel("Log")
#         self.lbl_log_title.setObjectName("subtitle")
#         self.log_text = QTextEdit()
#         log_layout.addWidget(self.lbl_log_title)
#         log_layout.addWidget(self.log_text)
#         right_layout.addLayout(log_layout)
#
#         # 오른쪽 레이아웃을 QWidget에 설정
#         right_widget = QWidget()
#         right_widget.setLayout(right_layout)
#         splitter.addWidget(right_widget)
#
#         # 스플리터 비율 설정
#         splitter.setStretchFactor(0, 5)
#         splitter.setStretchFactor(1, 5)
#
#         # 스플리터를 메인 레이아웃에 추가
#         main_layout.addWidget(splitter)
#
#         self.setLayout(main_layout)
#
#         # 스타일 시트 적용
#         # self.setStyleSheet("""
#         #     QGroupBox {
#         #         font-family: '현대하모니 M';
#         #         font: bold;
#         #         color: white;
#         #         border: 0px solid silver;
#         #         border-radius: 6px;
#         #         margin: 5px;
#         #     }
#         #     QGroupBox::title {
#         #         color: white;
#         #         subcontrol-origin: margin;
#         #         subcontrol-position: top center;
#         #         padding: 0 3px;
#         #     }
#         #     QLabel {
#         #         font-family: '현대하모니 L';
#         #         font-size: 14px;
#         #         padding: 2px;
#         #     }
#         #     QTextEdit {
#         #         font-family: '현대하모니 L';
#         #         font-size: 14px;
#         #         padding: 2px;
#         #         color: black;
#         #         background-color: white;
#         #     }
#         #     QCheckBox {
#         #         font-family: '현대하모니 L';
#         #         font-size: 14px;
#         #         padding: 2px;
#         #         color: white;
#         #     }
#         #     QComboBox {
#         #         font-family: '현대하모니 L';
#         #         font-size: 14px;
#         #         padding: 2px;
#         #         color: black;
#         #         background-color: white;
#         #     }
#         #     QPushButton {
#         #         font-family: '현대하모니 L';
#         #         font-size: 14px;
#         #         padding: 2px;
#         #         color: white;
#         #         background-color: #0078d7;
#         #         border: none;
#         #         border-radius: 4px;
#         #     }
#         #     QPushButton:hover {
#         #         background-color: #005bb5;
#         #     }
#         #     QPushButton:pressed {
#         #         background-color: #003f8c;
#         #     }
#         # """)
#
#     def set_connection_status(self, status):
#         self.lbl_connect_value.setText(status)
#         if status == "CONNECTED":
#             self.lbl_connect_value.setStyleSheet("""
#                 font-family: '현대하모니 L';
#                 color: white;
#                 background-color: lime;
#                 font-size: 16px;
#                 font-weight: bold;
#                 padding: 4px;
#                 border-radius: 4px;
#             """)
#         else:
#             self.lbl_connect_value.setStyleSheet("""
#                 font-family: '현대하모니 L';
#                 color: white;
#                 background-color: red;
#                 font-size: 16px;
#                 font-weight: bold;
#                 padding: 4px;
#                 border-radius: 4px;
#             """)
#
#
# if __name__ == "__main__":
#     from PySide2.QtWidgets import QApplication
#     import sys
#
#     app = QApplication(sys.argv)
#     window = OPCStatusWidget()
#     window.show()
#     sys.exit(app.exec_())
#



