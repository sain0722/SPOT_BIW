import queue
import threading

from bosdyn.client.estop import EstopEndpoint, EstopKeepAlive, MotorsOnError


class SpotEstop:
    """
    """
    def __init__(self):
        self.estop_client = None
        self.estop_endpoint = None
        self.estop_keepalive = None

    def initialize(self, client):
        self.estop_client = client

    def start_estop(self):
        """
        """
        try:
            self.estop_endpoint = EstopEndpoint(self.estop_client, 'TWIM_ESTOP', 9.0)
            self.estop_endpoint.force_simple_setup()
            self.estop_keepalive = EstopKeepAlive(self.estop_endpoint)
            self.release_estop()
            return True

        except MotorsOnError as motor_on_error:
            print(f"[SpotEstop.py] - Start E-STOP Raised Exception. MotorOnError: \n{motor_on_error}")
            raise motor_on_error

        except Exception as e:
            print(f"[SpotEstop.py] - Start E-STOP Raised Exception. {e}")
            return False

    def return_estop(self):
        try:
            self.estop_keepalive.shutdown()
            self.estop_endpoint = None
            self.estop_keepalive = None
            return True
        except Exception as e:
            print(f"[SpotEstop.py] - Return E-STOP Raised Exception. {e}")
            return False

    def release_estop(self):
        if self.estop_keepalive:
            self.estop_keepalive.allow()

    def stop_estop(self):
        if self.estop_keepalive:
            self.estop_keepalive.settle_then_cut()
            self.estop_keepalive.stop()

    def get_keep_alive_status(self):
        if not self.estop_keepalive:
            return "OFF"

        try:
            status, msg = self.estop_keepalive.status_queue.get(timeout=1)  # blocking
        except queue.Empty:
            return ""

        if status == EstopKeepAlive.KeepAliveStatus.OK:
            return "Alive"
        elif status == EstopKeepAlive.KeepAliveStatus.ERROR:
            return "Error"
        elif status == EstopKeepAlive.KeepAliveStatus.DISABLED:
            return "Disabled"
        else:
            return "None"
