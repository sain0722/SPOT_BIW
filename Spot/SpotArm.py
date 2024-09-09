import copy
import time

from bosdyn.api import trajectory_pb2, arm_command_pb2, synchronized_command_pb2, robot_command_pb2, geometry_pb2
from bosdyn.client import math_helpers, frame_helpers
from bosdyn.client.frame_helpers import GRAV_ALIGNED_BODY_FRAME_NAME, ODOM_FRAME_NAME, BODY_FRAME_NAME
from bosdyn.client.robot_command import RobotCommandBuilder, block_until_arm_arrives
from bosdyn.util import seconds_to_duration

class SpotArm:
    """
    Spot 로봇의 팔을 제어하는 클래스입니다.
    """
    def __init__(self):
        """
        SpotArm 클래스의 인스턴스를 초기화합니다.
        """
        # current joint state
        # sh0, sh1, el0, el1, wr0, wr1
        self.robot = None
        self.robot_command_executor = None

        self.joint_params = None
        self.JOINT_MOVE_RATE = 0.1  # arm joint move rate
        self.JOINT_TIME_SEC  = 1.0  # arm control speed
        self.VELOCITY_HAND_NORMALIZED = 0.2  # normalized hand velocity [0, 1]
        self.VELOCITY_ANGULAR_HAND = 0.2  # rad/sec

    def initialize(self, robot):
        """
        Parameters:
            robot (Robot): Robot 객체입니다.
        """
        self.robot = robot
        self.robot_command_executor = robot.robot_commander

    @property
    def joint_move_rate(self):
        """
        팔의 관절 이동 속도를 반환합니다.
        """
        return self.JOINT_MOVE_RATE

    @joint_move_rate.setter
    def joint_move_rate(self, value):
        """
        팔의 관절 이동 속도를 설정합니다.

        Parameters:
            value (float): 이동 속도 값입니다.
        """
        self.JOINT_MOVE_RATE = value

    @property
    def joint_time_sec(self):
        """
        팔의 관절 이동 시간을 반환합니다.
        """
        return self.JOINT_TIME_SEC

    @joint_time_sec.setter
    def joint_time_sec(self, value):
        """
        팔의 관절 이동 시간을 설정합니다.

        Parameters:
            value (float): 이동 시간 값입니다.
        """
        self.JOINT_TIME_SEC = value

    def stow(self):
        """
        팔을 접힌 상태로 변환하는 커맨드를 실행합니다.
        """
        stow_command    = RobotCommandBuilder.arm_stow_command()
        gripper_command = RobotCommandBuilder.claw_gripper_close_command()
        synchro_command = RobotCommandBuilder.build_synchro_command(gripper_command, stow_command)

        return self.robot_command_executor.start_robot_command('stow', synchro_command,
                                                               end_time_secs=10.0)

    def unstow(self):
        """
        팔을 펼친 상태로 변환하는 커맨드를 실행합니다.
        """
        ready_command   = RobotCommandBuilder.arm_ready_command()
        gripper_command = RobotCommandBuilder.claw_gripper_open_command()
        synchro_command = RobotCommandBuilder.build_synchro_command(gripper_command, ready_command)

        return self.robot_command_executor.start_robot_command('unstow', synchro_command,
                                                               end_time_secs=10.0)

    def gripper_open(self):
        """
        그리퍼를 열기 위한 커맨드를 실행합니다.
        """
        return self.robot_command_executor.start_robot_command('gripper_open',
                                                               RobotCommandBuilder.claw_gripper_open_command(),
                                                               end_time_secs=6.0)

    def gripper_close(self):
        """
        그리퍼를 닫기 위한 커맨드를 실행합니다.
        """
        return self.robot_command_executor.start_robot_command('gripper_close',
                                                               RobotCommandBuilder.claw_gripper_close_command(),
                                                               end_time_secs=6.0)

    def gripper_check(self):
        """
        그리퍼 상태를 확인합니다.
        """
        gripper_open_percentage = self.robot.robot_state.manipulator_state.gripper_open_percentage

    def is_gripper_open(self):
        """
        그리퍼가 열려있는지 여부를 반환합니다.
        """
        if self.robot.robot_state.manipulator_state.gripper_open_percentage >= 10:
            return True
        else:
            return False

    def joint_move(self, target):
        """
        지정된 관절을 이동시키는 커맨드를 실행합니다.

        Parameters:
            target (str): 이동할 관절의 목표 위치를 나타내는 문자열입니다.

        Returns:
            RobotCommand: 커맨드 실행 결과를 나타내는 RobotCommand 객체입니다.
        """
        self.joint_params = self.robot.get_current_joint_state()
        if target == "sh0_right":
            self.joint_params['sh0'] = self.joint_params['sh0'] - self.JOINT_MOVE_RATE

        elif target == "sh0_left":
            self.joint_params['sh0'] = self.joint_params['sh0'] + self.JOINT_MOVE_RATE

        elif target == "sh1_up":
            self.joint_params['sh1'] = self.joint_params['sh1'] - self.JOINT_MOVE_RATE

        elif target == "sh1_down":
            self.joint_params['sh1'] = self.joint_params['sh1'] + self.JOINT_MOVE_RATE

        elif target == "el0_up":
            self.joint_params['el0'] = self.joint_params['el0'] - self.JOINT_MOVE_RATE

        elif target == "el0_down":
            self.joint_params['el0'] = self.joint_params['el0'] + self.JOINT_MOVE_RATE

        elif target == "el1_right":
            self.joint_params['el1'] = self.joint_params['el1'] + self.JOINT_MOVE_RATE

        elif target == "el1_left":
            self.joint_params['el1'] = self.joint_params['el1'] - self.JOINT_MOVE_RATE

        elif target == "wr0_up":
            self.joint_params['wr0'] = self.joint_params['wr0'] - self.JOINT_MOVE_RATE

        elif target == "wr0_down":
            self.joint_params['wr0'] = self.joint_params['wr0'] + self.JOINT_MOVE_RATE

        elif target == "wr1_right":
            self.joint_params['wr1'] = self.joint_params['wr1'] - self.JOINT_MOVE_RATE

        elif target == "wr1_left":
            self.joint_params['wr1'] = self.joint_params['wr1'] + self.JOINT_MOVE_RATE

        return self.robot_command_executor.joint_move_cmd_helper(desc=target,
                                                                 params=self.joint_params.values(),
                                                                 time_secs=self.JOINT_TIME_SEC)

    def joint_move_manual(self, params):
        """
        지정된 관절 파라미터를 사용하여 관절을 이동시키는 커맨드를 실행합니다.

        Parameters:
            params (list): 관절 파라미터의 목록입니다.

        Returns:
            RobotCommand: 커맨드 실행 결과를 나타내는 RobotCommand 객체입니다.
        """
        return self.robot_command_executor.joint_move_cmd_helper(desc="joint_move_manual",
                                                                 params=params,
                                                                 time_secs=self.JOINT_TIME_SEC)

    def trajectory(self, position, rotation, frame_name=BODY_FRAME_NAME, end_time=2.0):
        """
        주어진 위치와 회전값에 따라 팔을 이동시키는 커맨드를 실행합니다.

        Parameters:
            position (dict): 팔의 이동할 위치를 나타내는 딕셔너리입니다.
            rotation (dict): 팔의 이동할 회전값을 나타내는 딕셔너리입니다.
            frame_name (str): 프레임 이름입니다.
            end_time (float): 이동 완료 시간(초)입니다.

        Returns:
            int: 커맨드 ID입니다.
        """
        # Use the same rotation as the robot's body.
        rotation = math_helpers.Quat(w=rotation['w'], x=rotation['x'], y=rotation['y'], z=rotation['z'])

        # Build the points in the trajectory.
        hand_pose = math_helpers.SE3Pose(x=position['x'], y=position['y'], z=position['z'], rot=rotation)

        traj_point = trajectory_pb2.SE3TrajectoryPoint(
            pose=hand_pose.to_proto(), time_since_reference=seconds_to_duration(end_time))

        # Build the trajectory proto by combining the points.
        hand_traj = trajectory_pb2.SE3Trajectory(points=[traj_point])

        arm_cartesian_command = arm_command_pb2.ArmCartesianCommand.Request(
            pose_trajectory_in_task=hand_traj, root_frame_name=frame_name)

        # Pack everything up in protos.
        arm_command = arm_command_pb2.ArmCommand.Request(
            arm_cartesian_command=arm_cartesian_command)

        synchronized_command = synchronized_command_pb2.SynchronizedCommand.Request(
            arm_command=arm_command)

        robot_command = robot_command_pb2.RobotCommand(synchronized_command=synchronized_command)

        # Keep the gripper opened the whole time.
        robot_command = RobotCommandBuilder.claw_gripper_open_fraction_command(
            1.0, build_on_command=robot_command)

        # Send the trajectory to the robot.
        cmd_id = self.robot_command_executor.start_robot_command('trajectory', robot_command,
                                                                 end_time_secs=end_time)

        self.robot_command_executor.wait_until_arm_arrives(cmd_id, end_time)
        return cmd_id

    def move_out(self):
        return self.robot_command_executor.arm_cylindrical_velocity_cmd_helper('move_out', v_r=self.VELOCITY_HAND_NORMALIZED)

    def move_in(self):
        return self.robot_command_executor.arm_cylindrical_velocity_cmd_helper('move_in', v_r=-self.VELOCITY_HAND_NORMALIZED)

    def rotate_ccw(self):
        return self.robot_command_executor.arm_cylindrical_velocity_cmd_helper('rotate_ccw', v_theta=self.VELOCITY_HAND_NORMALIZED)

    def rotate_cw(self):
        return self.robot_command_executor.arm_cylindrical_velocity_cmd_helper('rotate_cw', v_theta=-self.VELOCITY_HAND_NORMALIZED)

    def move_up(self):
        return self.robot_command_executor.arm_cylindrical_velocity_cmd_helper('move_up', v_z=self.VELOCITY_HAND_NORMALIZED)

    def move_down(self):
        return self.robot_command_executor.arm_cylindrical_velocity_cmd_helper('move_down', v_z=-self.VELOCITY_HAND_NORMALIZED)

    def rotate_plus_rx(self):
        return self.robot_command_executor.arm_angular_velocity_cmd_helper('rotate_plus_rx', v_rx=self.VELOCITY_ANGULAR_HAND)

    def rotate_minus_rx(self):
        return self.robot_command_executor.arm_angular_velocity_cmd_helper('rotate_minus_rx', v_rx=-self.VELOCITY_ANGULAR_HAND)

    def rotate_plus_ry(self):
        return self.robot_command_executor.arm_angular_velocity_cmd_helper('rotate_plus_ry', v_ry=self.VELOCITY_ANGULAR_HAND)

    def rotate_minus_ry(self):
        return self.robot_command_executor.arm_angular_velocity_cmd_helper('rotate_minus_ry', v_ry=-self.VELOCITY_ANGULAR_HAND)

    def rotate_plus_rz(self):
        return self.robot_command_executor.arm_angular_velocity_cmd_helper('rotate_plus_rz', v_rz=self.VELOCITY_ANGULAR_HAND)

    def rotate_minus_rz(self):
        return self.robot_command_executor.arm_angular_velocity_cmd_helper('rotate_minus_rz', v_rz=-self.VELOCITY_ANGULAR_HAND)
