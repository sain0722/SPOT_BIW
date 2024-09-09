import logging
import math
import signal
import sys
import threading
import time
from sys import platform

import cv2
import numpy as np
from PIL import Image

import bosdyn.client
import bosdyn.client.util
from bosdyn import geometry
from bosdyn.api import geometry_pb2, image_pb2, trajectory_pb2, world_object_pb2
from bosdyn.api.geometry_pb2 import SE2Velocity, SE2VelocityLimit, Vec2
from bosdyn.api.spot import robot_command_pb2 as spot_command_pb2
from bosdyn.client import ResponseError, RpcError, create_standard_sdk
from bosdyn.client.frame_helpers import (BODY_FRAME_NAME, VISION_FRAME_NAME, get_a_tform_b,
                                         get_vision_tform_body)
from bosdyn.client.image import ImageClient, build_image_request
from bosdyn.client.lease import LeaseClient
from bosdyn.client.math_helpers import Quat, SE3Pose
from bosdyn.client.power import PowerClient
from bosdyn.client.robot_command import RobotCommandBuilder, RobotCommandClient, blocking_stand
from bosdyn.client.robot_id import RobotIdClient, version_tuple
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.client.world_object import WorldObjectClient

# Use this length to make sure we're commanding the head of the robot
# to a position instead of the center.
BODY_LENGTH = 1.1


class FollowFiducial(object):
    """ Detect and follow a fiducial with Spot."""

    def __init__(self, robot, distance_margin=0.5, limit_speed=True, avoid_obstacles=False):
        # Robot instance variable.
        self._robot = robot
        self._robot_id = robot.ensure_client(RobotIdClient.default_service_name).get_id(timeout=0.4)
        self._power_client = robot.ensure_client(PowerClient.default_service_name)
        self._image_client = robot.ensure_client(ImageClient.default_service_name)
        self._robot_state_client = robot.ensure_client(RobotStateClient.default_service_name)
        self._robot_command_client = robot.ensure_client(RobotCommandClient.default_service_name)
        self._world_object_client = robot.ensure_client(WorldObjectClient.default_service_name)

        # Stopping Distance (x,y) offset from the tag and angle offset from desired angle.
        self.distance_margin = distance_margin
        self._tag_offset = float(self.distance_margin) + BODY_LENGTH / 2.0  # meters

        # Maximum speeds.
        self._max_x_vel = 0.5
        self._max_y_vel = 0.5
        self._max_ang_vel = 1.0

        # Indicator if fiducial detection's should be from the world object service using
        # spot's perception system or detected with the apriltag library. If the software version
        # does not include the world object service, than default to april tag library.
        # self._use_world_object_service = (options.use_world_objects and
        #                                   self.check_if_version_has_world_objects(self._robot_id))

        # Indicators for movement and image displays.
        self._standup = True  # Stand up the robot.
        self._movement_on = True  # Let the robot walk towards the fiducial.
        self._limit_speed = limit_speed  # Limit the robot's walking speed.
        self._avoid_obstacles = avoid_obstacles  # Disable obstacle avoidance.

        # Epsilon distance between robot and desired go-to point.
        self._x_eps = .05
        self._y_eps = .05
        self._angle_eps = .075

        # Indicator for if motor power is on.
        self._powered_on = False

        # Counter for the number of iterations completed.
        self._attempts = 0

        # Maximum amount of iterations before powering off the motors.
        self._max_attempts = 100000

        # Camera intrinsics for the current camera source being analyzed.
        self._intrinsics = None

        # Transform from the robot's camera frame to the baselink frame.
        # It is a math_helpers.SE3Pose.
        self._camera_tform_body = None

        # Transform from the robot's baselink to the world frame.
        # It is a math_helpers.SE3Pose.
        self._body_tform_world = None

        # Latest detected fiducial's position in the world.
        self._current_tag_world_pose = np.array([])

        # Heading angle based on the camera source which detected the fiducial.
        self._angle_desired = None

        # Dictionary mapping camera source to it's latest image taken.
        self._image = dict()

        # List of all possible camera sources.
        self._source_names = [
            src.name for src in self._image_client.list_image_sources() if
            (src.image_type == image_pb2.ImageSource.IMAGE_TYPE_VISUAL and 'depth' not in src.name)
        ]
        print(self._source_names)

        # Dictionary mapping camera source to previously computed extrinsics.
        self._camera_to_extrinsics_guess = self.populate_source_dict()

        # Camera source which a bounding box was last detected in.
        self._previous_source = None

        # Thread
        self.started = False

    def set_parameters(self, distance_margin, limit_speed, avoid_obstacles):
        self.distance_margin = distance_margin
        self._tag_offset = float(self.distance_margin) + BODY_LENGTH / 2.0  # meters
        self.limit_speed = limit_speed
        self.avoid_obstacles = avoid_obstacles

    @property
    def robot_state(self):
        """Get latest robot state proto."""
        return self._robot_state_client.get_robot_state()

    @property
    def image(self):
        """Return the current image associated with each source name."""
        return self._image

    @property
    def image_sources_list(self):
        """Return the list of camera sources."""
        return self._source_names

    def populate_source_dict(self):
        """Fills dictionary of the most recently computed camera extrinsics with the camera source.
           The initial boolean indicates if the extrinsics guess should be used."""
        camera_to_extrinsics_guess = dict()
        for src in self._source_names:
            # Dictionary values: use_extrinsics_guess bool, (rotation vector, translation vector) tuple.
            camera_to_extrinsics_guess[src] = (False, (None, None))
        return camera_to_extrinsics_guess

    def check_if_version_has_world_objects(self, robot_id):
        """Check that software version contains world object service."""
        # World object service was released in spot-sdk version 1.2.0
        return version_tuple(robot_id.software_release.version) >= (1, 2, 0)

    def start(self):
        """Claim lease of robot and start the fiducial follower."""
        self._robot.time_sync.wait_for_sync()

        # Stand the robot up.
        if self._standup:
            # self.power_on()
            self._powered_on = self._robot.is_powered_on()
            blocking_stand(self._robot_command_client)

            # Delay grabbing image until spot is standing (or close enough to upright).
            time.sleep(.35)

            self.started = True

        # while self.started and self._attempts <= self._max_attempts:
        detected_fiducial = False
        fiducial_rt_world = None
        # Get the first fiducial object Spot detects with the world object service.
        fiducial = self.get_fiducial_objects()
        if fiducial is not None:
            vision_tform_fiducial = get_a_tform_b(
                fiducial.transforms_snapshot, VISION_FRAME_NAME,
                fiducial.apriltag_properties.frame_name_fiducial).to_proto()
            if vision_tform_fiducial is not None:
                detected_fiducial = True
                fiducial_rt_world = vision_tform_fiducial.position

        if detected_fiducial:
            # Go to the tag and stop within a certain distance
            self.go_to_tag(fiducial_rt_world)
        else:
            print('No fiducials found')

            # self._attempts += 1  #increment attempts at finding a fiducial

        # Power off at the conclusion of the example.
        # if self._powered_on:
        #     self.power_off()

    # def stop(self):
    #     self.started = False

    def get_fiducial_objects(self):
        """Get all fiducials that Spot detects with its perception system."""
        # Get all fiducial objects (an object of a specific type).
        request_fiducials = [world_object_pb2.WORLD_OBJECT_APRILTAG]
        fiducial_objects = self._world_object_client.list_world_objects(
            object_type=request_fiducials).world_objects
        fiducial_objects_list = []
        if len(fiducial_objects) > 0:
            for fid in fiducial_objects:
                if fid.apriltag_properties.tag_id >= 500:
                    continue
                fiducial_objects_list.append(fid)
            # Return the first detected fiducial.
            return fiducial_objects_list[0]

        # Return none if no fiducials are found.
        return None

    def power_on(self):
        """Power on the robot."""
        self._robot.power_on()
        self._powered_on = True
        print(f'Powered On {self._robot.is_powered_on()}')

    def power_off(self):
        """Power off the robot."""
        self._robot.power_off()
        print(f'Powered Off {not self._robot.is_powered_on()}')

    def compute_fiducial_in_world_frame(self, tvec):
        """Transform the tag position from camera coordinates to world coordinates."""
        fiducial_rt_camera_frame = np.array(
            [float(tvec[0][0]) / 1000.0,
             float(tvec[1][0]) / 1000.0,
             float(tvec[2][0]) / 1000.0])
        body_tform_fiducial = (self._camera_tform_body.inverse()).transform_point(
            fiducial_rt_camera_frame[0], fiducial_rt_camera_frame[1], fiducial_rt_camera_frame[2])
        fiducial_rt_world = self._body_tform_world.inverse().transform_point(
            body_tform_fiducial[0], body_tform_fiducial[1], body_tform_fiducial[2])
        return fiducial_rt_world

    def go_to_tag(self, fiducial_rt_world):
        """Use the position of the april tag in vision world frame and command the robot."""
        # Compute the go-to point (offset by .5m from the fiducial position) and the heading at
        # this point.
        self._current_tag_world_pose, self._angle_desired = self.offset_tag_pose(
            fiducial_rt_world, self._tag_offset)

        #Command the robot to go to the tag in kinematic odometry frame
        mobility_params = self.set_mobility_params()
        tag_cmd = RobotCommandBuilder.synchro_se2_trajectory_point_command(
            goal_x=self._current_tag_world_pose[0], goal_y=self._current_tag_world_pose[1],
            goal_heading=self._angle_desired, frame_name=VISION_FRAME_NAME, params=mobility_params,
            body_height=0.0, locomotion_hint=spot_command_pb2.HINT_AUTO)
        end_time = 5.0
        if self._movement_on and self._powered_on:
            #Issue the command to the robot
            self._robot_command_client.robot_command(lease=None, command=tag_cmd,
                                                     end_time_secs=time.time() + end_time)
            # #Feedback to check and wait until the robot is in the desired position or timeout
            start_time = time.time()
            current_time = time.time()
            while (not self.final_state() and current_time - start_time < end_time):
                time.sleep(.25)
                current_time = time.time()
        return

    def final_state(self):
        """Check if the current robot state is within range of the fiducial position."""
        robot_state = get_vision_tform_body(self.robot_state.kinematic_state.transforms_snapshot)
        robot_angle = robot_state.rot.to_yaw()
        if self._current_tag_world_pose.size != 0:
            x_dist = abs(self._current_tag_world_pose[0] - robot_state.x)
            y_dist = abs(self._current_tag_world_pose[1] - robot_state.y)
            angle = abs(self._angle_desired - robot_angle)
            if ((x_dist < self._x_eps) and (y_dist < self._y_eps) and (angle < self._angle_eps)):
                return True
        return False

    def get_desired_angle(self, xhat):
        """Compute heading based on the vector from robot to object."""
        zhat = [0.0, 0.0, 1.0]
        yhat = np.cross(zhat, xhat)
        mat = np.array([xhat, yhat, zhat]).transpose()
        return Quat.from_matrix(mat).to_yaw()

    def offset_tag_pose(self, object_rt_world, dist_margin=1.0):
        """Offset the go-to location of the fiducial and compute the desired heading."""
        robot_rt_world = get_vision_tform_body(self.robot_state.kinematic_state.transforms_snapshot)
        robot_to_object_ewrt_world = np.array(
            [object_rt_world.x - robot_rt_world.x, object_rt_world.y - robot_rt_world.y, 0])
        robot_to_object_ewrt_world_norm = robot_to_object_ewrt_world / np.linalg.norm(
            robot_to_object_ewrt_world)
        heading = self.get_desired_angle(robot_to_object_ewrt_world_norm)
        goto_rt_world = np.array([
            object_rt_world.x - robot_to_object_ewrt_world_norm[0] * dist_margin,
            object_rt_world.y - robot_to_object_ewrt_world_norm[1] * dist_margin
        ])
        return goto_rt_world, heading

    def set_mobility_params(self):
        """Set robot mobility params to disable obstacle avoidance."""
        obstacles = spot_command_pb2.ObstacleParams(disable_vision_body_obstacle_avoidance=True,
                                                    disable_vision_foot_obstacle_avoidance=True,
                                                    disable_vision_foot_constraint_avoidance=True,
                                                    obstacle_avoidance_padding=.001)
        body_control = self.set_default_body_control()
        if self._limit_speed:
            speed_limit = SE2VelocityLimit(max_vel=SE2Velocity(
                linear=Vec2(x=self._max_x_vel, y=self._max_y_vel), angular=self._max_ang_vel))
            if not self._avoid_obstacles:
                mobility_params = spot_command_pb2.MobilityParams(
                    obstacle_params=obstacles, vel_limit=speed_limit, body_control=body_control,
                    locomotion_hint=spot_command_pb2.HINT_AUTO)
            else:
                mobility_params = spot_command_pb2.MobilityParams(
                    vel_limit=speed_limit, body_control=body_control,
                    locomotion_hint=spot_command_pb2.HINT_AUTO)
        elif not self._avoid_obstacles:
            mobility_params = spot_command_pb2.MobilityParams(
                obstacle_params=obstacles, body_control=body_control,
                locomotion_hint=spot_command_pb2.HINT_AUTO)
        else:
            #When set to none, RobotCommandBuilder populates with good default values
            mobility_params = None
        return mobility_params

    @staticmethod
    def set_default_body_control():
        """Set default body control params to current body position"""
        footprint_R_body = geometry.EulerZXY()
        position = geometry_pb2.Vec3(x=0.0, y=0.0, z=0.0)
        rotation = footprint_R_body.to_quaternion()
        pose = geometry_pb2.SE3Pose(position=position, rotation=rotation)
        point = trajectory_pb2.SE3TrajectoryPoint(pose=pose)
        traj = trajectory_pb2.SE3Trajectory(points=[point])
        return spot_command_pb2.BodyControlParams(base_offset_rt_footprint=traj)

    @staticmethod
    def make_camera_matrix(ints):
        """Transform the ImageResponse proto intrinsics into a camera matrix."""
        camera_matrix = np.array([[ints.focal_length.x, ints.skew.x, ints.principal_point.x],
                                  [ints.skew.y, ints.focal_length.y, ints.principal_point.y],
                                  [0, 0, 1]])
        return camera_matrix
