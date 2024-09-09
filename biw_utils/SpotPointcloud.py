import numpy as np
import open3d as o3d
from biw_utils.outlier_processing import remove_outlier_sor_filter

fx = 217.19888305664062
fy = 217.19888305664062
# 90도 로테이션을 했기 때문에, cx, cy의 좌표값을 서로 바꾸어 줌. 기존: (111.-, 87.-)
cx = 87.27774047851562
cy = 111.68077850341797
depth_scale = 1000


class SpotPointcloud:
    def __init__(self):
        self.depth = None
        self.transformation = np.eye(4)
        self.pointcloud = o3d.geometry.PointCloud()

        self.buffer = []
        self.accumulated_depth = None
        self.depth_accumulator = DepthAccumulator()

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

        self.pointcloud = load_point_cloud(depth, camera_intrinsics)

    def apply_sor_filter(self):
        nb_neighbors = 20
        std_ratio = 2.0
        self.pointcloud = remove_outlier_sor_filter(self.pointcloud, nb_neighbors, std_ratio)

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


def transformation_depth_to_pcd(calibration: tuple, depth: np.ndarray):
    fx, fy, cx, cy, depth_scale = calibration
    # depth 이미지의 크기를 구합니다.
    height, width = depth.shape[:2]

    # 카메라 파라미터를 이용하여 포인트 클라우드를 생성합니다.
    # 포인트 클라우드는 (h*w, 3) 크기의 NumPy 배열입니다.
    pointcloud = np.zeros((height * width, 3), dtype=np.float32)

    index = 0
    for v in range(height):
        for u in range(width):
            # 이미지 상의 (u, v) 좌표의 깊이 값을 가져옵니다.
            depth_value = depth[v, u]

            # 깊이 값이 0인 경우는 포인트 클라우드에 추가하지 않습니다.
            if depth_value == 0:
                continue

            # 이미지 상의 (u, v) 좌표의 3차원 좌표 값을 계산합니다.
            Z = depth_value / depth_scale
            X = (u - cx) * Z / fx
            Y = (v - cy) * Z / fy
            pointcloud[index, :] = [X, Y, Z]
            index += 1

    # 포인트 클라우드가 저장된 NumPy 배열과 포인트 개수를 반환합니다.
    return pointcloud[:index, :]


def transformation_pcd_to_depth(calibration: tuple, pointcloud, height=224, width=171):
    fx, fy, cx, cy, depth_scale = calibration

    depth_image = np.zeros((height, width), dtype=np.float32)

    # Z 값이 0인 포인트 제거
    valid_points = pointcloud[pointcloud[:, 2] != 0]

    # 3D 좌표를 이미지 좌표 (u, v)로 변환
    u = np.round((valid_points[:, 0] * fx / valid_points[:, 2]) + cx).astype(int)
    v = np.round((valid_points[:, 1] * fy / valid_points[:, 2]) + cy).astype(int)

    # 이미지 범위 내의 좌표만 선택
    valid_indices = np.where((0 <= u) & (u < width) & (0 <= v) & (v < height))

    # 이미지에 깊이 값을 저장
    depth_values = valid_points[valid_indices][:, 2] * depth_scale
    depth_image[v[valid_indices], u[valid_indices]] = depth_values

    return depth_image


def load_point_cloud(depth: np.ndarray, camera_intrinsics) -> o3d.geometry.PointCloud:
    """ 깊이 이미지로부터 포인트 클라우드를 로드하는 함수 """
    # Open3D 이미지로 변환
    depth_o3d = o3d.geometry.Image(depth)

    pcd = o3d.geometry.PointCloud.create_from_depth_image(
        depth_o3d, camera_intrinsics, depth_scale=1000)
    return pcd


def show(pointcloud: o3d.geometry.PointCloud):
    width  = 1440
    height = 968
    left   = 50
    top    = 50

    # 224 x 171 크기의 window 파라미터
    front  = [0.16, -0.85, -0.49]
    lookat = [-0.05, 0.26, 0.67]
    up     = [-0.009, -0.5, 0.86]
    zoom   = 1.2

    # Crop 시 window 파라미터
    front  = [0.11, 0.44, -0.89]
    lookat = [-0.16, -0.21, 0.63]
    up     = [0.34, -0.86, -0.38]
    zoom   = 1.74

    o3d.visualization.draw_geometries([pointcloud],
                                      width=width, height=height, left=left, top=top,
                                      front=front, lookat=lookat, up=up, zoom=zoom)

