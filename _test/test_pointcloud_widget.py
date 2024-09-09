import sys
import numpy as np
import cv2
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer
import pyqtgraph.opengl as gl
import open3d as o3d

class SpotPointcloud:
    def __init__(self):
        self.depth = None
        self.rgb = None
        self.transformation = np.eye(4)
        self.pointcloud = o3d.geometry.PointCloud()

    def prepare(self, depth, rgb):
        self.depth = depth
        self.rgb = rgb

        camera_intrinsics = o3d.camera.PinholeCameraIntrinsic(
            width=depth.shape[1],
            height=depth.shape[0],
            fx=217.19888305664062,  # 카메라의 focal length x
            fy=217.19888305664062,  # 카메라의 focal length y
            cx=87.27774047851562,   # 이미지의 중심 x
            cy=111.68077850341797   # 이미지의 중심 y
        )

        self.pointcloud = self.load_point_cloud(depth, camera_intrinsics)
        self.apply_color(rgb)

    def load_point_cloud(self, depth, camera_intrinsics):
        depth_o3d = o3d.geometry.Image(depth)
        pcd = o3d.geometry.PointCloud.create_from_depth_image(
            depth_o3d, camera_intrinsics, depth_scale=1000, project_valid_depth_only=False)
        return pcd

    def apply_color(self, rgb):
        rgb_flat = rgb.reshape((-1, 3)) / 255.0  # Normalize RGB values to [0, 1]
        valid_indices = np.asarray(self.pointcloud.points).shape[0]
        self.pointcloud.colors = o3d.utility.Vector3dVector(rgb_flat[:valid_indices])

    def get_pointcloud_data(self):
        return np.asarray(self.pointcloud.points), np.asarray(self.pointcloud.colors)

class PointCloudVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.depth_path = "D:/Project/2024/BIW(US)/KioskApplication/data/20230605_source_depth.png"
        self.rgb_path = "D:/Project/2024/BIW(US)/KioskApplication/data/20230605_source_hand_color_in_depth_frame.png"
        self.spot_pointcloud = SpotPointcloud()  # SpotPointcloud 객체 생성
        self.initUI()

    def initUI(self):
        # OpenGL 뷰어 위젯 생성
        self.widget = gl.GLViewWidget()
        self.widget.opts['distance'] = 20

        # 버튼 생성
        self.update_button = QPushButton('Update PointCloud')
        self.rotate_button = QPushButton('Rotate PointCloud')

        # 버튼 레이아웃 설정
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.rotate_button)

        # 메인 레이아웃 설정
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        # 초기 3D PointCloud 데이터 생성
        self.pointcloud_data, self.colors = self.generate_pointcloud_data(self.depth_path, self.rgb_path)

        # GLScatterPlotItem 생성
        self.scatter_plot = gl.GLScatterPlotItem(pos=self.pointcloud_data, color=self.colors, size=2)
        self.widget.addItem(self.scatter_plot)

        # 회전 속도 (초당 10도)
        self.rotation_speed = 50

        # 타이머 설정
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_rotation)
        self.timer.start(50)  # 50ms마다 업데이트

        # 초기 회전 설정
        self.azimuth = 0
        self.elevation = 0

        # 버튼 클릭 이벤트 연결
        self.update_button.clicked.connect(self.update_pointcloud)
        self.rotate_button.clicked.connect(self.rotate_pointcloud)

    def generate_pointcloud_data(self, depth_image_path, rgb_image_path):
        # 깊이 이미지 로드
        depth_image = cv2.imread(depth_image_path, cv2.IMREAD_UNCHANGED)
        # RGB 이미지 로드
        rgb_image = cv2.imread(rgb_image_path, cv2.IMREAD_COLOR)
        rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)  # BGR에서 RGB로 변환

        # 이미지가 없으면 빈 배열 반환
        if depth_image is None or rgb_image is None:
            return np.empty((0, 3)), np.empty((0, 4))

        # RGB 이미지를 깊이 이미지 크기에 맞게 리사이즈
        if depth_image.shape[:2] != rgb_image.shape[:2]:
            rgb_image = cv2.resize(rgb_image, (depth_image.shape[1], depth_image.shape[0]), interpolation=cv2.INTER_LINEAR)

        # 깊이 이미지와 RGB 이미지를 준비
        self.spot_pointcloud.prepare(depth_image, rgb_image)

        # 포인트 클라우드 데이터와 색상 데이터를 생성
        points, colors = self.spot_pointcloud.get_pointcloud_data()

        return points, colors

    def update_pointcloud(self):
        # 깊이 데이터 업데이트
        self.pointcloud_data, self.colors = self.generate_pointcloud_data(self.depth_path, self.rgb_path)
        self.scatter_plot.setData(pos=self.pointcloud_data, color=self.colors)

    def update_rotation(self):
        # 뷰 회전 업데이트
        self.azimuth = (self.azimuth + self.rotation_speed * 0.1) % 360  # 초당 10도 회전
        self.elevation = (self.elevation + self.rotation_speed * 0.05) % 360  # 초당 5도 회전

        self.widget.opts['azimuth'] = self.azimuth
        self.widget.opts['elevation'] = self.elevation
        self.widget.update()

    def rotate_pointcloud(self):
        # 버튼 클릭 시 회전 시작
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(50)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    visualizer = PointCloudVisualizer()
    visualizer.show()
    sys.exit(app.exec_())
