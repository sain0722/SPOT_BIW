from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setWindowIcon(QIcon('resources/BIW_logo.png'))
        layout = QVBoxLayout()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)  # Set echo mode to hide password

        button_box = QDialogButtonBox(self)
        button_box.setOrientation(Qt.Horizontal)
        button_box.setStandardButtons(QDialogButtonBox.Ok)

        button_box.accepted.connect(self.accept)

        layout.addWidget(self.password_edit)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.password_edit.setFocus()

    def get_password(self):
        return self.password_edit.text()
