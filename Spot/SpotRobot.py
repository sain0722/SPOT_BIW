import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from PySide6.QtCore import QTimer, Qt, QThread
from bosdyn.api.docking import docking_pb2
from bosdyn.api.docking.docking_pb2 import DockingCommandResponse
from bosdyn.client import UnableToConnectToRobotError, RpcError, InvalidLoginError, ResponseError
from bosdyn.client.async_tasks import AsyncPeriodicQuery, AsyncTasks
from bosdyn.client.common import maybe_raise, common_lease_errors
from bosdyn.client.docking import DockingClient, blocking_go_to_prep_pose
from bosdyn.client.estop import EstopClient, EstopEndpoint, EstopKeepAlive
from bosdyn.client.frame_helpers import get_a_tform_b, ODOM_FRAME_NAME, HAND_FRAME_NAME
from bosdyn.client.graph_nav import GraphNavClient
from bosdyn.client.gripper_camera_param import GripperCameraParamClient
from bosdyn.client.image import ImageClient
from bosdyn.client.lease import LeaseClient, LeaseKeepAlive, ResourceAlreadyClaimedError
from bosdyn.client.map_processing import MapProcessingServiceClient
from bosdyn.client.power import PowerClient
from bosdyn.client.recording import GraphNavRecordingServiceClient
from bosdyn.client.robot_command import RobotCommandClient, RobotCommandBuilder, CommandFailedError, blocking_stand
from bosdyn.client.robot_id import RobotIdClient
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.client.time_sync import TimeSyncClient, TimeSyncEndpoint
from bosdyn.client.world_object import WorldObjectClient
import bosdyn.api.robot_state_pb2 as robot_state_proto
import bosdyn.api.power_pb2 as PowerServiceProto
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
from bosdyn.geometry import EulerZXY

from bosdyn.util import secs_to_hms, now_sec, seconds_to_timestamp
import bosdyn.client
from bosdyn.mission.client import MissionClient

import DefineGlobal
from Spot.CarInspection.CarInspection import SpotInspection, MoveWithFiducial
from Spot.SpotCameraParameter import SpotCameraParameter
from Spot.SpotEstop import SpotEstop
from Spot.SpotGraphNav import SpotGraphNav, SpotGraphNavRecording
from Spot.SpotArm import SpotArm
from Spot.SpotCamera import SpotCamera
from Spot.SpotCommand import try_grpc, RobotCommandExecutor
from Spot.SpotMove import SpotMove
from Thread.DockingThread import DockingThread

ASYNC_CAPTURE_RATE = 40  # milliseconds, 25 Hz


class Robot:
    """
    Spot 로봇과의 연결을 관리하고 제어하기 위한 클래스입니다.
    이 객체를 통해 Spot 로봇과 통신하고, 로봇 상태를 확인하며 로봇에 명령을 전송할 수 있습니다.

    Attributes
    ----------
    dock_id (int): 로봇이 도킹되는 ID를 나타내는 속성입니다.

    """
    dock_id = 525
    # dock_id = 532

    # Robot state
    mode = None
    has_robot_control = False
    motors_powered = False
    is_connected = False

    try_reconnect_attempt = 0

    def __init__(self):
        self.robot = None
        # self.logger = logging.getLogger(self._name or 'bosdyn.Robot')
        self.logger = logging.getLogger('bosdyn.Robot')
        self.robot_id                    = None
        self.power_client                = None
        self.estop_client                = None
        self.lease_client                = None
        self.robot_state_client          = None
        self.robot_command_client        = None
        self.image_client                = None
        self.gripper_camera_param_client = None
        self.world_object_client         = None
        self.graph_nav_client            = None
        self.time_sync_client            = None

        # Setup the recording service client.
        self.recording_client = None
        self.map_processing_client = None

        # Mission Client
        self.mission_client = None

        # lease
        self._lease_keepalive = None

        # command
        self.robot_commander            = RobotCommandExecutor()
        self.robot_move_manager         = SpotMove()
        self.robot_arm_manager          = SpotArm()
        self.robot_camera_manager       = SpotCamera()
        self.robot_camera_param_manager = SpotCameraParameter()
        self.robot_graphnav_manager     = SpotGraphNav()
        self.robot_recording_manager    = SpotGraphNavRecording()
        self.robot_inspection_manager   = SpotInspection()
        self.robot_fiducial_manager     = MoveWithFiducial()
        self.robot_estop_manager        = SpotEstop()

        self._robot_state_task = None
        self.async_tasks       = None

        self.get_state_thread  = None

        self.command_dictionary = {
            "lease"      : self._toggle_lease,
            "power"      : self._toggle_power,
            "estop"      : self._toggle_estop,
            "get_lease"  : self._lease_str,
            "get_power"  : self._power_state_str,
            "get_battery": self._battery_str,
            "get_estop"  : self._estop_str
        }

        self.body_height = 0.0
        self.stand_yaw   = 0.0
        self.stand_roll  = 0.0
        self.stand_pitch = 0.0

        self.stand_height_change = False
        self.stand_roll_change = False
        self.stand_pitch_change = False
        self.stand_yaw_change = False

    def connect(self, hostname, username, password, dock_id):
        """
        로봇에 연결하는 메소드입니다.

        Args:
            hostname (str): 호스트 이름
            username (str): 사용자 이름
            password (str): 비밀번호
            dock_id  (int): Dock 번호

        Returns:
            tuple: 연결 성공 여부와 메시지 (connect, content)
        """
        if self.robot:
            return False, 'Already Connected'
        try:
            connect, content = self.create_robot(hostname, username, password)
        except UnableToConnectToRobotError as disconnect_error:
            return False, disconnect_error.error_message

        if connect:
            self.dock_id = dock_id
            self.initialize_robot()
            self.is_connected = True
            self.try_reconnect_attempt = 0

        return connect, content

    def create_robot(self, hostname, username, password):
        """
        로봇 객체를 생성하는 메소드입니다.

        Args:
            hostname (str): 호스트 이름
            username (str): 사용자 이름
            password (str): 비밀번호

        Returns:
            tuple: 생성 성공 여부와 메시지 (create, content)
        """

        try:
            sdk = bosdyn.client.create_standard_sdk('TWIM', [MissionClient])
            robot = sdk.create_robot(hostname)
            robot.authenticate(username=username, password=password, timeout=1.5)

            self.robot = robot
            return True, 'succeed'

        except UnableToConnectToRobotError as exc:
            print(f"{exc}")
            raise exc

        except RpcError as exc:
            print(exc)
            return False, exc.error_message

        except InvalidLoginError as exc:
            print(exc)
            return False, exc.error_message

        except Exception as exc:
            print(exc)
            return False, "Exception"

    def initialize_robot(self):
        """
        로봇을 초기화하는 메소드입니다.
        """
        if self.robot is None:
            return

        self.robot_id = self.robot.ensure_client(RobotIdClient.default_service_name).get_id(timeout=0.4)

        self.power_client                = self.robot.ensure_client(PowerClient.default_service_name)
        self.lease_client                = self.robot.ensure_client(LeaseClient.default_service_name)
        self.estop_client                = self.robot.ensure_client(EstopClient.default_service_name)

        self.robot_state_client          = self.robot.ensure_client(RobotStateClient.default_service_name)
        self.robot_command_client        = self.robot.ensure_client(RobotCommandClient.default_service_name)
        self.image_client                = self.robot.ensure_client(ImageClient.default_service_name)

        self.gripper_camera_param_client = self.robot.ensure_client(GripperCameraParamClient.default_service_name)
        self.world_object_client         = self.robot.ensure_client(WorldObjectClient.default_service_name)

        self.graph_nav_client            = self.robot.ensure_client(GraphNavClient.default_service_name)
        self.recording_client            = self.robot.ensure_client(GraphNavRecordingServiceClient.default_service_name)
        self.map_processing_client       = self.robot.ensure_client(MapProcessingServiceClient.default_service_name)

        self.time_sync_client = self.robot.ensure_client(TimeSyncClient.default_service_name)
        self.time_sync_endpoint = TimeSyncEndpoint(self.time_sync_client)

        self.establish_timesync()

        # Create the client for Mission Service
        self.mission_client = self.robot.ensure_client(MissionClient.default_service_name)

        # client_metadata
        session_name = 'recoding_session_test'
        user_name = self.robot._current_user
        client_metadata = GraphNavRecordingServiceClient.make_client_metadata(
            session_name=session_name, client_username=user_name, client_id='RecordingClient',
            client_type='Python SDK')

        # ESTOP SETTING
        # Force server to set up a single endpoint system
        # timeout_sec = 5
        # ep = EstopEndpoint(self.estop_client, None, timeout_sec)
        # ep.force_simple_setup()

        # # Begin periodic check-in between keep-alive and robot
        # self.estop_keep_alive = EstopKeepAlive(ep)

        # commander initialize
        self.robot_commander.initialize(self)
        self.robot_move_manager.initialize(self)
        self.robot_arm_manager.initialize(self)
        self.robot_camera_manager.initialize(self)
        self.robot_camera_param_manager.initialize(self)
        self.robot_graphnav_manager.initialize(self)
        self.robot_recording_manager.initialize(self, client_metadata)
        self.robot_inspection_manager.initialize(self)
        self.robot_fiducial_manager = self.robot_inspection_manager.move_with_fiducial
        self.robot_estop_manager.initialize(self.estop_client)

        self._robot_state_task = AsyncRobotState(self.robot_state_client)
        self.async_tasks       = AsyncTasks([self._robot_state_task])
        self.async_tasks.update()

        self.update_task_timer = QTimer()
        self.update_task_timer.setTimerType(Qt.PreciseTimer)
        self.update_task_timer.timeout.connect(self._update_tasks)
        self.update_task_timer.start(ASYNC_CAPTURE_RATE)

        # self.update_task_thread = UpdateTaskTimer(self._update_tasks)
        # self.update_task_thread.start()

        # self.start_getting_state()

    @property
    def robot_state(self):
        """Get latest robot state proto."""
        return self._robot_state_task.proto

    @property
    def robot_lease_keepalive(self):
        return self._lease_keepalive

    def robot_is_power_off(self):
        return self._power_state() == robot_state_proto.PowerState.STATE_OFF

    def _update_tasks(self):
        """Updates asynchronous robot state captures"""
        try:
            self.async_tasks.update()
            if self.try_reconnect_attempt > 0:
                self.try_reconnect_attempt = 0
        except UnableToConnectToRobotError:
            # Try Reconnect
            print("The robot may be offline or otherwise unreachable.")
            self.is_connected = False
            if self.try_reconnect_attempt < 5:
                self.reconnect()
                self.try_reconnect_attempt += 1

        except Exception as e:
            print(f"SpotRobot.py - update_tasks Raised Error: {e}")

        self.motors_powered = self._power_state() == robot_state_proto.PowerState.STATE_ON

        if self._lease_keepalive:
            self.has_robot_control = self._lease_keepalive.is_alive()
        else:
            self.has_robot_control = False

    def establish_timesync(self):
        # makes weveral RPC calls to TimeSyncUpdate, continually updaing the clock skew estimate.
        did_establish = self.time_sync_endpoint.establish_timesync(max_samples=10, break_on_success=False)
        return did_establish

    def reconnect(self):
        print("Try to Reconnect.")
        self.robot = None
        self.try_reconnect_attempt += 1
        hostname = DefineGlobal.SPOT_HOSTNAME
        username = DefineGlobal.SPOT_USERNAME
        password = DefineGlobal.SPOT_PASSWORD
        dock_id  = DefineGlobal.SPOT_DOCK_ID
        is_connect, message = self.connect(hostname, username, password, dock_id)
        return is_connect, message

    def _request_power_on(self):
        """
        로봇의 전원을 켜는 메소드입니다.

        Returns:
            int: 전원 상태 코드
        """
        request = PowerServiceProto.PowerCommandRequest.REQUEST_ON
        return self.power_client.power_command_async(request)

    def _safe_power_off(self):
        """
        로봇의 전원을 안전하게 끄는 메소드입니다.
        """
        # bosdyn.client.power.power_off(self.power_client)
        # self._start_robot_command('safe_power_off', RobotCommandBuilder.safe_power_off_command())
        self.robot_commander.start_robot_command('safe_power_off', RobotCommandBuilder.safe_power_off_command())
        self.motors_powered = False

    def dock(self):
        """
        로봇을 도킹시키는 메소드입니다.

        Returns:
            bool: 도킹 성공 여부
        """
        if self.robot_arm_manager.is_gripper_open():
            self.robot_arm_manager.gripper_close()

        blocking_dock_robot(self.robot, self.dock_id)

        # make sure standing
        # blocking_stand(self.robot_command_client)

        # Create a queue for the result
        # q = queue.Queue()
        #
        # # Define a new function that calls the original function and puts the result in the queue
        # def wrapper_func():
        #     result = blocking_dock_robot(self.robot, self.dock_id)
        #     q.put(result)
        #
        # # Dock the robot
        # self.dock_thread = threading.Thread(target=wrapper_func, daemon=True)
        # self.dock_thread.start()
        #
        # # Wait for the result
        # return_value = q.get()
        # return return_value

    def undock(self):
        """
        로봇을 언도킹시키는 메소드입니다.

        Returns:
            bool: 언도킹 성공 여부
        """
        result = blocking_undock(self.robot)

        # make sure standing
        # blocking_stand(self.robot_command_client)
        # blocking_go_to_prep_pose(self.robot, self.dock_id)

        # blocking_undock(self.robot)
        # Create a queue for the result
        # q = queue.Queue()
        #
        # # Define a new function that calls the original function and puts the result in the queue
        # def wrapper_func():
        #     result = blocking_undock(self.robot)
        #     q.put(result)
        #
        # # Dock the robot
        # self.dock_thread = threading.Thread(target=wrapper_func, daemon=True)
        # self.dock_thread.start()
        #
        # # Wait for the result
        # return_value = q.get()
        return result

    def get_current_joint_state(self):
        """
        현재 로봇의 관절 상태를 가져오는 메소드입니다.

        Returns:
            dict: 관절 이름과 위치로 이루어진 딕셔너리
        """
        state = self.robot_state
        if not state:
            return None
        joint_states = state.kinematic_state.joint_states
        joint_names = ['arm0.sh0', 'arm0.sh1', 'arm0.el0', 'arm0.el1', 'arm0.wr0', 'arm0.wr1']
        joint_pos_list = [
            state.position.value
            for state in joint_states if state.name in joint_names
        ]
        joint_pos_dict = {
            name.split(".")[1]: round(value, 4)
            for name, value in zip(joint_names, joint_pos_list)
        }

        return joint_pos_dict

    def get_current_hand_position(self, key):
        """
        현재 로봇의 손 위치를 가져오는 메소드입니다.

        Args:
            key (str): 위치를 가져올 부위 (hand, body, flat_body, gpe, odom, vision, link_wr1)

        Returns:
            dict: 위치와 회전으로 이루어진 딕셔너리
        """
        if not self.robot_state:
            return None

        kinematic_state = self.robot_state.kinematic_state
        return kinematic_state.transforms_snapshot.child_to_parent_edge_map[key].parent_tform_child

    def get_odom_tform_hand(self):
        """
        로봇의 ODOM 프레임과 Hand 프레임 사이의 변환 행렬을 가져오는 메소드입니다.

        Returns:
            geometry_msgs.msg.Transform: 변환 행렬
        """
        if not self.robot_state:
            return None

        odom_tform_hand = get_a_tform_b(self.robot_state.kinematic_state.transforms_snapshot,
                                        ODOM_FRAME_NAME, HAND_FRAME_NAME)

        return odom_tform_hand

    def get_hand_position_dict(self):
        """
        Hand 프레임의 위치와 회전을 딕셔너리 형태로 반환하는 메소드입니다.

        Returns:
            dict: Hand 위치와 회전
        """
        hand_snapshot = self.get_current_hand_position('hand')
        if hand_snapshot is None:
            return

        position, rotation = se3pose_to_dict(hand_snapshot)
        hand_pose = {
            "position": position,
            "rotation": rotation
        }
        return hand_pose

    def get_odom_tform_hand_dict(self):
        """
        ODOM 프레임과 손 프레임 사이의 변환 행렬을 딕셔너리 형태로 반환하는 메소드입니다.

        Returns:
            dict: ODOM 프레임 위치와 회전
        """
        odom_tform_hand = self.get_odom_tform_hand()
        if odom_tform_hand is None:
            return

        position, rotation = se3pose_to_dict(odom_tform_hand)
        return position, rotation

    def _toggle_lease(self):
        """
        제어권(Lease) 활성화 또는 비활성화하는 메소드입니다.

        Returns:
            str: 메시지
        """

        """toggle lease acquisition. Initial state is acquired"""
        if self.lease_client is not None:
            if self._lease_keepalive is None:
                try:
                    message = "lease acquire is succeed."
                    self.lease_client.acquire()
                    self.has_robot_control = True

                except ResourceAlreadyClaimedError:
                    message = "the robot is already standing via the tablet. Will take over from the tablet."
                    self.lease_client.take()
                    self.has_robot_control = True

                self._lease_keepalive = LeaseKeepAlive(self.lease_client,
                                                       must_acquire=True,
                                                       return_at_exit=True,
                                                       on_failure_callback=self.lease_keepalive_failure_callback)
            else:
                message = "return lease is succeed."
                self._lease_keepalive.shutdown()
                self._lease_keepalive = None
                self.has_robot_control = False

        else:
            message = "Must be connect the robot."

        return message

    def lease_keepalive_failure_callback(self, exc):
        print("resuming check-in")
        print(exc)
        try:
            self._lease_keepalive.shutdown()
        except RuntimeError as ex:
            print(f"SpotRobot.py: {ex}")
        self._lease_keepalive = None
        # try:
        #     self._lease_keepalive.shutdown()
        # except Exception as e:
        #     print(e)

    def _toggle_power(self):
        """
        전원을 켜거나 끄는 메소드입니다.

        Returns:
            int or str: 전원 상태 코드 또는 메시지
        """
        power_state = self._power_state()
        if power_state is None:
            # self.add_message('Could not toggle power because power state is unknown')
            print('Could not toggle power because power state is unknown')
            return

        if power_state == robot_state_proto.PowerState.STATE_OFF:
            # try_grpc_async("powering-on", self._request_power_on)
            result = self._request_power_on()
            result = result.result().status

            if result == 1:
                result = 'POWER_STATUS_OK'
        else:
            result = try_grpc("powering-off", self._safe_power_off)

        return result

    def _power_state(self):
        """
        전원 상태를 반환하는 메소드입니다.

        Returns:
            int: 전원 상태 코드
        """
        state = self.robot_state
        if not state:
            return None
        return state.power_state.motor_power_state

    def _lease_str(self):
        """
        Lease 상태를 문자열로 반환하는 메소드입니다.

        Returns:
            str: Lease 상태
        """
        if self._lease_keepalive is None:
            alive = 'STOPPED'
            lease = 'RETURNED'
        else:
            try:
                _lease = self._lease_keepalive.lease_wallet.get_lease()
                # lease = '{}:{}'.format(_lease.lease_proto.resource, _lease.lease_proto.sequence)
                lease = 'ON'
            except bosdyn.client.lease.Error:
                lease = '...'
            except bosdyn.client.LeaseUseError as e:
                lease = e

            if self._lease_keepalive.is_alive():
                alive = 'RUNNING'
            else:
                alive = 'STOPPED'
        # return '{} {}'.format(lease, alive)
        return alive

    def _toggle_estop(self):
        try:
            if not self.robot_estop_manager.estop_keepalive:
                self.robot_estop_manager.start_estop()
            else:
                self.robot_estop_manager.return_estop()
        except Exception as e:
            print(f"SpotRobot.py - SPOT E-STOP Exception. {e}")

    def _estop_state(self):
        """
        None
        OK
        ERROR
        Disabled
        """
        state_str = self.robot_estop_manager.get_keep_alive_status()
        return state_str

    def _estop_str(self):
        estop_state = self._estop_state()
        software_estop_state_str = "-"
        try:
            software_estop_state = self.robot_state.estop_states[2].state
            # 1: ESTOPPED
            # 2: NOT ESTOPPED
            if software_estop_state == 1:
                software_estop_state_str = "E-STOPPED"
            elif software_estop_state == 2:
                software_estop_state_str = "NOT E-STOPPED"
        except Exception as e:
            print(f"SpotRobot.py - Raised Exception. \n{e}")

        return estop_state, software_estop_state_str

    def _power_state_str(self):
        """
        전원 상태를 문자열로 반환하는 메소드입니다.

        Returns:
            str: 전원 상태
        """
        if not self._robot_state_task:
            return ''

        power_state = self._power_state()
        if power_state is None:
            state_str = ""
        else:
            state_str = robot_state_proto.PowerState.MotorPowerState.Name(power_state)
        return '{}'.format(state_str[6:])  # get rid of STATE_ prefix

    def _battery_str(self):
        """
        배터리 상태를 문자열로 반환하는 메소드입니다.

        Returns:
            str: 배터리 상태
        """
        if not self._robot_state_task:
            return ''

        if self.robot_state is None:
            status    = ""
            bar_val   = 0
            time_left = ""
        else:
            battery_state = self.robot_state.battery_states[0]
            status = battery_state.Status.Name(battery_state.status)
            status = status[7:]  # get rid of STATUS_ prefix
            if battery_state.charge_percentage.value:
                bar_val = battery_state.charge_percentage.value
                bar_len = int(bar_val) // 5
            else:
                bar_val = 0
            time_left = ""
            if battery_state.estimated_runtime:
                time_left = secs_to_hms(battery_state.estimated_runtime.seconds)
        return status, bar_val, time_left

    def spot_is_charging(self):
        # STATUS_CHARGING: 2
        return self.robot_state.battery_states[0].status == 2

    def is_battery_low(self, threshold):
        """
        배터리 수준이 threshold% 이하인지 확인하는 메소드입니다.

        Returns:
            bool: 배터리 수준이 threshold% 이하인 경우 True, 그렇지 않으면 False
            int:  battery value
        """
        _, bar_val, _ = self._battery_str()
        return bar_val <= threshold

    def get_battery_value(self):
        return self.robot_state.battery_states[0].charge_percentage.value

    def blocking_stand(self):
        body_control = spot_command_pb2.BodyControlParams(
                        body_assist_for_manipulation=spot_command_pb2.BodyControlParams.
                        BodyAssistForManipulation(enable_hip_height_assist=True, enable_body_yaw_assist=False))
        blocking_stand(self.robot_command_client, timeout_sec=10,
                       params=spot_command_pb2.MobilityParams(body_control=body_control))

        stand_command = RobotCommandBuilder.synchro_stand_command(
            params=spot_command_pb2.MobilityParams(body_control=body_control))

    def robot_height_change(self, height):
        """Changes robot body height.

        Args:
            direction: 1 to increase height, -1 to decrease height.
        """
        # HEIGHT_CHANGE = 0.1  # m per command
        HEIGHT_MAX = 0.3  # m

        # self.body_height = self.body_height + direction * HEIGHT_CHANGE
        # self.body_height = min(HEIGHT_MAX, self.body_height)
        # self.body_height = max(-HEIGHT_MAX, self.body_height)
        self.robot_move_manager.body_height = height
        self._orientation_cmd_helper(height=height)

    def _reset_height(self):
        """Resets robot body height to normal stand height.
        """

        self.body_height = 0.0
        self._orientation_cmd_helper(height=self.body_height)
        self.stand_height_change = False

    def _issue_robot_command(self, command, endtime=None):
        """Check that the lease has been acquired and motors are powered on before issuing a command.

        Args:
            command: RobotCommand message to be sent to the robot.
            endtime: Time (in the local clock) that the robot command should stop.
        """
        if not self.has_robot_control:
            print('Must have control by acquiring a lease before commanding the robot.')
            return
        if not self.motors_powered:
            print('Must have motors powered on before commanding the robot.')
            return

        self.robot_command_client.robot_command_async(command, end_time_secs=endtime)

    def _orientation_cmd_helper(self, yaw=0.0, roll=0.0, pitch=0.0, height=0.0):
        """Helper function that commands the robot with an orientation command;
        Used by the other orientation functions.

        Args:
            yaw: Yaw of the robot body. Defaults to 0.0.
            roll: Roll of the robot body. Defaults to 0.0.
            pitch: Pitch of the robot body. Defaults to 0.0.
            height: Height of the robot body from normal stand height. Defaults to 0.0.
        """

        VELOCITY_CMD_DURATION = 0.6  # seconds

        if not self.motors_powered:
            return

        orientation = EulerZXY(yaw, roll, pitch)
        cmd = RobotCommandBuilder.synchro_stand_command(body_height=height,
                                                        footprint_R_body=orientation)
        self._issue_robot_command(cmd, endtime=time.time() + VELOCITY_CMD_DURATION)


    # endregion


LOGGER = logging.getLogger()


class AsyncRobotState(AsyncPeriodicQuery):
    """Grab robot state."""

    def __init__(self, robot_state_client):
        super(AsyncRobotState, self).__init__("robot_state", robot_state_client, LOGGER,
                                              period_sec=0.2)

    def _start_query(self):
        return self._client.get_robot_state_async()


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Timed out!")


def blocking_dock_robot(robot, dock_id, num_retries=4, timeout=30):
    """Blocking helper that takes control of the robot and docks it.

    Args:
        robot: The instance of the robot to control.
        dock_id: The ID of the dock to dock at.
        num_retries: Optional, number of attempts.

    Returns:
        The number of retries required

    Raises:
        CommandFailedError: The robot was unable to be docked. See error for details.
    """
    docking_client = robot.ensure_client(DockingClient.default_service_name)

    attempt_number = 0
    docking_success = False

    # Try to dock the robot
    while attempt_number < num_retries and not docking_success:
        attempt_number += 1
        converter = robot.time_sync.get_robot_time_converter()
        start_time = converter.robot_seconds_from_local_seconds(now_sec())
        cmd_end_time = start_time + timeout
        cmd_timeout = cmd_end_time + 10  # client side buffer

        prep_pose = (docking_pb2.PREP_POSE_USE_POSE if
                     (attempt_number % 2) else docking_pb2.PREP_POSE_SKIP_POSE)

        try:
            cmd_id = docking_client.docking_command(dock_id, robot.time_sync.endpoint.clock_identifier,
                                                    seconds_to_timestamp(cmd_end_time), prep_pose)
        except ResponseError as exc:
            return exc.error_message

        while converter.robot_seconds_from_local_seconds(now_sec()) < cmd_timeout:
            feedback = docking_client.docking_command_feedback_full(cmd_id)
            maybe_raise(common_lease_errors(feedback))
            status = feedback.status
            if status == docking_pb2.DockingCommandFeedbackResponse.STATUS_IN_PROGRESS:
                # keep waiting/trying
                time.sleep(1)
            elif status == docking_pb2.DockingCommandFeedbackResponse.STATUS_DOCKED:
                docking_success = True
                break
            elif (status in [
                    docking_pb2.DockingCommandFeedbackResponse.STATUS_MISALIGNED,
                    docking_pb2.DockingCommandFeedbackResponse.STATUS_ERROR_COMMAND_TIMED_OUT,
            ]):
                # Retry
                break
            else:
                return CommandFailedError(
                    "Docking Failed, status: '%s'" %
                    docking_pb2.DockingCommandFeedbackResponse.Status.Name(status))

    if docking_success:
        return attempt_number - 1

    # Try and put the robot in a safe position
    try:
        blocking_go_to_prep_pose(robot, dock_id)
    except CommandFailedError:
        pass

    # Raise error on original failure to dock
    return CommandFailedError("Docking Failed, too many attempts")


def blocking_undock(robot, timeout=20):
    """Blocking helper that undocks the robot from the currently docked dock.

    Args:
        robot: The instance of the robot to control.

    Returns:
        None

    Raises:
        CommandFailedError: The robot was unable to undock. See error for details.
    """
    docking_client = robot.ensure_client(DockingClient.default_service_name)

    converter = robot.time_sync.get_robot_time_converter()
    start_time = converter.robot_seconds_from_local_seconds(now_sec())
    cmd_end_time = start_time + timeout
    cmd_timeout = cmd_end_time + 10  # client side buffer
    try:
        cmd_id = docking_client.docking_command(0, robot.time_sync.endpoint.clock_identifier,
                                                seconds_to_timestamp(cmd_end_time),
                                                docking_pb2.PREP_POSE_UNDOCK)
    except bosdyn.client.exceptions.ResponseError as e:
        return e.error_message
    except bosdyn.client.lease.NoSuchLease as e:
        return e

    while converter.robot_seconds_from_local_seconds(now_sec()) < cmd_timeout:
        feedback = docking_client.docking_command_feedback_full(cmd_id)
        maybe_raise(common_lease_errors(feedback))
        status = feedback.status
        if status == docking_pb2.DockingCommandFeedbackResponse.STATUS_IN_PROGRESS:
            # keep waiting/trying
            time.sleep(1)
        elif status == docking_pb2.DockingCommandFeedbackResponse.STATUS_AT_PREP_POSE:
            return
        else:
            raise CommandFailedError("Failed to undock the robot, status: '%s'" %
                                     docking_pb2.DockingCommandFeedbackResponse.Status.Name(status))

    raise CommandFailedError("Error undocking the robot, timeout exceeded.")


def se3pose_to_dict(pose_proto):
    position = {
        'x': round(pose_proto.position.x, 4),
        'y': round(pose_proto.position.y, 4),
        'z': round(pose_proto.position.z, 4)
    }

    rotation = {
        'x': round(pose_proto.rotation.x, 6),
        'y': round(pose_proto.rotation.y, 6),
        'z': round(pose_proto.rotation.z, 6),
        'w': round(pose_proto.rotation.w, 6)
    }

    return position, rotation


class UpdateTaskTimer(QThread):
    def __init__(self, update_task_function):
        super().__init__()
        self.update_task = update_task_function
        self.running = True

    def run(self):
        self.running = True
        while self.running:
            self.update_task()
            time.sleep(0.4)

    def stop(self):
        self.running = False
        self.wait()
        self.quit()
