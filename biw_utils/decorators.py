from PySide6.QtWidgets import QMessageBox
from bosdyn.client.graph_nav import RobotImpairedError
from bosdyn.client.power import KeepaliveMotorsOffError, EstoppedError

from biw_utils import util_functions


def exception_decorator(method):
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args)

        except AttributeError as disconnected_error:
            message = "SPOT is disconnected."
            msg_box = QMessageBox()
            method(self)
            msg_box.information(None, "Error", message, QMessageBox.Ok)

        except KeepaliveMotorsOffError as keepalive_error:
            util_functions.show_message(text=f"{keepalive_error}")

        except EstoppedError as estop_error:
            util_functions.show_message(text=f"{estop_error}")

        except RobotImpairedError as robot_impaired_error:
            util_functions.show_message(text=f"{robot_impaired_error}")

        except Exception as E:
            print("[Error]:", E)
            if type(self).__name__ == 'MainOperator':
                self.write_log(str(E))
            else:
                msg_box = QMessageBox()
                method(self)
                msg_box.information(None, "Error", str(E), QMessageBox.Ok)

    return wrapper


def arm_control_exception_decorator(method):
    def wrapper(self):
        try:
            return method(self)

        except AttributeError as disconnected_error:
            message = "SPOT is disconnected."
            # self.status_label.setText(message)
            self.main_operator.write_log(message)

        except Exception as E:
            # self.status_label.setText(str(E))
            self.main_operator.write_log(E)

    return wrapper


def user_input_decorator(method):
    def wrapper(self):
        msg_box = QMessageBox()
        try:
            method(self)
            message = "Complete."
            msg_box.information(None, "Information", message, QMessageBox.Ok)

        except Exception as E:
            message = str(E)
            msg_box.critical(None, "Error", message, QMessageBox.Ok)

    return wrapper


def spot_connection_check(method):
    def wrapper(self):
        msg_box = QMessageBox()
        message = f"{method.__name__}"
        try:
            method(self)
        except AttributeError as disconnected_error:
            message = "SPOT is disconnected. Check SPOT Connection."
            util_functions.show_message(text=message)
        except Exception as E:
            message = str(E)
            util_functions.show_message(text=message)

    return wrapper
