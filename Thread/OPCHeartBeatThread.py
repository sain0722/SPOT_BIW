import time
from PySide6.QtCore import QThread, Signal

from communication.OPC.opc_client import BIWOPCUAClient


class HeartbeatThread(QThread):
    heartbeat_signal = Signal(bool)

    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.running = True

    def run(self):
        previous_heartbeat = None
        while self.running:
            # if not self.main_operator.opc_client.connected:
            #     self.main_operator.opc_connect()

            # st_time = time.time()
            # while st_time + 5 >= time.time():
            #     time.sleep(0.5)  # 0.5초마다 서버 상태 확인
            #     current_heartbeat = self.main_operator.opc_client.check_heartbeat()
            #     if current_heartbeat:
            #         continue
            #     else:
            #         self.heartbeat_signal.emit(False)

            current_heartbeat = self.main_operator.opc_client.check_heartbeat()
            # self.main_operator.opc_client.do_heartbeat(current_heartbeat)

            if current_heartbeat:
                self.heartbeat_signal.emit(True)
            else:
                self.heartbeat_signal.emit(False)

            time.sleep(0.5)
            # TODO: heartbeat 값에 따른 처리 (필요한 경우)
            # if current_heartbeat is None or (previous_heartbeat is not None and previous_heartbeat == current_heartbeat):
            #     self.heartbeat_signal.emit(False)
            #     self.main_operator.opc_client.connected = False
            #     self.main_operator.opc_disconnect()
            #     time.sleep(1)
            #     self.main_operator.opc_connect()
            # else:
            #     self.heartbeat_signal.emit(True)

            # previous_heartbeat = current_heartbeat

    def stop(self):
        self.running = False


class HeartbeatWriteThread(QThread):
    def __init__(self, opc_client: BIWOPCUAClient):
        super().__init__()
        self.client = opc_client
        self.running = True

    def run(self):
        while self.running:
            self.client.write_node_id()