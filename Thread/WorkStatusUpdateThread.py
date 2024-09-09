import time

from PySide6.QtCore import QThread, Signal

import DefineGlobal


class WorkStatusUpdateThread(QThread):
    progress_update_work_status = Signal(DefineGlobal.WORK_STATUS)
    progress_update_work_complete_status = Signal(bool)

    def __init__(self, opc_client):
        super().__init__()
        self.opc_client = opc_client
        self._running = True
        self.previous_status = DefineGlobal.WORK_STATUS.NONE
        self.previous_work_complete_status = False
        self.spot_position = DefineGlobal.SPOT_POSITION

    def run(self):
        while self._running:
            if not self.opc_client.connected:
                time.sleep(.5)
                continue

            if DefineGlobal.CURRENT_WORK_STATUS != self.previous_status:
                self.previous_status = DefineGlobal.CURRENT_WORK_STATUS
                self.progress_update_work_status.emit(DefineGlobal.CURRENT_WORK_STATUS)

            if self.spot_position == DefineGlobal.BIW_POSITION.RH:
                DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = self.opc_client.read_node_id(DefineGlobal.OPC_SPOT_RB1_WRITE_DATA.S600_SPOT_RB1_I_LAST_WORK_COMP)
            else:
                DefineGlobal.CURRENT_WORK_COMPLETE_STATUS = self.opc_client.read_node_id(DefineGlobal.OPC_SPOT_RB2_WRITE_DATA.S600_SPOT_RB2_I_LAST_WORK_COMP)

            self.progress_update_work_complete_status.emit(DefineGlobal.CURRENT_WORK_COMPLETE_STATUS)
            time.sleep(.5)  # 1초마다 업데이트

    def stop(self):
        self._running = False
        self.quit()
        self.wait()

