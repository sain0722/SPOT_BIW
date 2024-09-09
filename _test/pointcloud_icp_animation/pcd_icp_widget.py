import sys
import open3d as o3d
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer, QThread, Signal
from PySide6.QtGui import QVector3D
import pyqtgraph.opengl as gl
import copy


class CustomGLViewWidget(gl.GLViewWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.lastPos = None
        self.lastOpts = None
        self.center = np.array([0, 0, 0])

    def mousePressEvent(self, event):
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event):
        if self.lastPos is not None:
            delta = event.pos() - self.lastPos
            self.opts['azimuth'] += delta.x() * 0.5  # adjust sensitivity
            self.opts['elevation'] -= delta.y() * 0.5  # adjust sensitivity
            self.lastPos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.lastPos = None
        self.lastOpts = self.opts

    def setCenter(self, center):
        self.center = QVector3D(center[0], center[1], center[2])
        self.opts['center'] = self.center
        # self.opts['rotateCenter'] = self.center  # Set rotation center

    def setAzimuth(self, azimuth):
        self.opts['azimuth'] = azimuth
        self.lastOpts = self.opts

    def setElevation(self, elevation):
        self.opts['elevation'] = elevation
        self.lastOpts = self.opts


class ICPPointCloudVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.source = None
        self.target = None
        self.initUI()

    def init_pointcloud(self, source, target):
        self.source = np.asarray(source.points)
        self.target = np.asarray(target.points)

        # GLScatterPlotItem 생성
        self.colors_source = np.array([[1.0, 0.0, 0.0, 0.5] for _ in range(self.source.shape[0])])
        self.colors_target = np.array([[0.0, 1.0, 0.0, 0.5] for _ in range(self.target.shape[0])])

        self.scatter_plot_source = gl.GLScatterPlotItem(pos=self.source, color=self.colors_source, size=2)
        self.scatter_plot_target = gl.GLScatterPlotItem(pos=self.target, color=self.colors_target, size=2)

        self.widget.addItem(self.scatter_plot_source)
        self.widget.addItem(self.scatter_plot_target)

    def initUI(self):
        # OpenGL 뷰어 위젯 생성
        self.widget = CustomGLViewWidget()

        self.set_pointcloud_center()

        # 초기 각도 설정
        self.azimuth = -89.5
        self.elevation = 267.5
        distance = 0.5

        self.widget.opts['azimuth'] = self.azimuth
        self.widget.opts['elevation'] = self.elevation
        self.widget.opts['distance'] = distance

        # 버튼 생성
        self.update_button = QPushButton('Update PointCloud')
        self.rotate_button = QPushButton('Rotate PointCloud')
        self.icp_button = QPushButton('ICP Algorithm')

        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.rotate_button)
        button_layout.addWidget(self.icp_button)

        # 메인 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 회전 속도 (초당 10도)
        self.rotation_speed = 10

        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rotation)
        self.timer.start(50)  # 50ms마다 업데이트

        # 버튼 클릭 이벤트 연결
        self.update_button.clicked.connect(self.update_pointcloud)
        self.rotate_button.clicked.connect(self.rotate_pointcloud)
        self.icp_button.clicked.connect(self.run_icp_algorithm)

    def set_pointcloud_center(self):
        # 포인트 클라우드의 중심 계산
        if self.source.points.size > 0:
            center = self.source.points.mean(axis=0)
            self.widget.setCenter(center)

    def update_pointcloud(self):
        # 포인트 클라우드 업데이트 (임시로 동일한 데이터를 사용)
        source_pcd = o3d.io.read_point_cloud("pointcloud_source.ply")
        target_pcd = o3d.io.read_point_cloud("pointcloud_target_10.ply")
        self.source = np.asarray(source_pcd.points)
        self.target = np.asarray(target_pcd.points)

        self.scatter_plot_source.setData(pos=self.source, color=self.colors_source)
        self.scatter_plot_target.setData(pos=self.target, color=self.colors_target)

        self.set_pointcloud_center()

    def update_rotation(self):
        if self.widget.lastOpts is not None:
            self.azimuth = self.widget.lastOpts['azimuth']
            self.elevation = self.widget.lastOpts['elevation']

        # 뷰 회전 업데이트
        self.azimuth = (self.azimuth + self.rotation_speed * 0.1) % 360  # 초당 10도 회전
        self.elevation = (self.elevation + self.rotation_speed * 0.1) % 360  # 초당 5도 회전

        self.widget.opts['azimuth'] = self.azimuth
        self.widget.opts['elevation'] = self.elevation
        self.widget.update()

    def rotate_pointcloud(self):
        # 버튼 클릭 시 회전 시작/정지
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(50)

    def update_source_points(self, new_source_points):
        self.source = new_source_points
        self.scatter_plot_source.setData(pos=self.source, color=self.colors_source)

    def run_icp_algorithm(self):
        # ICP 알고리즘을 실행하는 스레드 시작
        self.icp_thread = ICPThread(self.source_pcd, self.target_pcd, threshold=0.02, max_iterations=50)
        self.icp_thread.transformation_signal.connect(self.update_source_points)
        self.icp_thread.start()

    def set_point_clouds(self, source_pcd, target_pcd):
        self.source_pcd = source_pcd
        self.target_pcd = target_pcd


class ICPThread(QThread):
    transformation_signal = Signal(np.ndarray)

    def __init__(self, source, target, threshold, max_iterations):
        super().__init__()
        self.source = source
        self.target = target
        self.transformation = np.identity(4)
        self.threshold = threshold
        self.iteration = 0
        self.max_iterations = max_iterations

    def run(self):
        source_temp = copy.deepcopy(self.source)
        while self.iteration < self.max_iterations:
            reg_p2p = o3d.pipelines.registration.registration_icp(
                source_temp, self.target, self.threshold, self.transformation,
                o3d.pipelines.registration.TransformationEstimationPointToPoint(),
                o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=1)
            )
            self.transformation = reg_p2p.transformation
            source_temp.transform(self.transformation)
            self.transformation_signal.emit(np.asarray(source_temp.points))
            self.iteration += 1


class ICPWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ICP Registration Animation")
        # self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.pointcloud_visualizer = PointCloudVisualizer()
        self.layout.addWidget(self.pointcloud_visualizer)

        self.init_icp()

    def init_icp(self):
        source_pcd = o3d.io.read_point_cloud("pointcloud_source.ply")
        target_pcd = o3d.io.read_point_cloud("pointcloud_target_10.ply")
        self.pointcloud_visualizer.init_pointcloud(source_pcd, target_pcd)
        self.pointcloud_visualizer.set_point_clouds(source_pcd, target_pcd)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = ICPWidget()
    widget.show()
    sys.exit(app.exec_())
