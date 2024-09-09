import numpy as np
import sys
import cv2
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLineEdit, QLabel, QSpinBox
from PySide6.QtCore import QTimer
from PySide6.QtGui import QVector3D, QMatrix4x4

import pyqtgraph.opengl as gl
import open3d as o3d

import pointcloud_functions as pointcloud_functions
import outlier_processing as outlier_processing


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


class PointCloudVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.depth_path = "data/20230605_source_depth.png"
        # self.depth_path = "data/hand_depth.png"
        self.spot_pointcloud = SpotPointcloud()  # SpotPointcloud 객체 생성
        self.initUI()

    def initUI(self):
        # OpenGL 뷰어 위젯 생성
        self.widget = CustomGLViewWidget()

        # 초기 3D PointCloud 데이터 생성
        self.pointcloud_data, self.colors = self.generate_pointcloud_data(self.depth_path)

        # GLScatterPlotItem 생성
        self.scatter_plot = gl.GLScatterPlotItem(pos=self.pointcloud_data, color=self.colors, size=1)
        self.widget.addItem(self.scatter_plot)

        self.set_pointcloud_center()

        # 초기 각도 설정
        self.azimuth = -89.5
        self.elevation = 267.5
        distance = 2.4

        self.widget.opts['azimuth'] = self.azimuth
        self.widget.opts['elevation'] = self.elevation
        self.widget.opts['distance'] = distance

        # 버튼 생성
        self.update_button = QPushButton('Update PointCloud')
        self.rotate_button = QPushButton('Rotate PointCloud')

        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.rotate_button)

        # 사용자 입력 레이아웃 설정
        user_input_layout = QVBoxLayout()

        azimuth_layout = QHBoxLayout()
        azimuth_label = QLabel("azimuth")
        self.azimuth_input_label = QSpinBox()
        self.azimuth_input_label.setMinimum(-360)
        self.azimuth_input_label.setMaximum(360)
        self.azimuth_input_label.setValue(-89)

        azimuth_layout.addWidget(azimuth_label)
        azimuth_layout.addWidget(self.azimuth_input_label)

        elevation_layout = QHBoxLayout()
        elevation_label = QLabel("elevation")
        self.elevation_input_label = QSpinBox()
        self.elevation_input_label.setMinimum(-360)
        self.elevation_input_label.setMaximum(360)
        self.elevation_input_label.setValue(267)

        elevation_layout.addWidget(elevation_label)
        elevation_layout.addWidget(self.elevation_input_label)

        user_input_layout.addLayout(azimuth_layout)
        user_input_layout.addLayout(elevation_layout)

        # 메인 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addLayout(button_layout)
        # layout.addLayout(user_input_layout)
        self.setLayout(layout)

        # 회전 속도 (초당 10도)
        self.rotation_speed = 50

        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rotation)
        # self.timer.start(50)  # 50ms마다 업데이트

        # 버튼 클릭 이벤트 연결
        self.update_button.clicked.connect(self.update_pointcloud)
        self.rotate_button.clicked.connect(self.rotate_pointcloud)

    def calculate_colors(self, points):
        # 포인트의 z 값 (거리 값)에 따라 색상을 계산
        z_values = points[:, 2]
        z_min, z_max = np.min(z_values), np.max(z_values)
        colors = np.zeros((points.shape[0], 4))

        # z 값을 0과 1 사이로 정규화
        normalized_z = (z_values - z_min) / (z_max - z_min)

        # 색상 매핑 (예: 파란색에서 빨간색으로)
        colors[:, 0] = normalized_z  # R
        colors[:, 2] = 1 - normalized_z  # B
        colors[:, 3] = 1.0  # Alpha

        return colors

    def generate_pointcloud_data(self, depth_image_path):
        # 깊이 이미지 로드
        depth_image = cv2.imread(depth_image_path, cv2.IMREAD_UNCHANGED)

        # 이미지가 없으면 빈 배열 반환
        if depth_image is None:
            return np.empty((0, 3))

        # 깊이 이미지와 RGB 이미지를 준비
        self.spot_pointcloud.prepare(depth_image)

        # 포인트 클라우드 데이터와 색상 데이터를 생성
        points = self.spot_pointcloud.get_pointcloud_data()
        colors = self.calculate_colors(points)

        return points, colors

    def set_pointcloud_center(self):
        # 포인트 클라우드의 중심 계산
        if self.pointcloud_data.size > 0:
            center = self.pointcloud_data.mean(axis=0)
            self.widget.setCenter(center)

    def update_pointcloud(self):
        azimuth = self.azimuth_input_label.value()
        elevation = self.elevation_input_label.value()

        self.set_pointcloud_center()

        self.widget.setAzimuth(azimuth)
        self.widget.setElevation(elevation)
        self.widget.update()

        # 깊이 데이터 업데이트
        # self.pointcloud_data, self.colors = self.generate_pointcloud_data(self.depth_path)
        # self.scatter_plot.setData(pos=self.pointcloud_data, color=self.colors)
        # self.set_pointcloud_center()

    def update_rotation(self):
        if self.widget.lastOpts is not None:
            self.azimuth = self.widget.lastOpts['azimuth']
            self.elevation = self.widget.lastOpts['elevation']

        # self.set_pointcloud_center()
        # 뷰 회전 업데이트
        self.azimuth = (self.azimuth + self.rotation_speed * 0.1) % 360  # 초당 10도 회전
        self.elevation = (self.elevation + self.rotation_speed * 0.1) % 360  # 초당 5도 회전

        self.widget.opts['azimuth'] = self.azimuth
        self.widget.opts['elevation'] = self.elevation
        self.widget.update()

    def rotate_pointcloud(self):
        # 버튼 클릭 시 회전 시작
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(50)


fx = 217.19888305664062
fy = 217.19888305664062
# 90도 로테이션을 했기 때문에, cx, cy의 좌표값을 서로 바꾸어 줌. 기존: (111.-, 87.-)
# cx = 87.27774047851562
# cy = 111.68077850341797
cx = 87.27774047851562
cy = 111.68077850341797
depth_scale = 1000


class SpotPointcloud:
    def __init__(self):
        self.depth = None
        self.rgb = None
        self.transformation = np.eye(4)
        self.pointcloud = o3d.geometry.PointCloud()

        self.buffer = []
        self.accumulated_depth = None

    def prepare(self, depth):
        self.depth = depth

        # calibration = fx, fy, cx, cy, depth_scale
        # points = pointcloud_functions.transformation_depth_to_pcd(calibration, self.depth)
        # self.pointcloud.points = o3d.utility.Vector3dVector(points)

        camera_intrinsics = o3d.camera.PinholeCameraIntrinsic(
            width=depth.shape[1],
            height=depth.shape[0],
            fx=fx,  # 카메라의 focal length x
            fy=fy,  # 카메라의 focal length y
            cx=cx,  # 이미지의 중심 x
            cy=cy  # 이미지의 중심 y
        )

        self.pointcloud = pointcloud_functions.load_point_cloud(depth, camera_intrinsics)

    def apply_color(self, rgb):
        colors = rgb.reshape((-1, 3)) / 255.0  # Normalize RGB values to [0, 1]
        self.pointcloud.colors = o3d.utility.Vector3dVector(colors)

    def get_pointcloud_data(self):
        return np.asarray(self.pointcloud.points)

    def apply_sor_filter(self):
        nb_neighbors = 20
        std_ratio = 2.0
        self.pointcloud = outlier_processing.remove_outlier_sor_filter(self.pointcloud, nb_neighbors, std_ratio)

    def save_ply(self, path):
        o3d.io.write_point_cloud(path, self.pointcloud)
