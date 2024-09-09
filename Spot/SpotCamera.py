import cv2
from bosdyn.api import image_pb2, gripper_camera_param_pb2
from bosdyn.client.image import build_image_request
import numpy as np
from scipy import ndimage


class SpotCamera:
    """
    Spot 로봇의 Camera 기능을 관리하는 클래스입니다.
    이 객체를 통해 로봇에게 컬러 이미지, Depth 데이터 등의 획득 명령을 전송할 수 있습니다.
    """
    def __init__(self):
        """
        SpotCamera 클래스의 생성자입니다.
        """
        self.image_client = None
        self.gripper_client = None
        self.video_mode = False

    def initialize(self, robot):
        self.image_client = robot.image_client
        self.gripper_client = robot.gripper_camera_param_client

    def take_image(self):
        """
        이미지를 촬영하는 메소드입니다.

        Returns:
            np.ndarray: opencv 형태의 이미지
        """
        image = self.image_client.get_image_from_sources(['hand_color_image'])
        return rgb_image_to_opencv(image[0], auto_rotate=False)

    def take_image_from_source(self, camera_name):
        """
        특정 카메라 소스로부터 이미지를 촬영하는 메소드입니다.

        Args:
            camera_name (str): 카메라 소스 이름

        Returns:
            tuple: (image, depth, image_data) 형태의 이미지 데이터
        """
        image_client = self.image_client
        source_name = camera_name
        image_sources = image_client.list_image_sources()
        source = [source for source in image_sources if source.name == source_name]
        pixel_format = image_pb2.Image.PIXEL_FORMAT_RGB_U8
        image_request = [
            build_image_request(source_name, pixel_format=pixel_format)
            # for source in image_sources if source.name == source_name
        ]
        image_responses = image_client.get_image(image_request)

        if pixel_format == image_pb2.Image.PIXEL_FORMAT_DEPTH_U16:
            image = depth_image_to_opencv(image_responses[0], auto_rotate=True)
        else:
            image = rgb_image_to_opencv(image_responses[0], auto_rotate=True)

        return image

    def get_depth(self):
        """
        깊이 이미지를 가져오는 메소드입니다.

        Returns:
            numpy.ndarray: 깊이 이미지 데이터
        """
        pixel_format = image_pb2.Image.PIXEL_FORMAT_DEPTH_U16
        image_format = image_pb2.Image.FORMAT_RAW
        request = build_image_request(image_source_name='hand_depth',
                                      quality_percent=100,
                                      image_format=image_format,
                                      pixel_format=pixel_format)
        response = self.image_client.get_image([request])[0]
        dtype = np.uint16
        img = np.frombuffer(response.shot.image.data, dtype=dtype)

        depth_data = img.reshape(response.shot.image.rows,
                                 response.shot.image.cols)
        depth_data = cv2.rotate(depth_data, cv2.ROTATE_90_CLOCKWISE)

        # depth_data = cv2.imread("UI/widget/test_depth_data_2.png", cv2.IMREAD_UNCHANGED)
        return depth_data

    def get_depth_data(self):
        """Get depth data from ToF sensor."""
        image_responses = self.image_client.get_image_from_sources(["depth"])

        depth_image = None
        for image_response in image_responses:
            if image_response.shot.image.pixel_format == image_pb2.Image.PIXEL_FORMAT_DEPTH_U16:
                depth_image = image_response.shot.image
                break

        if depth_image is None:
            raise ValueError("No depth image received.")

        # Convert depth image to numpy array
        depth_array = np.frombuffer(depth_image.data, dtype=np.uint16)
        depth_array = depth_array.reshape(depth_image.rows, depth_image.cols)
        depth_array = cv2.rotate(depth_array, cv2.ROTATE_90_CLOCKWISE)

        return depth_array

    def get_color_depth(self):
        """
        깊이 이미지를 가져오는 메소드입니다.

        Returns:
            numpy.ndarray: 깊이 이미지 데이터
        """
        pixel_format = image_pb2.Image.PIXEL_FORMAT_DEPTH_U16
        image_format = image_pb2.Image.FORMAT_RAW
        request = build_image_request(image_source_name='hand_depth',
                                      quality_percent=100,
                                      image_format=image_format,
                                      pixel_format=pixel_format)
        response = self.image_client.get_image([request])[0]
        color_depth = color_depth_image_to_opencv(response)
        return color_depth

    def set_resolution(self, resolution):
        camera_mode = None
        if resolution is not None:
            if resolution == '640x480':
                camera_mode = gripper_camera_param_pb2.GripperCameraParams.MODE_640_480_120FPS_UYVY
            elif resolution == '1280x720':
                camera_mode = gripper_camera_param_pb2.GripperCameraParams.MODE_1280_720_60FPS_UYVY
            elif resolution == '1920x1080':
                camera_mode = gripper_camera_param_pb2.GripperCameraParams.MODE_1920_1080_60FPS_MJPG
            elif resolution == '3840x2160':
                camera_mode = gripper_camera_param_pb2.GripperCameraParams.MODE_3840_2160_30FPS_MJPG
            elif resolution == '4096x2160':
                camera_mode = gripper_camera_param_pb2.GripperCameraParams.MODE_4096_2160_30FPS_MJPG
            elif resolution == '4208x3120':
                camera_mode = gripper_camera_param_pb2.GripperCameraParams.MODE_4208_3120_20FPS_MJPG

        params = gripper_camera_param_pb2.GripperCameraParams(
            camera_mode=camera_mode)

        request = gripper_camera_param_pb2.GripperCameraParamRequest(params=params)

        # Send the request
        response = self.gripper_client.set_camera_params(request)


ROTATION_ANGLE = {
    'hand_color_image': 0,
    'hand_depth': 0,
    'back_fisheye_image': 0,
    'frontleft_fisheye_image': -78,
    'frontright_fisheye_image': -102,
    'left_fisheye_image': 0,
    'right_fisheye_image': 180
}


def rgb_image_to_opencv(image, auto_rotate=True):
    """Convert an image proto message to an openCV image."""
    dtype = np.uint8
    img = np.frombuffer(image.shot.image.data, dtype=dtype)
    img = cv2.imdecode(img, -1)

    if auto_rotate:
        img = ndimage.rotate(img, ROTATION_ANGLE[image.source.name])

    return img


def depth_image_to_opencv(image, auto_rotate=True):
    dtype = np.uint16
    img = np.frombuffer(image.shot.image.data, dtype=dtype)
    img = cv2.imdecode(img, -1)
    if auto_rotate:
        img = ndimage.rotate(img, ROTATION_ANGLE[image.source.name])

    return img


def color_depth_image_to_opencv(image, auto_rotate=True):
    # Depth is a raw bytestream
    cv_depth = np.frombuffer(image.shot.image.data, dtype=np.uint16)
    cv_depth = cv_depth.reshape(image.shot.image.rows,
                                image.shot.image.cols)

    min_val = np.min(cv_depth)
    max_val = np.max(cv_depth)
    depth_range = max_val - min_val
    depth8 = (255.0 / depth_range * (cv_depth - min_val)).astype('uint8')
    depth8_rgb = cv2.cvtColor(depth8, cv2.COLOR_GRAY2RGB)
    depth_color = cv2.applyColorMap(depth8_rgb, cv2.COLORMAP_JET)

    out = depth_color

    if auto_rotate:
        if image.source.name[0:5] == 'front' or image.source.name[0:4] == 'hand':
            out = cv2.rotate(depth_color, cv2.ROTATE_90_CLOCKWISE)
        elif image.source.name[0:5] == 'right':
            out = cv2.rotate(depth_color, cv2.ROTATE_180)

    return out
