import json
import os

import cv2
import numpy as np
import open3d as o3d

import DefineGlobal
from DataManager.config import config_utils
from biw_utils import spot_functions
from biw_utils.SpotPointcloud import SpotPointcloud
from biw_utils.arm_calculate_utils import apply_spot_coordinate_matrix, apply_transformation_to_target
from biw_utils.util_functions import convert_to_target_pose
from Spot.SpotRobot import Robot


class ArmCorrectionData:
    def __init__(self):
        self.hand_color = None
        self.depth_color = None
        self.pointcloud = None
        self.hand_pose = None

    def prepare(self, pointcloud: SpotPointcloud,
                hand_pose: dict,
                hand_color: np.ndarray = None,
                depth_color: np.ndarray = None):
        """
        클래스를 초기화하는 함수
        pointcloud와 hand_pose만 등록할 수 있고, hand_color와 depth_color는 등록하지 않을 수 있다.

        :param pointcloud : (SpotPointcloud) Pointcloud 데이터
        :param hand_pose: (dict) Spot Hand의 Trajectory 정보 (position, rotation)
        :param hand_color: (np.ndarray) 컬러 이미지
        :param depth_color: (np.ndarray) depth 이미지
        """
        self.pointcloud = pointcloud
        self.hand_pose = hand_pose

        self.hand_color = hand_color
        self.depth_color = depth_color


def get_correction_data(robot: Robot) -> (np.ndarray, dict):
    camera_manager = robot.robot_camera_manager
    # 1. depth 데이터 취득
    # depth = camera_manager.get_depth()

    # Options: 누적?
    depth_setting = config_utils.read_depth_setting()
    depth = spot_functions.capture_depth(camera_manager, depth_setting)

    # Depth Inspection
    # depth_inspection_config = config_utils.read_depth_inspection()
    # if depth_inspection_config['is_depth_inspection']:
    #     roi = depth_inspection_config['region']
    #     x, y, w, h = roi
    #     depth = depth[y:y + h, x:x + w]

    # 2. 현 위치 hand 정보
    hand_pose = robot.get_hand_position_dict()

    return depth, hand_pose


def robust_icp(source: o3d.geometry.PointCloud, target: o3d.geometry.PointCloud,
               iteration=20, sigma=0.05, threshold=0.02) -> o3d.pipelines.registration.RegistrationResult:
    loss = o3d.pipelines.registration.TukeyLoss(k=sigma)
    p2l = o3d.pipelines.registration.TransformationEstimationPointToPlane(loss)

    # 초기 변환행렬은 항등행렬로 설정
    trans_init = np.eye(4)

    reg_p2l = o3d.pipelines.registration.RegistrationResult()
    source.estimate_normals()
    target.estimate_normals()
    for i in range(iteration):
        reg_p2l = o3d.pipelines.registration.registration_icp(source, target, threshold, trans_init, p2l)

        # 변환행렬 업데이트
        trans_init = reg_p2l.transformation

    return reg_p2l


def get_corrected_pose(transformation: np.array, hand_pose: dict) -> (dict, dict):
    target_pose = convert_to_target_pose(hand_pose)
    transformation_matrix = apply_spot_coordinate_matrix(transformation)
    corrected_target_pose = apply_transformation_to_target(transformation_matrix, target_pose)
    # key: x, y, z, rotation

    return corrected_target_pose['position'], corrected_target_pose['rotation']


class ArmCorrector:
    def __init__(self, robot: Robot):
        self.robot = robot
        self.master = ArmCorrectionData()
        self.target = ArmCorrectionData()

        self.icp_iteration = 0
        self.loss_sigma = 0
        self.threshold = 0

        self.icp_result = o3d.pipelines.registration.RegistrationResult()

    def prepare(self, master: ArmCorrectionData, icp_iteration, loss_sigma, threshold):
        self.master = master
        self.icp_iteration = icp_iteration
        self.loss_sigma = loss_sigma
        self.threshold = threshold

    def run(self):
        """
        Target 위치에서 시작해야 한다.
        """
        for _ in range(2):
            # 1. Target 데이터 획득
            print("get target data")
            depth, hand_pose = get_correction_data(self.robot)
            target_spot_pointcloud = SpotPointcloud()
            target_spot_pointcloud.prepare(depth)

            self.target.prepare(target_spot_pointcloud, hand_pose)

            # 2. ICP
            print("icp start")
            master_pointcloud = self.master.pointcloud.pointcloud
            target_pointcloud = self.target.pointcloud.pointcloud
            self.icp_result = robust_icp(master_pointcloud, target_pointcloud, self.icp_iteration, self.loss_sigma, self.threshold)

            # 3. 보정
            print("correction")
            transformation = self.icp_result.transformation
            corrected_position, corrected_rotation = get_corrected_pose(transformation, hand_pose)

            # 4. Reach
            print("reach")
            print(self.icp_result)
            if self.icp_result.fitness > 0.5:
                self.robot.robot_arm_manager.trajectory(corrected_position, corrected_rotation, end_time=0.5)


def arm_corrector_prepare(master: ArmCorrectionData, arm_corrector: ArmCorrector):
    config = config_utils.read_arm_correction()
    arm_correction_master_path = DefineGlobal.SPOT_MASTER_DATA_PATH
    hand_depth_path = os.path.join(arm_correction_master_path, config['hand_depth'])
    hand_depth = cv2.imread(hand_depth_path, cv2.IMREAD_ANYDEPTH)

    master_spot_pointcloud = SpotPointcloud()
    master_spot_pointcloud.prepare(hand_depth)

    master_hand_pose_path = os.path.join(arm_correction_master_path, config['arm_pose'])
    with open(master_hand_pose_path, 'r') as file:
        master_hand_pose = json.load(file)

    hand_color_path = os.path.join(arm_correction_master_path, config['hand_color'])
    hand_color = cv2.imread(hand_color_path)

    depth_color_path = os.path.join(arm_correction_master_path, config['depth_color'])
    depth_color = cv2.imread(depth_color_path)

    master.prepare(master_spot_pointcloud, master_hand_pose, hand_color=hand_color, depth_color=depth_color)
    arm_corrector.prepare(master, icp_iteration=10, loss_sigma=0.05, threshold=0.02)
