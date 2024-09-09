import cv2
import numpy as np
import open3d as o3d


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
