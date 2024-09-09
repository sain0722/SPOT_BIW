import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit, QCheckBox, QComboBox
from PySide6.QtCore import QTimer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPC Tag Manager")
        self.setGeometry(100, 100, 800, 600)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Create UI Components
        self.create_class_selection()
        self.create_tag_display()
        self.create_read_write_controls()
        self.create_update_toggle()

    def create_class_selection(self):
        self.class_selection_layout = QHBoxLayout()
        self.class_label = QLabel("Select Class:")
        self.class_combo = QComboBox()
        self.class_combo.addItems(["OPC_AGV_I_TAG", "OPC_O_TAG", "OPC_SPOT_AGV_BT_Data", "OPC_SPOT_I_RST",
                                   "OPC_SPOT_Heart_Bit", "OPC_SPOT_RB1_WRITE_DATA", "OPC_SPOT_RB2_WRITE_DATA",
                                   "OPC_S600_T_Reset", "OPC_SPOT_AGV_OUT_timer", "OPC_SPOT_I_AGV",
                                   "OPC_SPOT_I_RB", "OPC_SPOT_TEST_TIMER"])
        self.class_combo.currentTextChanged.connect(self.update_tag_display)

        self.class_selection_layout.addWidget(self.class_label)
        self.class_selection_layout.addWidget(self.class_combo)
        self.layout.addLayout(self.class_selection_layout)

    def create_tag_display(self):
        self.tag_display = QTextEdit()
        self.tag_display.setReadOnly(True)
        self.layout.addWidget(self.tag_display)
        # self.update_tag_display()

    def create_read_write_controls(self):
        self.read_write_layout = QHBoxLayout()

        self.tag_input = QLineEdit()
        self.read_button = QPushButton("Read Tag")
        self.write_button = QPushButton("Write Tag")
        self.value_input = QLineEdit()

        self.read_button.clicked.connect(self.read_tag)
        self.write_button.clicked.connect(self.write_tag)

        self.read_write_layout.addWidget(QLabel("Tag:"))
        self.read_write_layout.addWidget(self.tag_input)
        self.read_write_layout.addWidget(self.read_button)
        self.read_write_layout.addWidget(QLabel("Value:"))
        self.read_write_layout.addWidget(self.value_input)
        self.read_write_layout.addWidget(self.write_button)

        self.layout.addLayout(self.read_write_layout)

    def create_update_toggle(self):
        self.update_layout = QHBoxLayout()
        self.update_checkbox = QCheckBox("Auto Update")
        self.update_checkbox.stateChanged.connect(self.toggle_update)
        # self.update_timer = QTimer(self)
        # self.update_timer.timeout.connect(self.update_tag_display)

        self.update_layout.addWidget(self.update_checkbox)
        self.layout.addLayout(self.update_layout)

    def update_tag_display(self):
        current_class = self.class_combo.currentText()
        tags = [attr for attr in dir(eval(current_class)) if not callable(getattr(eval(current_class), attr)) and not attr.startswith("__")]
        self.tag_display.setPlainText("\n".join(tags))

    def read_tag(self):
        tag_name = self.tag_input.text()
        # OPC 서버에서 태그 읽기 로직 추가
        # value = opc_client.read(tag_name)
        value = "Read value (예시)"
        self.value_input.setText(value)

    def write_tag(self):
        tag_name = self.tag_input.text()
        value = self.value_input.text()
        # OPC 서버에 태그 쓰기 로직 추가
        # opc_client.write(tag_name, value)
        pass

    def toggle_update(self):
        if self.update_checkbox.isChecked():
            self.update_timer.start(1000)  # 1초마다 갱신
        else:
            self.update_timer.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
