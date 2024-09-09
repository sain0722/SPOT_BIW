from bosdyn.api import basic_command_pb2
from bosdyn.client.robot_command import RobotCommandBuilder
class SpotMove:
    """
    Spot 로봇의 움직임을 관리하는 클래스입니다.
    이 객체를 통해 로봇의 움직임 속도와 회전 각도를 제어할 수 있습니다.

    Attributes
    ----------
    VELOCITY_BASE_SPEED (float): 로봇의 스피드를 설정하는 속성입니다. 단위는 m/s 입니다.
    VELOCITY_BASE_ANGULAR (float): 로봇의 회전 각도를 설정하는 속성입니다. 단위는 rad/s 입니다.
    """

    def __init__(self):
        self.robot_commander = None
        self.BODY_HEIGHT = 0.0
        self.VELOCITY_BASE_SPEED = 0.5  # m/s
        self.VELOCITY_BASE_ANGULAR = 0.8  # rad/sec

    def initialize(self, robot):
        self.robot_commander = robot.robot_commander

    @property
    def velocity_base_speed(self):
        return self.VELOCITY_BASE_SPEED

    @velocity_base_speed.setter
    def velocity_base_speed(self, value):
        self.VELOCITY_BASE_SPEED = value

    @property
    def velocity_base_angular(self):
        return self.VELOCITY_BASE_ANGULAR

    @velocity_base_angular.setter
    def velocity_base_angular(self, value):
        self.VELOCITY_BASE_ANGULAR = value

    @property
    def body_height(self):
        return self.BODY_HEIGHT

    @body_height.setter
    def body_height(self, value):
        self.BODY_HEIGHT = value

    def sit(self):
        """
        로봇을 앉히는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.start_robot_command('sit', RobotCommandBuilder.synchro_sit_command())

    def stand(self):
        """
        로봇을 일으키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.start_robot_command('stand', RobotCommandBuilder.synchro_stand_command())

    def move_forward(self):
        """
        로봇을 전진시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.velocity_cmd_helper('move_forward', v_x=self.VELOCITY_BASE_SPEED, body_height=self.BODY_HEIGHT)

    def move_backward(self):
        """
        로봇을 후진시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.velocity_cmd_helper('move_backward', v_x=-self.VELOCITY_BASE_SPEED, body_height=self.BODY_HEIGHT)

    def strafe_left(self):
        """
        로봇을 왼쪽으로 이동시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.velocity_cmd_helper('strafe_left', v_y=self.VELOCITY_BASE_SPEED, body_height=self.BODY_HEIGHT)

    def strafe_right(self):
        """
        로봇을 오른쪽으로 이동시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.velocity_cmd_helper('strafe_right', v_y=-self.VELOCITY_BASE_SPEED, body_height=self.BODY_HEIGHT)

    def move_forward_left(self):
        return self.robot_commander.velocity_cmd_helper('strafe_right',
                                                        v_x=self.VELOCITY_BASE_SPEED,
                                                        v_y=-self.VELOCITY_BASE_SPEED,
                                                        v_rot=0.0)

    def turn_left(self):
        """
        로봇을 왼쪽으로 회전시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.velocity_cmd_helper('turn_left', v_rot=self.VELOCITY_BASE_ANGULAR, body_height=self.BODY_HEIGHT)

    def turn_right(self):
        """
        로봇을 오른쪽으로 회전시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.velocity_cmd_helper('turn_right', v_rot=-self.VELOCITY_BASE_ANGULAR, body_height=self.BODY_HEIGHT)

    def selfright(self):
        """
        로봇을 selfright 시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        return self.robot_commander.start_robot_command('selfright', RobotCommandBuilder.selfright_command())

    def battery_change_pose(self):
        """
        로봇의 배터리 교체 자세로 이동시키는 메소드입니다.

        Returns:
            bosdyn.client.robot_command.CommandResponse: RobotCommand 수행 결과
        """
        cmd = RobotCommandBuilder.battery_change_pose_command(
            dir_hint=basic_command_pb2.BatteryChangePoseCommand.Request.HINT_RIGHT)
        return self.robot_commander.start_robot_command('battery_change_pose', cmd)
