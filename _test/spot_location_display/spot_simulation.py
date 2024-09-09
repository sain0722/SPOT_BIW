import sys
import random
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import QTimer, QThread, Signal, Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.image as mpimg

# 지정된 waypoints
waypoints = {
    'waypoint_1': (20, 20),
    'waypoint_2': (20, 40),
    'waypoint_3': (20, 60),
    'waiting': (20, 10),
    'docking_station': (10, 10)
}

# Waypoint 순서 (inspection 추가)
waypoint_order = ['waypoint_1', 'inspection', 'waypoint_2', 'inspection', 'waypoint_3', 'inspection', 'waiting',
                  'docking_station']


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        self.init_map()

    def init_map(self):
        self.axes.set_xlim(0, 100)
        self.axes.set_ylim(0, 100)
        self.axes.set_aspect('equal')
        self.axes.axis('off')  # 축 숨기기


class DataThread(QThread):
    location_update = Signal(float, float, str)
    status_update = Signal(str)
    battery_update = Signal(int)

    def __init__(self):
        super().__init__()
        self.current_waypoint_index = 0
        self.battery_level = 100  # 초기 배터리 상태
        self.docking = False

    def run(self):
        while True:
            # 배터리 상태 업데이트
            self.battery_level -= random.randint(1, 5)
            if self.battery_level < 0:
                self.battery_level = 100  # 배터리 충전 시뮬레이션
            self.battery_update.emit(self.battery_level)

            # 배터리 상태에 따른 위치 업데이트
            if self.battery_level <= 20:
                waypoint_name = 'docking_station'
                self.docking = True
                self.status_update.emit('도킹 중...')
            else:
                if self.docking:
                    # 배터리가 20% 이상으로 충전되었으면 docking 상태 해제
                    self.docking = False
                    self.current_waypoint_index = 0
                waypoint_name = waypoint_order[self.current_waypoint_index]

            if waypoint_name == 'inspection':
                # Inspection 중임을 알리기 위해 특별한 신호를 보냄
                self.location_update.emit(None, None, 'inspection')
                self.status_update.emit('검사 중...')
            else:
                new_x, new_y = waypoints[waypoint_name]
                self.location_update.emit(new_x, new_y, waypoint_name)
                self.status_update.emit('이동 중...')

            if not self.docking:
                self.current_waypoint_index += 1
                if self.current_waypoint_index >= len(waypoint_order) - 1:  # docking_station은 제외
                    self.current_waypoint_index = 0

            self.msleep(2000)  # 2초마다 업데이트


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.status_label = QLabel('상태: 대기 중', self)
        self.status_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.x_data = []
        self.y_data = []
        self.labels = []
        self.robot_image = mpimg.imread('D:/Project/2024/BIW (미국 HMGMA)/KioskApplication/resources/spotimage.jpg')  # 일반 로봇 이미지
        self.robot_arm_image = mpimg.imread('D:/Project/2024/BIW (미국 HMGMA)/KioskApplication/resources/spot.jpg')  # 로봇 arm 펼친 이미지

        self.data_thread = DataThread()
        self.data_thread.location_update.connect(self.update_plot)
        self.data_thread.status_update.connect(self.update_status)
        self.data_thread.battery_update.connect(self.update_battery)
        self.data_thread.start()

    def update_plot(self, new_x, new_y, waypoint_name):
        if waypoint_name == 'inspection':
            # Inspection 상태에서는 arm 펼친 이미지를 사용
            if self.x_data and self.y_data:
                self.canvas.axes.imshow(self.robot_arm_image, extent=(
                self.x_data[-1] - 6, self.x_data[-1] + 6, self.y_data[-1] - 6, self.y_data[-1] + 6))
            self.canvas.draw()
            return

        if waypoint_name == 'waiting':
            self.x_data = []
            self.y_data = []
            self.labels = []
            self.canvas.init_map()

        self.x_data.append(new_x)
        self.y_data.append(new_y)
        self.labels.append(waypoint_name)

        self.canvas.axes.clear()
        self.canvas.init_map()
        self.canvas.axes.plot(self.x_data, self.y_data, 'r')
        for i, label in enumerate(self.labels):
            self.canvas.axes.text(self.x_data[i], self.y_data[i], label, fontsize=9, ha='right')

        # 로봇 이미지를 현재 위치에 그리기 (더 크게 보이도록 extent 조정)
        size = 6  # 이미지 크기를 조정할 값
        self.canvas.axes.imshow(self.robot_image, extent=(new_x - size, new_x + size, new_y - size, new_y + size))
        self.canvas.draw()

    def update_status(self, status):
        self.status_label.setText(f'상태: {status}')

    def update_battery(self, battery_level):
        self.setWindowTitle(f"Spot Simulation - Battery: {battery_level}%")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec_()


if __name__ == '__main__':
    main()
