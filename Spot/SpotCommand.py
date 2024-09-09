import time

from bosdyn.api import arm_command_pb2, synchronized_command_pb2, robot_command_pb2, geometry_pb2
from bosdyn.client import ResponseError, RpcError, LeaseUseError
from bosdyn.client.lease import Error as LeaseBaseError
from bosdyn.client.robot_command import RobotCommandBuilder


def try_grpc(desc, thunk):
    """
    gRPC 호출을 시도하고, 에러 발생 시 해당 에러 메시지를 반환하는 함수입니다.

    Args:
        desc (str): 작업 설명
        thunk (function): gRPC 호출 함수

    Returns:
        str: 에러 메시지 또는 호출 결과
    """
    try:
        return thunk()
    except (ResponseError, RpcError) as err:
        # self.add_message("Failed {}: {}".format(desc, err))
        # message = "{}: {}".format(desc, err)
        message = err.error_message
        print(err)
        return err
    except LeaseBaseError as err:
        message = err
        return message
    except LeaseUseError as err:
        raise err
        # return "Failed {}: {}".format(desc, err)


def try_grpc_async(desc, thunk):
    """
    비동기 gRPC 호출을 시도하고, 에러 발생 시 해당 에러 메시지를 출력하는 함수입니다.

    Args:
        desc (str): 작업 설명
        thunk (function): 비동기 gRPC 호출 함수
    """
    def on_future_done(fut):
        try:
            fut.result()
        except (ResponseError, RpcError, LeaseBaseError) as err:
            # self.add_message("Failed {}: {}".format(desc, err))
            message = "{}: {}".format(desc, err)
            print(message)
            return message

    future = thunk()
    future.add_done_callback(on_future_done)


def make_robot_command(arm_joint_traj, gripper_open_flag=False):
    """
    ArmJointTrajectory를 사용하여 RobotCommand를 생성하는 헬퍼 함수입니다.
    생성된 커맨드는 주어진 경로를 따라 이동하는 ArmJointMoveCommand를 가지는 SynchronizedCommand입니다.

    Args:
        arm_joint_traj (ArmJointTrajectory): 이동 경로를 포함하는 ArmJointTrajectory 객체
        gripper_open_flag (bool): 그리퍼를 열지 여부를 나타내는 플래그

    Returns:
        RobotCommand: 생성된 로봇 커맨드 객체
    """
    joint_move_command = arm_command_pb2.ArmJointMoveCommand.Request(trajectory=arm_joint_traj)
    arm_command = arm_command_pb2.ArmCommand.Request(arm_joint_move_command=joint_move_command)
    sync_arm = synchronized_command_pb2.SynchronizedCommand.Request(arm_command=arm_command)
    arm_sync_robot_cmd = robot_command_pb2.RobotCommand(synchronized_command=sync_arm)

    if gripper_open_flag:
        # Keep the gripper open the whole time, so we can get an image.
        arm_sync_robot_cmd = RobotCommandBuilder.claw_gripper_open_fraction_command(
            1.0, build_on_command=arm_sync_robot_cmd)

    return RobotCommandBuilder.build_synchro_command(arm_sync_robot_cmd)


class RobotCommandExecutor:
    """
    Spot 로봇의 커맨드 실행을 담당하는 클래스입니다.
    """
    def __init__(self):
        """
        RobotCommandExecutor 클래스의 생성자입니다.

        Args:
            robot: Robot 객체
        """
        self._robot = None
        self.robot_command_client = None
        self.VELOCITY_CMD_DURATION = 0.6  # seconds

    def initialize(self, robot):
        """
        RobotCommandExecutor 클래스를 초기화합니다.

        Args:
            robot: Robot 객체
        """
        self._robot = robot.robot
        self.robot_command_client  = robot.robot_command_client

    def start_robot_command(self, desc, command_proto, end_time_secs=None):
        """
        로봇 커맨드를 시작하는 메소드입니다.

        Args:
            desc (str): 커맨드 설명
            command_proto (RobotCommand): 시작할 로봇 커맨드 객체
            end_time_secs (float): 커맨드 종료 시간 (epoch 시간)

        Returns:
            str: 성공적으로 시작된 커맨드 ID 또는 에러 메시지
        """
        def _start_command():
            return self.robot_command_client.robot_command(lease=None, command=command_proto,
                                                           end_time_secs=end_time_secs)

        return try_grpc(desc, _start_command)

    def velocity_cmd_helper(self, desc='', v_x=0.0, v_y=0.0, v_rot=0.0, body_height=0.0):
        """
        속도 커맨드를 보내는 헬퍼 메소드입니다.

        Args:
            desc (str): 커맨드 설명
            v_x (float): x 방향 속도
            v_y (float): y 방향 속도
            v_rot (float): 회전 속도

        Returns:
            str: 성공적으로 시작된 커맨드 ID 또는 에러 메시지
        """
        return self.start_robot_command(
                desc, RobotCommandBuilder.synchro_velocity_command(v_x=v_x, v_y=v_y, v_rot=v_rot, body_height=body_height),
                end_time_secs=time.time() + self.VELOCITY_CMD_DURATION)

    def joint_move_cmd_helper(self, params, desc='', time_secs=1.0, flag=False):
        """
        관절 이동 커맨드를 보내는 헬퍼 메소드입니다.

        Args:
            params (tuple): 관절 각도 정보 (sh0, sh1, el0, el1, wr0, wr1)
            desc (str): 커맨드 설명
            time_secs (float): 이동 시간 (초)
            flag (bool): 그리퍼 열기 여부

        Returns:
            str: 성공적으로 시작된 커맨드 ID 또는 에러 메시지
        """
        sh0, sh1, el0, el1, wr0, wr1 = params
        # time_secs = JOINT_TIME_SEC
        traj_point = RobotCommandBuilder.create_arm_joint_trajectory_point(
            sh0, sh1, el0, el1, wr0, wr1, time_since_reference_secs=time_secs)

        arm_joint_traj = arm_command_pb2.ArmJointTrajectory(points=[traj_point])
        arm_command = make_robot_command(arm_joint_traj, flag)

        # Open the gripper
        gripper_command = RobotCommandBuilder.claw_gripper_open_fraction_command(1.0)

        # Build the proto
        command = RobotCommandBuilder.build_synchro_command(gripper_command, arm_command)

        cmd_id = self.start_robot_command(desc=desc, command_proto=command)
        return cmd_id

    def wait_until_arm_arrives(self, cmd_id, timeout=5):
        """
        로봇 팔이 목표 위치에 도착할 때까지 대기하는 메소드입니다.

        Args:
            cmd_id (str): 대기할 커맨드 ID
            timeout (float): 최대 대기 시간 (초)
        """
        # Wait until the arm arrives at the goal.
        start_time = time.time()
        end_time = start_time + timeout
        while time.time() < end_time:
            try:
                feedback_resp = self.robot_command_client.robot_command_feedback(cmd_id)
            except TypeError:
                print("[Error]", cmd_id)
                return

            print('Distance to final point: ' + '{:.2f} meters'.format(
                feedback_resp.feedback.synchronized_feedback.arm_command_feedback.
                arm_cartesian_feedback.measured_pos_distance_to_goal) + ', {:.2f} radians'.format(
                    feedback_resp.feedback.synchronized_feedback.arm_command_feedback.
                    arm_cartesian_feedback.measured_rot_distance_to_goal))

            if feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.status == arm_command_pb2.ArmCartesianCommand.Feedback.STATUS_TRAJECTORY_COMPLETE:
                # if feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.measured_rot_distance_to_goal < 0.03:
                print('Move complete.')
                break

            # if feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.measured_pos_distance_to_goal == 0 and \
            #    feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.measured_rot_distance_to_goal == 0:
            #     print("Move Arrived.")
            #     break

            time.sleep(0.1)

    def wait_command(self, cmd_id, timeout=5):
        while True:
            feedback_resp = self.robot_command_client.robot_command_feedback(cmd_id)
            measured_pos_distance_to_goal = feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.measured_pos_distance_to_goal
            measured_rot_distance_to_goal = feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.measured_rot_distance_to_goal

            if feedback_resp.feedback.synchronized_feedback.arm_command_feedback.arm_cartesian_feedback.status == arm_command_pb2.ArmCartesianCommand.Feedback.STATUS_TRAJECTORY_COMPLETE:
                print('Move complete.')
                break
            time.sleep(0.1)

    def feedback_test(self, cmd_id):
        feedback_resp = self.robot_command_client.robot_command_feedback(cmd_id)

        return feedback_resp

    def arm_cylindrical_velocity_cmd_helper(self, desc='', v_r=0.0, v_theta=0.0, v_z=0.0):
        """ Helper function to build a arm velocity command from unitless cylindrical coordinates.

        params:
        + desc: string description of the desired command
        + v_r: normalized velocity in R-axis to move hand towards/away from shoulder in range [-1.0,1.0]
        + v_theta: normalized velocity in theta-axis to rotate hand clockwise/counter-clockwise around the shoulder in range [-1.0,1.0]
        + v_z: normalized velocity in Z-axis to raise/lower the hand in range [-1.0,1.0]

        """
        # Build the linear velocity command specified in a cylindrical coordinate system
        cylindrical_velocity = arm_command_pb2.ArmVelocityCommand.CylindricalVelocity()
        cylindrical_velocity.linear_velocity.r = v_r
        cylindrical_velocity.linear_velocity.theta = v_theta
        cylindrical_velocity.linear_velocity.z = v_z

        arm_velocity_command = arm_command_pb2.ArmVelocityCommand.Request(
            cylindrical_velocity=cylindrical_velocity,
            end_time=self._robot.time_sync.robot_timestamp_from_local_secs(time.time() +
                                                                           self.VELOCITY_CMD_DURATION))

        return self.arm_velocity_cmd_helper(arm_velocity_command=arm_velocity_command, desc=desc)

    def arm_angular_velocity_cmd_helper(self, desc='', v_rx=0.0, v_ry=0.0, v_rz=0.0):
        """ Helper function to build a arm velocity command from angular velocities measured with respect
            to the odom frame, expressed in the hand frame.

        params:
        + desc: string description of the desired command
        + v_rx: angular velocity about X-axis in units rad/sec
        + v_ry: angular velocity about Y-axis in units rad/sec
        + v_rz: angular velocity about Z-axis in units rad/sec

        """
        # Specify a zero linear velocity of the hand. This can either be in a cylindrical or Cartesian coordinate system.
        cylindrical_velocity = arm_command_pb2.ArmVelocityCommand.CylindricalVelocity()

        # Build the angular velocity command of the hand
        angular_velocity_of_hand_rt_odom_in_hand = geometry_pb2.Vec3(x=v_rx, y=v_ry, z=v_rz)

        arm_velocity_command = arm_command_pb2.ArmVelocityCommand.Request(
            cylindrical_velocity=cylindrical_velocity,
            angular_velocity_of_hand_rt_odom_in_hand=angular_velocity_of_hand_rt_odom_in_hand,
            end_time=self._robot.time_sync.robot_timestamp_from_local_secs(time.time() +
                                                                           self.VELOCITY_CMD_DURATION))

        return self.arm_velocity_cmd_helper(arm_velocity_command=arm_velocity_command, desc=desc)

    def arm_velocity_cmd_helper(self, arm_velocity_command, desc=''):
        # Build synchronized robot command
        robot_command = robot_command_pb2.RobotCommand()
        robot_command.synchronized_command.arm_command.arm_velocity_command.CopyFrom(
            arm_velocity_command)

        return self.start_robot_command(desc, robot_command, end_time_secs=time.time() + self.VELOCITY_CMD_DURATION)
