import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from Spot.SpotArm import SpotArm
from biw_utils.decorators import arm_control_exception_decorator


class SpotArmControlWidget(QWidget):
    def __init__(self, main_operator):
        super().__init__()
        self.arm_manager = main_operator.spot_robot.robot_arm_manager
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Robot Movement Control")
        # self.setGeometry(100, 100, 300, 100)
        self.layout = QVBoxLayout()
        self.info_label = QLabel("Use WASD for lateral movements, RF for vertical movements, Y/N for stow/unstow, O/P for gripper.")
        self.status_label = QLabel("Status: Ready")

        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.status_label)
        self.setLayout(self.layout)

        # Set the focus policy to accept key events
        self.setFocusPolicy(Qt.StrongFocus)
        self.init_shortcut()

    def init_shortcut(self):
        # shortcut_move_left = QShortcut(QKeySequence("g"), self)
        # shortcut_move_left.activated.connect(self.move_forward_left)
        # TODO: 대각선 이동 추가
        pass

    def keyPressEvent(self, event):
        # Handle key press for continuous movement
        self.handle_movement(event.key())

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():  # Ignore auto-repeat events
            self.status_label.setText("Status: Ready")

    def handle_movement(self, key):
        if key == Qt.Key_W:
            self.move_forward()
        elif key == Qt.Key_S:
            self.move_backward()
        elif key == Qt.Key_A:
            self.move_left()
        elif key == Qt.Key_D:
            self.move_right()
        elif key == Qt.Key_R:
            self.move_up()
        elif key == Qt.Key_F:
            self.move_down()
        elif key == Qt.Key_Y:
            self.unstow()
        elif key == Qt.Key_N:
            self.stow()
        elif key == Qt.Key_O:
            self.gripper_open()
        elif key == Qt.Key_P:
            self.gripper_close()

    @arm_control_exception_decorator
    def move_forward(self):
        self.status_label.setText("Moving forward")
        result = self.arm_manager.move_out()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_backward(self):
        self.status_label.setText("Moving backward")
        result = self.arm_manager.move_in()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_left(self):
        self.status_label.setText("Moving left")
        result = self.arm_manager.rotate_ccw()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_right(self):
        self.status_label.setText("Moving right")
        result = self.arm_manager.rotate_cw()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_up(self):
        self.status_label.setText("Moving up")
        result = self.arm_manager.move_up()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_down(self):
        self.status_label.setText("Moving down")
        result = self.arm_manager.move_down()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def stow(self):
        self.status_label.setText("Stow")
        result = self.arm_manager.stow()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def unstow(self):
        self.status_label.setText("Unstow")
        result = self.arm_manager.unstow()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def gripper_open(self):
        self.status_label.setText("Gripper Open")
        result = self.arm_manager.gripper_open()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def gripper_close(self):
        self.status_label.setText("Gripper Close")
        result = self.arm_manager.gripper_close()
        self.status_label.setText(str(result))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = SpotArmControlWidget(SpotArm())  # Assuming SpotArm is properly initialized
    ex.show()
    sys.exit(app.exec_())
