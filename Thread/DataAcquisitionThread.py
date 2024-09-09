from PySide6.QtCore import QThread, Signal


class DataAcquisitionThread(QThread):
    event_run_process = Signal()
    event_battery_check = Signal()
    event_completed = Signal()

    def __init__(self, process_manager):
        super().__init__()
        self.process_manager = process_manager
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.event_run_process.emit()

            # Battery Check
            is_battery_low = self.event_battery_check.emit()
            if is_battery_low:
                self.stop()
                break

            # Go home
            self.event_completed.emit()

    def stop(self):
        self.running = False
