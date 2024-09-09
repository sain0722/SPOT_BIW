from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QGroupBox


class OPCStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 메인 레이아웃 생성
        main_layout = QVBoxLayout()

        # OPC STATUS 제목
        lbl_opc_title = QLabel("OPC STATUS")
        lbl_opc_title.setAlignment(Qt.AlignCenter)
        lbl_opc_title.setStyleSheet("""
        font-family: '현대하모니 M';
        font-size: 16pt;
        font-weight: bold;
        margin: 10px 0;
        background-color: transparent
        """)

        main_layout.addWidget(lbl_opc_title)

        # 수평 레이아웃 생성
        header_layout = QHBoxLayout()

        # # CONNECT 그룹
        self.connect_group = QGroupBox("CONNECT")
        connect_layout = QVBoxLayout()
        self.lbl_connect_value = QLabel("DISCONNECTED")
        self.lbl_connect_value.setStyleSheet("font-family: '현대하모니 L';")
        connect_layout.addWidget(self.lbl_connect_value)
        self.connect_group.setLayout(connect_layout)
        header_layout.addWidget(self.connect_group)

        main_layout.addLayout(header_layout)

        self.setLayout(main_layout)

        # 스타일 시트 적용
        self.setStyleSheet("""
            QGroupBox {
                font-family: '현대하모니 M';
                font: bold;
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

    def set_connection_status(self, status):
        self.lbl_connect_value.setText(status)
        if status == "CONNECTED":
            self.lbl_connect_value.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: lime;
                font-size: 16px;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
            """)
        else:
            self.lbl_connect_value.setStyleSheet("""
                font-family: '현대하모니 L';
                color: white;
                background-color: red;
                font-size: 16px;
                font-weight: bold;
                padding: 4px;
                border-radius: 4px;
            """)






