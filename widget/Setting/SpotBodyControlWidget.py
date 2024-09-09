from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from biw_utils.decorators import arm_control_exception_decorator


class SpotBodyControlWidget(QWidget):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.move_manager = self.main_operator.spot_robot.robot_move_manager
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Robot Movement Control")
        self.layout = QVBoxLayout()
        self.info_label = QLabel("Use WASD for lateral movements, QE for turn movements, N: battery change pose, M: selfright")
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
            self.strafe_left()
        elif key == Qt.Key_D:
            self.strafe_right()
        elif key == Qt.Key_Q:
            self.turn_left()
        elif key == Qt.Key_E:
            self.turn_right()
        elif key == Qt.Key_N:
            self.battery_change_pose()
        elif key == Qt.Key_M:
            self.selfright()

    @arm_control_exception_decorator
    def move_forward(self):
        self.status_label.setText("Moving forward")
        result = self.move_manager.move_forward()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_backward(self):
        self.status_label.setText("Moving forward")
        result = self.move_manager.move_backward()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def strafe_left(self):
        self.status_label.setText("strafe_left")
        result = self.move_manager.strafe_left()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def strafe_right(self):
        self.status_label.setText("strafe_right")
        result = self.move_manager.strafe_right()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def move_forward_left(self):
        self.status_label.setText("move_forward_left")
        result = self.move_manager.move_forward_left()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def turn_left(self):
        self.status_label.setText("turn_left")
        result = self.move_manager.turn_left()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def turn_right(self):
        self.status_label.setText("turn_right")
        result = self.move_manager.turn_right()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def selfright(self):
        self.status_label.setText("selfright")
        result = self.move_manager.selfright()
        self.status_label.setText(str(result))

    @arm_control_exception_decorator
    def battery_change_pose(self):
        self.status_label.setText("battery_change_pose")
        result = self.move_manager.battery_change_pose()
        self.status_label.setText(str(result))


"""
strafe_left
strafe_right
turn_left
turn_right
selfright
battery_change_pose
"""