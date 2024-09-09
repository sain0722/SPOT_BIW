import sys
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel

class WorkerThread(QThread):
    progress = Signal(int)

    def run(self):
        for i in range(100):
            print(f"Worker thread running: {i}")  # 중단점 테스트 위치 1
            self.sleep(1)
            self.progress.emit(i)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

        # QThread를 이용한 백그라운드 작업 실행
        self.worker = WorkerThread()
        self.worker.progress.connect(self.update_label)
        self.worker.start()

    def initUI(self):
        self.setWindowTitle("PySide6 Debug Test")

        self.label = QLabel("Click the button to test breakpoint")
        self.button = QPushButton("Test Breakpoint")
        self.button.clicked.connect(self.on_button_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def on_button_clicked(self):
        print("Button clicked!")  # 중단점 테스트 위치 2
        self.label.setText("Button was clicked!")

    def update_label(self, value):
        self.label.setText(f"Worker thread value: {value}")  # 중단점 테스트 위치 3

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
