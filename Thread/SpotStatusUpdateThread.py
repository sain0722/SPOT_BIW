import time

from PySide6.QtCore import QThread, Signal

from Spot.SpotRobot import Robot


class SpotStatusUpdateThread(QThread):
    progress = Signal(str, str, str, int, str, bool, bool, str, str)

    def __init__(self, spot_robot: Robot, parent=None):
        super().__init__(parent)
        self.spot_robot = spot_robot
        self._running = True

    def run(self):
        while self._running:
            try:
                lease = self.spot_robot.command_dictionary["get_lease"]()
                power = self.spot_robot.command_dictionary["get_power"]()
                status, bar_val, time_left = self.spot_robot.command_dictionary["get_battery"]()
                is_connected = self.spot_robot.is_connected
                is_localized = self.spot_robot.robot_graphnav_manager.is_localized()
                estop_status, sw_estop_status = self.spot_robot.command_dictionary["get_estop"]()
            except Exception as e:
                print(e)
                lease = ""
                power = ""
                status, bar_val, time_left = "", 0, ""
                is_connected = "?"
                is_localized = "?"
                estop_status = "?"

            self.progress.emit(lease, power, status, bar_val, time_left, is_connected, is_localized, estop_status, sw_estop_status)
            time.sleep(1)  # 1초마다 업데이트

    def stop(self):
        self._running = False
        self.quit()
        self.wait()
