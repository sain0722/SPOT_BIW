import numpy as np
import open3d as o3d

from utils import outlier_processing, pointcloud_functions

fx = 217.19888305664062
fy = 217.19888305664062
# 90도 로테이션을 했기 때문에, cx, cy의 좌표값을 서로 바꾸어 줌. 기존: (111.-, 87.-)
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
        self.depth_accumulator = DepthAccumulator()

    def prepare(self, depth, rgb):
        self.depth = depth
        self.rgb = rgb

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
        self.apply_color(rgb)

    def apply_color(self, rgb):
        colors = rgb.reshape((-1, 3)) / 255.0  # Normalize RGB values to [0, 1]
        self.pointcloud.colors = o3d.utility.Vector3dVector(colors)

    def get_pointcloud_data(self):
        return np.asarray(self.pointcloud.points), np.asarray(self.pointcloud.colors)

    def apply_sor_filter(self):
        nb_neighbors = 20
        std_ratio = 2.0
        self.pointcloud = outlier_processing.remove_outlier_sor_filter(self.pointcloud, nb_neighbors, std_ratio)

    def accumulate(self, depth):
        self.depth_accumulator.add_data(depth)

    def clear(self):
        self.depth_accumulator.clear()

    def accumulate_prepare(self):
        accumulated_depth = self.depth_accumulator.cumulative_data
        self.prepare(accumulated_depth)

    def save_ply(self, path):
        o3d.io.write_point_cloud(path, self.pointcloud)


class DepthAccumulator:
    def __init__(self):
        """
        DepthAccumulator 클래스의 초기화 메서드입니다.
        이 클래스는 깊이 데이터를 누적하고 필터링하는 기능을 제공합니다.

        매개변수:
        - buffer_size: 깊이 데이터의 버퍼 크기
        """

        self.buffer = []
        self.buffer_size = 10
        self.n_accumulate = 0
        self.prev_data = None
        self.curr_data = None

        # 누적 처리된 데이터 초기화
        self.cumulative_data = np.zeros((224, 171))

    def set_buffer_size(self, buffer_size):
        self.buffer_size = buffer_size

    def add_data(self, data):
        """
        깊이 데이터를 누적 버퍼에 추가하는 메서드입니다.

        매개변수:
        - data: 추가할 깊이 데이터
        """

        # 이전 데이터 저장
        self.prev_data = self.curr_data
        # 현재 데이터 저장
        self.curr_data = data.copy()

        if len(self.buffer) >= self.buffer_size:
            self.buffer.pop(0)
            idx = self.buffer_size - 1
        else:
            idx = self.n_accumulate
        self.buffer.append(data)

        if self.n_accumulate == 0:
            self.cumulative_data = self.buffer[idx]
        elif self.n_accumulate == 1:
            self.cumulative_data = self.processing(self.buffer[idx-1], self.buffer[idx])
        elif self.n_accumulate >= 2:
            self.cumulative_data = self.processing(self.cumulative_data, self.buffer[idx])

        self.n_accumulate += 1

    @staticmethod
    def processing(prev_data, curr_data):
        """
        두 깊이 데이터를 처리하여 누적된 깊이 데이터를 반환하는 메서드입니다.

        매개변수:
        - prev_data: 이전 깊이 데이터
        - curr_data: 현재 깊이 데이터

        반환값:
        - cumulative_data: 누적된 깊이 데이터
        """

        cumulative_data = np.zeros_like(curr_data)

        # 이전 데이터와 현재 데이터 비교하여 적절한 데이터 선택
        mask = (prev_data == 0) & (curr_data != 0)
        cumulative_data[mask] = curr_data[mask]
        mask = (prev_data != 0) & (curr_data == 0)
        cumulative_data[mask] = prev_data[mask]
        mask = (prev_data != 0) & (curr_data != 0)
        cumulative_data[mask] = (prev_data[mask] + curr_data[mask]) / 2

        cumulative_data = cumulative_data.astype(np.uint16)
        return cumulative_data

    def clear(self):
        """
        깊이 누적 클래스를 초기화하는 메서드입니다.
        """

        self.buffer.clear()
        self.n_accumulate = 0
        self.cumulative_data = np.zeros((224, 171))
