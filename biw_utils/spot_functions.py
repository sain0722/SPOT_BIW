import json
import os

import cv2
from PySide6.QtGui import QImage, QPixmap
from bosdyn.client import robot_command
from bosdyn.api import image_pb2

import numpy as np
from scipy import ndimage

from biw_utils.SpotPointcloud import SpotPointcloud
from biw_utils import outlier_processing

from Spot.SpotCamera import SpotCamera
from Spot.SpotRobot import Robot


def save_arm_joint_state(robot: Robot, file_path: str):
    joint_params = robot.get_current_joint_state()

    # 입력된 파일 경로의 확장자 검사
    if not file_path.endswith(".json"):
        file_path += '.json'

    with open(file_path, 'w') as file:
        json.dump(joint_params, file, indent=4)


def save_arm_trajectory_state(hand_position: dict, file_path: str):
    # 입력된 파일 경로의 확장자 검사
    if not file_path.endswith(".json"):
        file_path += '.json'

    with open(file_path, 'w') as file:
        json.dump(hand_position, file, indent=4)


def capture_bgr(camera_manager: SpotCamera) -> np.ndarray:
    return camera_manager.take_image()
    # import cv2
    # return cv2.imread("UI/widget/test_capture_position2.jpg", cv2.IMREAD_COLOR)


def capture_depth(camera_manager: SpotCamera, depth_setting: dict):
    # 누적
    if depth_setting['is_accumulate']:
        # acm_count 만큼 누적 진행
        spot_pointcloud = SpotPointcloud()

        if depth_setting['is_accumulate']:
            iteration = depth_setting['acm_count']
            spot_pointcloud.depth_accumulator.set_buffer_size(iteration)
            for i in range(iteration):
                hand_depth = camera_manager.get_depth()
                spot_pointcloud.accumulate(hand_depth)
            spot_pointcloud.accumulate_prepare()
        else:
            hand_depth = camera_manager.get_depth()
            spot_pointcloud.prepare(hand_depth)

        depth = spot_pointcloud.depth
    else:
        # 1회 촬영
        depth = camera_manager.get_depth()

    # Outlier
    if depth_setting['is_extract_range']:
        range_min = depth_setting['range_min']
        range_max = depth_setting['range_max']
        depth = outlier_processing.extract_data_in_percentile_range(depth, range_min, range_max)
    if depth_setting['is_gaussian']:
        threshold = depth_setting['threshold']
        depth = outlier_processing.remove_outlier_gaussian(depth, threshold=threshold)

    if depth_setting['is_sor']:
        # Pointcloud 객체에 사용 가능.
        # Pointcloud 처리 부에서 적용
        pass

    return depth


def is_position_within_tolerance(saved_position, current_position, tolerance_percent=10):
    # Calculate the absolute difference for each coordinate (x, y, z)
    diff_x = abs(saved_position["x"] - current_position["x"])
    diff_y = abs(saved_position["y"] - current_position["y"])
    diff_z = abs(saved_position["z"] - current_position["z"])

    # Check if any coordinate has a difference of tolerance_percent or more
    if (diff_x / saved_position["x"] * 100 >= tolerance_percent) or \
       (diff_y / saved_position["y"] * 100 >= tolerance_percent) or \
       (diff_z / saved_position["z"] * 100 >= tolerance_percent):
        return False
    else:
        return True


def dock_if_battery_low(robot: Robot, threshold) -> bool:
    """
    배터리 수준이 지정된 임계값 이하인 경우 dock 메서드를 실행합니다.

    Args:
        robot (Robot): SpotRobot 객체
        threshold (int): 배터리 수준의 임계값 (%)
    """

    dock_id = robot.dock_id

    if robot.is_battery_low(threshold):
        from Thread.DockingThread import DockingThread
        dock_thread = DockingThread(robot, dock_id, is_docking=True)
        dock_thread.start()
        return True

    return False


# Arm Correction Data Save Function
def arm_correction_data_save(robot_camera_manager, depth_setting):
    camera_manager = robot_camera_manager
    hand_color = capture_bgr(camera_manager)
    hand_depth = capture_depth(camera_manager=camera_manager, depth_setting=depth_setting)
    saved_path = self.main_window.widget_setting_page.widget_spot_setting.line_edit_data_save_dir_manual.text()
    os.makedirs(saved_path, exist_ok=True)

    hand_depth_color = depth_to_color(hand_depth)

    cv2.imwrite(os.path.join(saved_path, "hand_color.jpg"), hand_color)
    cv2.imwrite(os.path.join(saved_path, "hand_depth.png"), hand_depth)
    cv2.imwrite(os.path.join(saved_path, "hand_depth_color.png"), hand_depth_color)

    # Arm Current Position Save.
    # Trajectory values
    save_arm_trajectory_state(self.main_window.robot, os.path.join(saved_path, "arm_pose.json"))

    log_message = f"저장이 완료되었습니다. 저장위치: {saved_path}"
    self.main_window.write_log(log_message)


def depth_to_color(depth_data):
    """
    깊이 이미지를 컬러 이미지로 변환하는 메소드입니다.

    Args:
        depth_data (numpy.ndarray): 깊이 이미지 데이터

    Returns:
        numpy.ndarray: 컬러 이미지 데이터
    """
    min_val = np.min(depth_data)
    max_val = np.max(depth_data)
    depth_range = max_val - min_val

    if depth_range == 0:
        # depth8 = depth_data.astype('uint8')
        normalized_depth = depth_data.astype('uint8')
    else:
        # depth8 = (255.0 / depth_range * (depth_data - min_val)).astype('uint8')
        # 최소값을 0으로, 최대값을 255로 정규화
        normalized_depth = (255.0 * (depth_data - min_val) / (max_val - min_val)).astype('uint8')

    # depth8_rgb = cv2.cvtColor(depth8, cv2.COLOR_GRAY2RGB)
    # depth_color = cv2.applyColorMap(depth8_rgb, cv2.COLORMAP_JET)
    depth8_rgb = cv2.cvtColor(normalized_depth, cv2.COLOR_GRAY2RGB)
    depth_color = cv2.applyColorMap(depth8_rgb, cv2.COLORMAP_JET)
    return depth_color


### Depth 카메라 기반 거리 측정 및 충돌 방지 기능 ###

ROTATION_ANGLE = {
    'hand_depth': 0,
    'hand_color_image': 0,
    'frontleft_depth': 0,
    'frontright_depth': 0,

    'back_fisheye_image': 0,
    'frontleft_fisheye_image': -78,
    'frontright_fisheye_image': -102,
    'left_fisheye_image': 0,
    'right_fisheye_image': 180
}

def get_depth_data(image_client, source="hand_depth"):
    """Get depth data from the hand depth sensor."""
    # image_responses = image_client.get_image_from_sources(["hand_depth_in_hand_color_frame"])
    image_responses = image_client.get_image_from_sources([source])

    image = None
    for image_response in image_responses:
        if image_response.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_DEPTH_U16:
            image = image_response
            break

    if image is None:
        raise ValueError("No hand depth image received.")

    # Convert depth image to numpy array
    # depth_array = np.frombuffer(depth_image.data, dtype=np.uint16)
    # depth_array = depth_array.reshape(depth_image.rows, depth_image.cols)
    # depth_array = cv2.rotate(depth_array, cv2.ROTATE_90_CLOCKWISE)
    #
    # return depth_array

    num_bytes = 1  # Assume a default of 1 byte encodings.
    if image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_DEPTH_U16:
        dtype = np.uint16
        extension = '.png'
    else:
        if image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_RGB_U8:
            num_bytes = 3
        elif image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_RGBA_U8:
            num_bytes = 4
        elif image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_GREYSCALE_U8:
            num_bytes = 1
        elif image.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_GREYSCALE_U16:
            num_bytes = 2
        dtype = np.uint8
        extension = '.jpg'

    img = np.frombuffer(image.shot.image.data, dtype=dtype)
    if image.shot.image.format == image_pb2.Image.FORMAT_RAW:
        try:
            # Attempt to reshape array into an RGB rows X cols shape.
            img = img.reshape((image.shot.image.rows, image.shot.image.cols, num_bytes))
        except ValueError:
            # Unable to reshape the image data, trying a regular decode.
            img = cv2.imdecode(img, -1)
    else:
        img = cv2.imdecode(img, -1)

    auto_rotate = True
    if auto_rotate:
        img = ndimage.rotate(img, ROTATION_ANGLE[image.source.name])

    return img



def measure_distance(depth_array):
    """Measure the distance from the sensor to the nearest object using the ROI method."""
    rows, cols, _ = depth_array.shape
    # Define the ROI as the central region
    roi_rows_start = rows // 4
    roi_rows_end = rows * 3 // 4
    roi_cols_start = cols // 4
    roi_cols_end = cols * 3 // 4

    # Extract the ROI
    roi = depth_array[roi_rows_start:roi_rows_end, roi_cols_start:roi_cols_end]

    # Calculate the average distance in the ROI
    avg_distance = np.mean(roi)

    return avg_distance


def is_within_range(distance, min_distance=270, max_distance=330):
    """Check if the distance is within the specified range."""
    return min_distance <= distance <= max_distance


def move_back(spot_robot: Robot, distance=0.5):
    # B/D robot
    robot = spot_robot.robot

    """Move the robot back by the specified distance (in meters)."""
    # mobility_client = robot.ensure_client('bosdyn.client.lease')
    # robot.logger.info('Moving the robot back.')
    # lease = mobility_client.lease_keep_alive()

    command_client = robot.ensure_client('bosdyn.client.robot_command')
    command = robot_command.RobotCommandBuilder.synchro_se2_trajectory_point_command(
        goal_x=-distance, goal_y=0, goal_heading=0, frame_name='body')

    command_client.robot_command(command)
    robot.logger.info('Move back command issued.')
    print('Move back command issued.')


def array_to_qpximap(image_array):
    image_array = np.ascontiguousarray(image_array, dtype=np.uint8)

    # NumPy 배열을 QImage 객체로 변환
    height, width, channels = image_array.shape
    bytes_per_line = channels * width

    # qimage = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGB888)
    qimage = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
    qpixmap = QPixmap.fromImage(qimage)

    return qpixmap


def depth_array_to_qpximap(image_array):
    image_array = np.ascontiguousarray(image_array, dtype=np.uint16)

    # NumPy 배열을 QImage 객체로 변환
    qimage = get_qimage(image_array)
    # height, width = image_array.shape
    # channels = 2
    # format = QImage.Format_Grayscale16
    # bytes_per_line = channels * width
    #
    # qimage = QImage(image_array.data, width, height, bytes_per_line, format)
    qpixmap = QPixmap.fromImage(qimage)

    return qpixmap


def get_qimage(image):
    if image.shape[-1] == 3:
        image = np.ascontiguousarray(image, dtype=np.uint8)

        height, width, colors = image.shape
        bytesPerLine = 3 * width
        image_format = QImage.Format_RGB888

        # composing image from image data
        image = QImage(bytes(image.data),
                       width,
                       height,
                       bytesPerLine,
                       image_format)

        image = image.rgbSwapped()

    else:
        # 데이터 타입을 uint8로 변환합니다.
        if image.max() != 0:
            depth_data_uint8 = cv2.convertScaleAbs(image, alpha=(255.0 / image.max()))
        else:
            depth_data_uint8 = image

        # Convert the image to grayscale
        # gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height, width = depth_data_uint8.shape
        bytesPerLine = width
        image_format = QImage.Format_Grayscale8

        # composing image from image data
        image = QImage(depth_data_uint8.data,
                       width,
                       height,
                       bytesPerLine,
                       image_format)

    return image
