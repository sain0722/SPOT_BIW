from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QLabel, QPushButton


class DisconnectDialog(QDialog):
    def __init__(self):
        super().__init__()

        # 제목 표시줄 없애기
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        # 레이아웃 설정
        layout = QVBoxLayout()

        # 라벨 추가
        label = QLabel("SPOT DISCONNECT.")
        label.setAlignment(Qt.AlignCenter)
        # label.setStyleSheet("""
        #
        # """)
        label.setFont(QFont("현대하모니 M", 36))
        layout.addWidget(label)

        # 버튼 추가
        # button = QPushButton("TEST")
        # button.clicked.connect(self.close)
        # layout.addWidget(button)

        self.setLayout(layout)

        # 다이얼로그 크기 설정
        self.resize(300, 200)
