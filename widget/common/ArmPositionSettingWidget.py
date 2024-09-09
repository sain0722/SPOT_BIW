import json

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog
from PySide6.QtCore import Qt

class ArmPositionSettingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout()

        self.lbl_title = QLabel("Arm Position Setting")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_title)

        self.hlayout_sh0 = QHBoxLayout()
        self.hlayout_sh1 = QHBoxLayout()
        self.hlayout_el0 = QHBoxLayout()
        self.hlayout_el1 = QHBoxLayout()
        self.hlayout_wr0 = QHBoxLayout()
        self.hlayout_wr1 = QHBoxLayout()

        self.lbl_sh0 = QLabel("sh0")
        self.lbl_sh1 = QLabel("sh1")
        self.lbl_el0 = QLabel("el0")
        self.lbl_el1 = QLabel("el1")
        self.lbl_wr0 = QLabel("wr0")
        self.lbl_wr1 = QLabel("wr1")

        self.line_edit_sh1_value = QLineEdit("{value}")
        self.line_edit_sh0_value = QLineEdit("{value}")
        self.line_edit_el0_value = QLineEdit("{value}")
        self.line_edit_el1_value = QLineEdit("{value}")
        self.line_edit_wr0_value = QLineEdit("{value}")
        self.line_edit_wr1_value = QLineEdit("{value}")

        self.hlayout_sh0.addWidget(self.lbl_sh0)
        self.hlayout_sh0.addWidget(self.line_edit_sh0_value)
        self.hlayout_sh1.addWidget(self.lbl_sh1)
        self.hlayout_sh1.addWidget(self.line_edit_sh1_value)
        self.hlayout_el0.addWidget(self.lbl_el0)
        self.hlayout_el0.addWidget(self.line_edit_el0_value)
        self.hlayout_el1.addWidget(self.lbl_el1)
        self.hlayout_el1.addWidget(self.line_edit_el1_value)
        self.hlayout_wr0.addWidget(self.lbl_wr0)
        self.hlayout_wr0.addWidget(self.line_edit_wr0_value)
        self.hlayout_wr1.addWidget(self.lbl_wr1)
        self.hlayout_wr1.addWidget(self.line_edit_wr1_value)

        self.hlayout_sh0.setStretch(0, 1)
        self.hlayout_sh0.setStretch(1, 1)
        self.hlayout_sh1.setStretch(0, 1)
        self.hlayout_sh1.setStretch(1, 1)
        self.hlayout_el0.setStretch(0, 1)
        self.hlayout_el0.setStretch(1, 1)
        self.hlayout_el1.setStretch(0, 1)
        self.hlayout_el1.setStretch(1, 1)
        self.hlayout_wr0.setStretch(0, 1)
        self.hlayout_wr0.setStretch(1, 1)
        self.hlayout_wr1.setStretch(0, 1)
        self.hlayout_wr1.setStretch(1, 1)

        self.hlayout_buttons = QHBoxLayout()
        self.btn_apply_position = QPushButton("Apply Current Arm Pose")
        self.btn_load_position = QPushButton("Load (.json)")
        self.btn_save_position = QPushButton("Save (.json)")

        self.hlayout_buttons.addWidget(self.btn_apply_position)
        self.hlayout_buttons.addWidget(self.btn_load_position)
        self.hlayout_buttons.addWidget(self.btn_save_position)

        self.hlayout_act_buttons = QHBoxLayout()
        self.btn_deploy = QPushButton("Deploy")
        self.btn_stow = QPushButton("Stow")
        self.btn_capture = QPushButton("Capture")

        self.hlayout_act_buttons.addWidget(self.btn_deploy)
        self.hlayout_act_buttons.addWidget(self.btn_stow)
        self.hlayout_act_buttons.addWidget(self.btn_capture)

        self.main_layout.addLayout(self.hlayout_sh0)
        self.main_layout.addLayout(self.hlayout_sh1)
        self.main_layout.addLayout(self.hlayout_el0)
        self.main_layout.addLayout(self.hlayout_el1)
        self.main_layout.addLayout(self.hlayout_wr0)
        self.main_layout.addLayout(self.hlayout_wr1)
        self.main_layout.addLayout(self.hlayout_buttons)
        self.main_layout.addLayout(self.hlayout_act_buttons)
        self.main_layout.addStretch(1)

        self.setLayout(self.main_layout)

    def apply_current_position(self, function):
        self.btn_apply_position.clicked.connect(function)

    def execute_load_arm_status(self, function):
        self.btn_load_position.clicked.connect(function)

    def execute_joint_move(self, function):
        self.btn_deploy.clicked.connect(function)

    def execute_stow(self, function):
        self.btn_stow.clicked.connect(function)

    def execute_capture(self, function):
        self.btn_capture.clicked.connect(function)

    def execute_save_arm_status(self, function):
        self.btn_save_position.clicked.connect(function)

    def show_load_dialog(self, position: str):
        joint_pos_dict = self.load_arm_status()
        if joint_pos_dict:
            self.write_arm_position(position, joint_pos_dict)
            self.setup_arm_values(position, joint_pos_dict.values())

    @staticmethod
    def load_arm_status() -> dict:
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("JSON Files (*.json)")
        if dialog.exec_():
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                with open(file_path, 'r') as file:
                    data = json.load(file)
                return data

