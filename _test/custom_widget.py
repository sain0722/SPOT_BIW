import sys

import PySide6
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout
from PySide6.QtGui import QFont, QPixmap, QPalette, QBrush, QPainter, QLinearGradient, QColor
from PySide6.QtCore import Qt, QTimer, QTime
import pyqtgraph.opengl as gl


class RoundLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        brush = QBrush(Qt.white)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)
        super().paintEvent(event)


class PointCloudVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # OpenGL 뷰어 위젯 생성
        self.widget = gl.GLViewWidget()
        self.widget.opts['distance'] = 20
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)

        # 3D PointCloud 데이터 생성
        self.pointcloud_data = self.generate_pointcloud_data()

        # GLScatterPlotItem 생성
        self.scatter_plot = gl.GLScatterPlotItem(pos=self.pointcloud_data, color=(1, 1, 1, 1), size=1)
        self.widget.addItem(self.scatter_plot)

        # 회전 속도 (초당 10도)
        self.rotation_speed = 50

        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)  # 100ms마다 업데이트

    def generate_pointcloud_data(self):
        # 랜덤으로 PointCloud 데이터 생성
        num_points = 1000
        points = np.random.rand(num_points, 3) * 10 - 5
        return points

    def update(self):
        # PointCloud 데이터 업데이트
        self.pointcloud_data += np.random.normal(0, 0.1, self.pointcloud_data.shape)
        self.scatter_plot.setData(pos=self.pointcloud_data)

        # 뷰 회전 업데이트
        current_azimuth = self.widget.opts['azimuth']
        new_azimuth = (current_azimuth + self.rotation_speed * 0.1) % 360  # 초당 10도 회전
        self.widget.opts['azimuth'] = new_azimuth
        self.widget.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Hyundai BIW Inspection Display')
        # self.setGeometry(100, 100, 1600, 900)

        self.initUI()
        self.applyGradientBackground()

    def applyGradientBackground(self):
        palette = QPalette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0, 119, 139))  # 시작 색 (청록색)
        gradient.setColorAt(1.0, QColor(0, 79, 94))  # 끝 색 (어두운 청록색)
        palette.setBrush(QPalette.Window, gradient)
        self.setPalette(palette)

    def initUI(self):
        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 헤더
        header = self.createHeader()
        main_layout.addWidget(header)

        # 중앙 디스플레이 영역
        central_widget = QWidget()
        central_layout = QHBoxLayout()

        left_side = self.createSidePanel()
        right_side = self.createSidePanel()

        central_layout.addWidget(left_side)
        central_layout.addWidget(right_side)

        central_widget.setLayout(central_layout)
        main_layout.addWidget(central_widget)

        # PointCloud 시각화 위젯 추가
        pointcloud_widget = PointCloudVisualizer()
        main_layout.addWidget(pointcloud_widget)

        # 상태 바
        status_bar = QLabel("현재 공정 상태: 정상")
        # status_bar.setStyleSheet("background-color: #0033A0; color: white; font-size: 16px; padding: 10px;")
        status_bar.setFont(QFont("현대하모니 M", 14))
        main_layout.addWidget(status_bar)

        # layout stretch 설정
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 5)
        main_layout.setStretch(2, 3)
        main_layout.setStretch(2, 1)

        # 메인 위젯 설정
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def createHeader(self):
        header_widget = QWidget()
        header_layout = QHBoxLayout()

        # 현대 로고
        hyundai_logo = QLabel('')
        hyundai_logo.setMaximumHeight(100)
        pixmap = QPixmap('../resources/hyundai_logo.png')
        scaled_pixmap = pixmap.scaled(hyundai_logo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        hyundai_logo.setPixmap(scaled_pixmap)
        hyundai_logo.setAlignment(Qt.AlignLeft)

        # 현재 시간
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignRight)
        self.clock_label.setFont(QFont("현대하모니 M", 16))

        header_layout.addWidget(hyundai_logo)
        header_layout.addWidget(self.clock_label, alignment=Qt.AlignRight)

        header_widget.setLayout(header_layout)

        # 시계 업데이트
        timer = QTimer(self)
        timer.timeout.connect(self.updateClock)
        timer.start(1000)
        self.updateClock()

        # header_widget.setStyleSheet("background-color: #0033A0; padding: 10px;")

        return header_widget

    def updateClock(self):
        current_time = QTime.currentTime().toString('hh:mm:ss')
        self.clock_label.setText(current_time)

    def createSidePanel(self):
        panel_widget = QWidget()
        panel_layout = QGridLayout()

        panel_widget.setObjectName("panel")

        # SPOT 로봇 정보
        spot_layout = QHBoxLayout()
        spot_robot_label_title, spot_robot_label_value = self.createLabel("SPOT", "BD-16071445")
        spot_layout.addWidget(spot_robot_label_title)
        spot_layout.addSpacing(20)
        spot_layout.addWidget(spot_robot_label_value)
        spot_layout.setStretch(0, 0)
        spot_layout.setStretch(1, 1)
        spot_layout.setStretch(2, 1)

        # BIW 정보
        biw_layout = QHBoxLayout()
        biw_label_title, biw_label_value = self.createLabel("BIW", "2.43")
        biw_layout.addWidget(biw_label_title)
        biw_layout.addSpacing(20)
        biw_layout.addWidget(biw_label_value)

        # MES 배터리 상태
        mes_layout = QHBoxLayout()
        mes_battery_label = self.createLabel("MES Battery Status", "85%")

        # 통신 상태
        comm_layout = QHBoxLayout()
        comm_status_label = self.createLabel("Communication Status", "Connected")

        panel_layout.addLayout(spot_layout, 0, 0)
        panel_layout.addLayout(biw_layout, 1, 0)
        panel_layout.addWidget(mes_battery_label[0], 2, 0)
        panel_layout.addWidget(mes_battery_label[1], 3, 0)
        panel_layout.addWidget(comm_status_label[0], 4, 0)
        panel_layout.addWidget(comm_status_label[1], 5, 0)

        panel_widget.setLayout(panel_layout)

        return panel_widget

    def createLabel(self, title, value):
        title_label = RoundLabel(title)
        title_label.setFont(QFont("현대하모니 M", 14))
        title_label.setObjectName("titleLabel")

        value_label = QLabel(value)
        value_label.setFont(QFont("현대하모니 M", 14))
        value_label.setObjectName("valueLabel")

        return title_label, value_label


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
