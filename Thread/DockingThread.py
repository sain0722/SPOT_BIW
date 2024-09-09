import time

from PySide6.QtCore import QThread, Signal
from bosdyn.api.docking import docking_pb2
from bosdyn.client import ResponseError, LeaseUseError
from bosdyn.client.common import maybe_raise, common_lease_errors
from bosdyn.client.docking import DockingClient, blocking_go_to_prep_pose
from bosdyn.client.lease import NoSuchLease
from bosdyn.client.robot_command import CommandFailedError
from bosdyn.util import now_sec, seconds_to_timestamp


class DockingThread(QThread):
    # 도킹 및 언도킹 결과를 나타내는 신호
    operation_result = Signal(bool, str)

    def __init__(self, robot, dock_id, is_docking=True):
        super().__init__()
        self.arm_manager = robot.robot_arm_manager
        self.robot = robot.robot
        self.dock_id = dock_id
        self.is_docking = is_docking

    def run(self):
        try:
            if self.is_docking:
                # 도킹 작업 수행
                function = self.blocking_dock_robot
                if self.arm_manager.is_gripper_open():
                    self.arm_manager.gripper_close()
            else:
                # 언도킹 작업 수행
                function = self.blocking_undock_robot
            function()
            message = f"{function.__name__} Complete."
            self.operation_result.emit(True, message)  # 성공 신호 전송
        except ResponseError as e:
            message = e.error_message
            self.operation_result.emit(False, message)  # 실패 신호 전송
        except CommandFailedError as e:
            print(e)  # 에러 출력
            message = e.__str__()
            self.operation_result.emit(False, message)  # 실패 신호 전송
        except Exception as e:
            message = e.__str__()
            self.operation_result.emit(False, message)  # 실패 신호 전송

    def blocking_dock_robot(self, num_retries=4, timeout=30):
        """Blocking helper that takes control of the robot and docks it.

        Args:
            num_retries: Optional, number of attempts.
            timeout: docking timeout seconds

        Returns:
            The number of retries required

        Raises:
            CommandFailedError: The robot was unable to be docked. See error for details.
        """
        docking_client = self.robot.ensure_client(DockingClient.default_service_name)

        attempt_number = 0
        docking_success = False

        # Try to dock the robot
        while attempt_number < num_retries and not docking_success:
            attempt_number += 1
            converter = self.robot.time_sync.get_robot_time_converter()
            start_time = converter.robot_seconds_from_local_seconds(now_sec())
            cmd_end_time = start_time + timeout
            cmd_timeout = cmd_end_time + 10  # client side buffer

            prep_pose = (docking_pb2.PREP_POSE_USE_POSE if
                         (attempt_number % 2) else docking_pb2.PREP_POSE_SKIP_POSE)

            try:
                cmd_id = docking_client.docking_command(self.dock_id, self.robot.time_sync.endpoint.clock_identifier,
                                                        seconds_to_timestamp(cmd_end_time), prep_pose)
            except ResponseError as exc:
                raise CommandFailedError(exc.error_message)

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
            blocking_go_to_prep_pose(self.robot, self.dock_id)
        except CommandFailedError:
            return CommandFailedError("Docking Failed.")

        # Raise error on original failure to dock
        return CommandFailedError("Docking Failed, too many attempts")

    def blocking_undock_robot(self, timeout=20):
        """Blocking helper that undocks the robot from the currently docked dock.

        Args:
            timeout: undocking timeout seconds

        Returns:
            None

        Raises:
            CommandFailedError: The robot was unable to undock. See error for details.
        """
        docking_client = self.robot.ensure_client(DockingClient.default_service_name)

        converter = self.robot.time_sync.get_robot_time_converter()
        start_time = converter.robot_seconds_from_local_seconds(now_sec())
        cmd_end_time = start_time + timeout
        cmd_timeout = cmd_end_time + 10  # client side buffer
        try:
            cmd_id = docking_client.docking_command(0, self.robot.time_sync.endpoint.clock_identifier,
                                                    seconds_to_timestamp(cmd_end_time),
                                                    docking_pb2.PREP_POSE_UNDOCK)
        except ResponseError as exc:
            raise exc

        except NoSuchLease as exc:
            raise exc

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
