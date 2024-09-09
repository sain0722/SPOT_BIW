import math

import numpy as np
from bosdyn.client import math_helpers


def quaternion_multiply(q1, q2):
    """
    주어진 두 개의 쿼터니언을 곱합니다.

    이 함수는 쿼터니언 곱셈을 수행하여 두 회전을 합성합니다. 쿼터니언 곱셈은
    비교적 간단하지만, 이해하려면 쿼터니언과 3차원 회전에 대한 이해가 필요합니다.

    Parameters:
    q1 (tuple): 첫 번째 쿼터니언입니다. w, x, y, z의 네 요소로 구성된 튜플이어야 합니다.
    q2 (tuple): 두 번째 쿼터니언입니다. w, x, y, z의 네 요소로 구성된 튜플이어야 합니다.

    Returns:
    rotation (math_helpers.Quat): 두 쿼터니언의 곱의 결과로 생성된 새로운 쿼터니언입니다.
    """

    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 + y1 * w2 + z1 * x2 - x1 * z2
    z = w1 * z2 + z1 * w2 + x1 * y2 - y1 * x2

    rotation = math_helpers.Quat(w, x, y, z)
    return rotation


def pose_to_homogeneous_matrix(pose):
    """
    주어진 3D 포즈를 동차 행렬로 변환합니다.

    Parameters:
    pose (tuple): 3D 포즈를 나타내는 튜플입니다. 튜플의 첫 3개 값은 x, y, z의 위치이며,
    나머지 4개 값은 w, x, y, z의 쿼터니언으로 표현된 방향입니다.

    Returns:
    homogeneous_matrix (np.ndarray): 동차 행렬을 나타내는 4x4 numpy 배열입니다.
    """

    # 회전 정보를 행렬로 변환
    rotation_matrix = np.array([
        [1 - 2 * (pose['rotation']['y'] ** 2) - 2 * (pose['rotation']['z'] ** 2),
         2 * (pose['rotation']['x'] * pose['rotation']['y'] - pose['rotation']['z'] * pose['rotation']['w']),
         2 * (pose['rotation']['x'] * pose['rotation']['z'] + pose['rotation']['y'] * pose['rotation']['w'])],
        [2 * (pose['rotation']['x'] * pose['rotation']['y'] + pose['rotation']['z'] * pose['rotation']['w']),
         1 - 2 * (pose['rotation']['x'] ** 2) - 2 * (pose['rotation']['z'] ** 2),
         2 * (pose['rotation']['y'] * pose['rotation']['z'] - pose['rotation']['x'] * pose['rotation']['w'])],
        [2 * (pose['rotation']['x'] * pose['rotation']['z'] - pose['rotation']['y'] * pose['rotation']['w']),
         2 * (pose['rotation']['y'] * pose['rotation']['z'] + pose['rotation']['x'] * pose['rotation']['w']),
         1 - 2 * (pose['rotation']['x'] ** 2) - 2 * (pose['rotation']['y'] ** 2)]
    ])

    # 동차 좌표계 행렬 생성
    homogeneous_matrix = np.eye(4)
    homogeneous_matrix[:3, :3] = rotation_matrix
    homogeneous_matrix[:3, 3] = [pose['x'], pose['y'], pose['z']]

    return homogeneous_matrix


def homogeneous_matrix_to_pose(matrix):
    """
    주어진 동차 행렬을 3D 포즈로 변환합니다.
    Parameters:
    matrix (np.ndarray): 동차 행렬을 나타내는 4x4 numpy 배열입니다.
    Returns:
    dict: 위치 (x, y, z) 및 회전 (w, x, y, z의 쿼터니언)을 포함하는 딕셔너리입니다.
    """
    # 위치 정보 추출
    tx, ty, tz = matrix[:3, 3]

    # 회전 정보(사원수) 추출
    trace = np.trace(matrix[:3, :3])
    if trace > 0:
        s = 0.5 / np.sqrt(trace + 1.0)
        w = 0.25 / s
        x = (matrix[2, 1] - matrix[1, 2]) * s
        y = (matrix[0, 2] - matrix[2, 0]) * s
        z = (matrix[1, 0] - matrix[0, 1]) * s
    else:
        if matrix[0, 0] > matrix[1, 1] and matrix[0, 0] > matrix[2, 2]:
            s = 2.0 * np.sqrt(1.0 + matrix[0, 0] - matrix[1, 1] - matrix[2, 2])
            w = (matrix[2, 1] - matrix[1, 2]) / s
            x = 0.25 * s
            y = (matrix[0, 1] + matrix[1, 0]) / s
            z = (matrix[0, 2] + matrix[2, 0]) / s
        elif matrix[1, 1] > matrix[2, 2]:
            s = 2.0 * np.sqrt(1.0 + matrix[1, 1] - matrix[0, 0] - matrix[2, 2])
            w = (matrix[0, 2] - matrix[2, 0]) / s
            x = (matrix[0, 1] + matrix[1, 0]) / s
            y = 0.25 * s
            z = (matrix[1, 2] + matrix[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + matrix[2, 2] - matrix[0, 0] - matrix[1, 1])
            w = (matrix[1, 0] - matrix[0, 1]) / s
            x = (matrix[0, 2] + matrix[2, 0]) / s
            y = (matrix[1, 2] + matrix[2, 1]) / s
            z = 0.25 * s
    position = {'x': tx, 'y': ty, 'z': tz}
    rotation = {'w': w, 'x': x, 'y': y, 'z': z}

    return {'position': position, 'rotation': rotation}


def apply_transformation_to_target(transformation_matrix, target_pose) -> dict:
    """
    주어진 변환 행렬을 사용하여 Target Pose에 변환을 적용합니다.

    Parameters:
    transformation_matrix (np.ndarray): 변환을 적용할 4x4 변환 행렬입니다.
    target_pose (dict): 변환을 적용할 Target Pose입니다. 위치 (x, y, z) 및 회전 (w, x, y, z의 쿼터니언)을 포함하는 딕셔너리입니다.

    Returns:
    corrected_target_pose (dict): 변환된 목표 포즈. 위치 (x, y, z) 및 회전 (w, x, y, z의 쿼터니언)을 포함하는 딕셔너리입니다.
    """
    # 입력된 SE3Pose를 동차 좌표계 행렬로 변환
    target_homogeneous_matrix = pose_to_homogeneous_matrix(target_pose)

    # 변환 행렬을 소스 위치에서의 포인트 클라우드를 타겟 위치에서의 포인트 클라우드로 변환하는 행렬로 사용
    # transformed_target_homogeneous_matrix = np.dot(target_homogeneous_matrix, np.linalg.inv(transformation_matrix))
    transformed_target_homogeneous_matrix = np.dot(target_homogeneous_matrix, transformation_matrix)

    # 변환된 동차 좌표계 행렬을 다시 SE3Pose로 변환
    # print(transformed_target_homogeneous_matrix)
    corrected_target_pose = homogeneous_matrix_to_pose(transformed_target_homogeneous_matrix)

    return corrected_target_pose


def apply_spot_coordinate_matrix(transformation_matrix):
    """
    주어진 변환 행렬을 Spot 좌표계에 적용합니다.

    Parameters:
    transformation_matrix (np.ndarray): 적용할 4x4 변환 행렬입니다.

    Returns:
    transformation_matrix (np.ndarray): Spot 좌표계에 맞게 재배열된 변환 행렬입니다.
    """
    # 변환 행렬의 역행렬
    transformation_matrix = np.linalg.inv(transformation_matrix)

    # 변환 행렬의 좌표계의 배열을 SPOT의 좌표계의 배열에 맞게 재배열합니다.
    # Spot 좌표계의 y축 (실제 좌표계의 x축)은 대칭이동합니다.
    transformation_matrix[:3, 3] = transformation_matrix[:3, 3][[2, 0, 1]]
    transformation_matrix[0, 3] = -transformation_matrix[0, 3]

    # Transformation matrix의 회전 부분만 추출합니다.
    rotation_matrix = transformation_matrix[:3, :3]

    # SPOT의 x축 (실제 z축)은 대칭이동합니다.
    rotation_matrix[0, 1] = -rotation_matrix[0, 1]
    rotation_matrix[1, 0] = -rotation_matrix[1, 0]

    # 새로운 순서에 맞게 회전 행렬의 행을 재배열합니다.
    rotation_matrix = rotation_matrix[[2, 0, 1]]

    # 새로운 순서에 맞게 회전 행렬의 열을 재배열합니다.
    rotation_matrix = rotation_matrix[:, [2, 0, 1]]

    transformation_matrix[:3, :3] = rotation_matrix

    return transformation_matrix


def calculate_new_rotation(axis, angle, body_tform_hand_rotation):
    """
    주어진 축과 각도에 따른 새로운 회전을 계산합니다.

    Parameters:
    axis (str): 회전 축입니다. x, y, z 중 하나입니다.
    angle (float): 회전할 각도입니다. 단위는 도입니다.
    body_tform_hand_rotation (math_helpers.Quat): 초기 회전 사원수입니다.

    Returns:
    math_helpers.Quat: 새로 계산된 회전 사원수입니다.
    """
    # 각도 변화 (라디안)
    angle = angle * (math.pi / 180)

    # 회전 축
    if axis == "x":
        axis = np.array([1, 0, 0])
    elif axis == "y":
        axis = np.array([0, 1, 0])
    elif axis == "z":
        axis = np.array([0, 0, 1])

    # 새로운 쿼터니언 생성
    new_quaternion = np.array([
        math.cos(angle / 2),
        axis[0] * math.sin(angle / 2),
        axis[1] * math.sin(angle / 2),
        axis[2] * math.sin(angle / 2)
    ])

    # 원래의 쿼터니언
    original_quaternion = [body_tform_hand_rotation.w,
                           body_tform_hand_rotation.x,
                           body_tform_hand_rotation.y,
                           body_tform_hand_rotation.z]

    # 쿼터니언 곱셈을 통해 새로운 회전 쿼터니언 계산
    new_rotation = quaternion_multiply(original_quaternion, new_quaternion)

    return new_rotation


def calculate_new_rotation_multi_axes(axes_angles, body_tform_hand_rotation):
    """
    주어진 여러 축과 각도에 따른 새로운 회전을 계산합니다.

    Parameters:
    axes_angles (dict): 각 축에 대한 회전 각도입니다. 축 이름을 키로, 회전 각도를 값으로 가집니다.
    body_tform_hand_rotation (math_helpers.Quat): 초기 회전 사원수입니다.

    Returns:
    math_helpers.Quat: 새로 계산된 회전 사원수입니다.
    """
    # 원래의 쿼터니언
    original_quaternion = [body_tform_hand_rotation.w,
                           body_tform_hand_rotation.x,
                           body_tform_hand_rotation.y,
                           body_tform_hand_rotation.z]

    # 각 축에 대해 회전을 계산
    for axis, angle in axes_angles.items():
        if type(original_quaternion) == math_helpers.Quat:
            original_quaternion = [original_quaternion.w,
                                   original_quaternion.x,
                                   original_quaternion.y,
                                   original_quaternion.z]

        # 각도 변화 (라디안)
        angle = angle * (math.pi / 180)

        # 회전 축
        if axis == "x":
            axis_vector = np.array([1, 0, 0])
        elif axis == "y":
            axis_vector = np.array([0, 1, 0])
        elif axis == "z":
            axis_vector = np.array([0, 0, 1])

        # 새로운 쿼터니언 생성
        new_quaternion = np.array([
            math.cos(angle / 2),
            axis_vector[0] * math.sin(angle / 2),
            axis_vector[1] * math.sin(angle / 2),
            axis_vector[2] * math.sin(angle / 2)
        ])

        # 쿼터니언 곱셈을 통해 새로운 회전 쿼터니언 계산
        original_quaternion = quaternion_multiply(original_quaternion, new_quaternion)

    return original_quaternion
