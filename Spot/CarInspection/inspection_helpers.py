# Copyright (c) 2023 Boston Dynamics, Inc.  All rights reserved.
#
# Downloading, reproducing, distributing or otherwise using the SDK Software
# is subject to the terms and conditions of the Boston Dynamics Software
# Development Kit License (20191101-BDSDK-SL).
''' Class to enable autonomous inspection with the gripper camera
'''
import csv
import os
import ssl
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import bosdyn.api.data_buffer_pb2 as data_buffer_protos
import bosdyn.client
import bosdyn.mission.client
import pandas as pd
from bosdyn.api import (data_acquisition_pb2, geometry_pb2,
                        gripper_camera_param_pb2, robot_state_pb2)
from bosdyn.api.autowalk import autowalk_pb2
from bosdyn.api.autowalk.walks_pb2 import (Action, ActionWrapper,
                                           BatteryMonitor, Element,
                                           FailureBehavior, Target, Walk)
from bosdyn.api.graph_nav import graph_nav_pb2, map_pb2, nav_pb2
from bosdyn.api.mission import mission_pb2, util_pb2
from bosdyn.api.robot_state_pb2 import ManipulatorState
from bosdyn.client.autowalk import AutowalkClient
from bosdyn.client.data_acquisition import DataAcquisitionClient
from bosdyn.client.data_acquisition_helpers import (
    acquire_and_process_request, make_time_query_params)
from bosdyn.client.data_buffer import DataBufferClient
from bosdyn.client.docking import DockingClient, blocking_undock, docking_pb2
from bosdyn.client.exceptions import ResponseError
from bosdyn.client.graph_nav import GraphNavClient
from bosdyn.client.power import PowerClient, power_on_motors
from bosdyn.client.robot_command import RobotCommandBuilder, RobotCommandClient
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.util import secs_to_hms
from google.protobuf import duration_pb2

ACTION_NAME = "Arm Pointing"
ANSWER_TRYAGAIN = "Try again"
ANSWER_SKIP = "Skip"
ANSWER_DOCK = "Return to dock and terminate mission"
# Answers questions raised during mission execution on the robot - set to ANSWER_SKIP
MISSION_QUESTION_ANSWER_CHOICE = ANSWER_SKIP


class ArmSensorInspector:
    def __init__(self, robot):
        '''
            - Args:
                - robot(BD SDK Robot): a robot object
                - upload_filepath(string): a filepath to an Autowalk .walk folder that contains
                                     edge_snapshots, waypoint_snapshots, missions,
                                      autowalk_metadata, and graph
        '''
        self._robot = robot.robot
        # Check if robot has an arm
        # assert self._robot.has_arm(
        # ), "ArmSensorInspector requires robot to have an arm!"
        # Filepath for edge_snapshots, waypoint_snapshots, missions, autowalk_metadata, and graph.
        self._walk_folder_path = ""
        self._walk_file_path = ""
        # # Force trigger timesync.
        # self._robot.time_sync.wait_for_sync()
        # # Create a power client for the robot.
        # self._power_client = self._robot.ensure_client(
        #     PowerClient.default_service_name)
        # # Create the client for the Graph Nav main service.
        # self._graph_nav_client = self._robot.ensure_client(
        #     GraphNavClient.default_service_name)
        # # Create the client for Autowalk Service
        # self._autowalk_service_client = self._robot.ensure_client(
        #     AutowalkClient.default_service_name)
        # # Create the client for Mission Service
        # self._mission_client = self._robot.ensure_client(
        #     bosdyn.mission.client.MissionClient.default_service_name)
        # # Create the client for lease
        # self._lease_client = self._robot.ensure_client(
        #     bosdyn.client.lease.LeaseClient.default_service_name)
        # # Create the robot command client
        # self._robot_command_client = self._robot.ensure_client(
        #     RobotCommandClient.default_service_name)
        # # Create the robot state client
        # self._robot_state_client = self._robot.ensure_client(
        #     RobotStateClient.default_service_name)
        # # Create a docking client
        # self._docking_client = self._robot.ensure_client(
        #     DockingClient.default_service_name)
        # # Create a data_acquisition client
        # self._data_acquisition_client = self._robot.ensure_client(
        #     DataAcquisitionClient.default_service_name)
        # Stores the base mission from autowalk recording
        self._base_mission = None
        self._base_inspection_elements = None
        self._base_inspection_ids = None

        # Maps inspection_ids  to node_ids to provide element-wise feedback for missions
        self._node_map = {}
        # Store the most recent knowledge of the state of the self._robot based on rpc calls.
        self._current_graph = None
        self._current_waypoint_snapshots = dict(
        )  # maps id to waypoint snapshot
        self._current_edge_snapshots = dict()  # maps id to edge snapshot
        # Stores the localization state for the robot
        self._inital_guess_localization = None
        # String to differentiate the captured images
        self._image_suffix = ''
        # Number of inspection points completed
        self._num_of_inspection_elements = None

        # Number of inspection points completed -  this is computed by counting number of images
        self._inspection_elements_completed = 0
        # Number of failed inspections due to arm pointing failure
        self._arm_pointing_failure_count = 0

        self._mission_status = None

        # Stores the localization state for the robot
        self._initial_guess_localization = None

        # The variable that determines when to send a mission play request
        self._play_request_time = time.time()
        # The data header for inspection data saved in csv
        self._inspection_data_header = [
            'Cycle #', 'Inspection Start Time', 'Inspection End Time',
            'Cycle Time in min', '# of required inspections',
            '# of completed inspections', '# of failed inspections',
            '# of arm pointing failures', 'Time Spent Docked',
            'Battery Level at the start of the cycle',
            'Battery Level at the end of the cycle', 'Battery Consumption',
            'Battery Min Temperature at the start of the cycle',
            'Battery Max Temperature at the start of the cycle',
            'Battery Min Temperature at the end of the cycle',
            'Battery Max Temperature at the end of the cycle',
            'Mission Succeeded?'
        ]
        # Initialize the inspection data which is saved to csv during periodic inspection
        self._inspection_data = [
            0 for i in range(len(self._inspection_data_header))
        ]
        # Initialize 'Mission Succeeded?' in self._inspection_data to False
        self._inspection_data[self._inspection_data_header.index(
            "Mission Succeeded?")] = False
        # The header for summarizing a periodic inspection
        self._summary_header = [
            "Periodic mission start datetime", "Periodic mission end datetime",
            "Periodic mission duration(hours)", "Cycles Required",
            "Cycles Completed", "Cycles Failed", "Inspections Required",
            "Inspections Completed", "Inspection Failures",
            "Arm Pointing Failures", "Average Cycle Time(minutes)",
            "Median Cycle Time(minutes)", "STDEV Cycle Time(minutes)",
            "Q1 Cycle Time(minutes)", "Q3 Cycle Time(minutes)",
            "Min cycle time", "Max cycle time", "Average Battery",
            "Median Battery", "STDEV Battery", "Q1 Battery", "Q3 Battery",
            "Min Battery", "Max Battery"
        ]

        self.inspection_arm_poses = []

    def set_upload_filepath(self, filepath):
        self._walk_folder_path = filepath
        try:
            mission_path = os.path.join(filepath, "missions")
            for file in os.listdir(mission_path):
                fname = os.path.join(filepath, "missions", file)
                _, ext = os.path.splitext(fname)
                if ext == ".walk":
                    self._walk_file_path = fname
            return True

        except FileNotFoundError:
            return False

    def init_inspection(self):
        # Force trigger timesync.
        self._robot.time_sync.wait_for_sync()
        # Create a power client for the robot.
        self._power_client = self._robot.ensure_client(
            PowerClient.default_service_name)
        # Create the client for the Graph Nav main service.
        self._graph_nav_client = self._robot.ensure_client(
            GraphNavClient.default_service_name)
        # Create the client for Autowalk Service
        self._autowalk_service_client = self._robot.ensure_client(
            AutowalkClient.default_service_name)
        # Create the client for Mission Service
        self._mission_client = self._robot.ensure_client(
            bosdyn.mission.client.MissionClient.default_service_name)
        # Create the client for lease
        self._lease_client = self._robot.ensure_client(
            bosdyn.client.lease.LeaseClient.default_service_name)
        # Create the robot command client
        self._robot_command_client = self._robot.ensure_client(
            RobotCommandClient.default_service_name)
        # Create the robot state client
        self._robot_state_client = self._robot.ensure_client(
            RobotStateClient.default_service_name)
        # Create a docking client
        self._docking_client = self._robot.ensure_client(
            DockingClient.default_service_name)
        # Create a data_acquisition client
        self._data_acquisition_client = self._robot.ensure_client(
            DataAcquisitionClient.default_service_name)
        # Create a data_buffer client
        self._data_buffer_client = self._robot.ensure_client(
            DataBufferClient.default_service_name)

        # Set base mission as the autogenerated from autowalk recording
        self._load_mission(self._walk_file_path)
        # Dict of inspection_elements and a list inspection_ids
        self._base_inspection_elements, self._base_inspection_ids = self._get_base_inspections()

        # Upload the graph and snapshots to the robot.
        assert self._run_with_fallback(
            self._upload_map_and_localize
        ), "ArmSensorInspector requires robot to be localized to the uploaded map!"

        self._num_of_inspection_elements = self._get_num_of_inspection_elements(self._base_mission)

        # The mission statte variable
        self._mission_status = self._mission_client.get_state().status

    def get_mission_list(self):
        return self._base_inspection_ids

    def get_inspection_arm_poses(self):
        return self.inspection_arm_poses

    def full_inspection(self,
                        dock_at_the_end=True,
                        stow_in_between=False,
                        output_dir=None):
        ''' A function that commands the robot to run the full mission and downloads captured images.
            - Args:
                - dock_at_the_end(boolean) : tells robot to dock at the end of inspection
                - stow_in_between(boolean) :  tells robot to stow arm in between inspection actions
                - output_dir(string): the filepath of the desired output directory to store inspection images
            - Returns:
                - success(boolean): boolean indicating if inspection is successful
                - inspection_time(seconds): the time it took to complete the inspection in seconds
        '''
        self._logger_info('ArmSensorInspector: Running full_inspection')
        # Set output_dir to default if output_dir is not provided
        if output_dir is None:
            timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")
            output_dir = os.getcwd(
            ) + '/full_inspections/'
        # Set the mission as the self._base_mission
        mission = self._base_mission.__deepcopy__()
        # Check if mission is valid
        if not self._base_mission:
            self._logger_error('ArmSensorInspector: Invalid Mission!')
            return
        # Set mission params
        self._set_mission_params(mission,
                                 mission_name=self._base_mission.map_name +
                                 '_Full_Inspection',
                                 dock_at_the_end=dock_at_the_end,
                                 stow_in_between=stow_in_between)
        # Set resolution to '4208x3120
        self._set_gripper_camera_parameters(mission, resolution='4208x3120')
        # Initialize the number of inspection points completed
        self._inspection_elements_completed = 0
        # Execute mission on robot
        start_time = time.time()
        success = self._execute_mission_on_robot(mission,
                                                 output_dir=output_dir)
        end_time = time.time()
        inspection_time = end_time - start_time
        self._logger_info((
            'ArmSensorInspector: full_inspection took {} mins and captured {} images!'
        ).format((inspection_time) / 60, self._inspection_elements_completed))
        # Log status
        self._log_command_status(command_name="full_inspection",
                                 status=success)
        return success, inspection_time

    def single_inspection(
        self,
        inspection_id,
        dock_at_the_end=False,
        stow_in_between=True,
        output_dir=None,
        output_filename=None,
    ):
        ''' A function that commands the robot to capture data at a single inspection point,
            and monitors feedback. It also downloads the captured image.
            - Args:
                - inspection_id(string): an inspection point ID
                - output_dir(string): the filepath of the desired output directory to store the inspection image
                - output_filename(string): the desired name of the file name for the captured image
                - dock_at_the_end(boolean) : tells robot to dock at the end of inspection
                - stow_in_between(boolean) :  tells robot to stow arm in between inspection actions
            - Returns:
                - success(boolean): boolean indicating if inspection is successful
                - inspection_time(seconds): the time it took to complete the inspection in seconds
        '''
        # Cleared for single_inspection
        # self._logger_info('ArmSensorInspector: Running single_inspection')
        # Set output_dir to default if output_dir is not provided
        if output_dir is None:
            timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")
            output_dir = os.getcwd(
            ) + '/single_inspection/single_inspection' + timestamp
        # Curate a mission based on inspection_ids
        curated_mission = self._construct_mission_given_inspection_ids(
            [inspection_id])
        # Set mission params
        self._set_mission_params(curated_mission,
                                 mission_name=self._base_mission.map_name +
                                 '_Single_Inspection',
                                 dock_at_the_end=dock_at_the_end,
                                 stow_in_between=stow_in_between)
        # Set resolution to '4208x3120'
        self._set_gripper_camera_parameters(mission=curated_mission,
                                            resolution='4208x3120')
        # Initialize the number of inspection points completed
        self._inspection_elements_completed = 0
        # Execute mission on robot
        start_time = time.time()
        success = self._execute_mission_on_robot(
            curated_mission,
            output_dir=output_dir,
            output_filename=output_filename)
        end_time = time.time()
        inspection_time = end_time - start_time
        # Log status
        self._log_command_status(command_name="single_inspection",
                                 status=success)
        # self._logger_info((
        #     'ArmSensorInspector: single_inspection took {} mins and captured {} images!'
        # ).format((inspection_time) / 60, self._inspection_elements_completed))
        return success, inspection_time

    def partial_inspection(self,
                           inspection_ids,
                           dock_at_the_end=True,
                           stow_in_between=False,
                           output_dir=None):
        ''' A function that commands the robot to capture data at one or many inspection points,
            and monitors feedback. It also downloads captured images. This function, if inspection_ids
            are not unique, generates a unique list.
            - Args:
                - inspection_ids(list): a list of unique inspection point IDs
                - dock_at_the_end(boolean) : tells robot to dock at the end of inspection
                - stow_in_between(boolean) :  tells robot to stow arm in between inspection actions
                - output_dir(string): the filepath of the desired output directory to store inspection images
            - Returns:
                - success(boolean): boolean indicating if inspection is successful
                - inspection_time(seconds): the time it took to complete the inspection in seconds
        '''
        # Check that inspection_ids is a unique list
        if not (len(set(inspection_ids)) == len(inspection_ids)):
            self._logger_error(
                'ArmSensorInspector: Invalid inspection_ids! Try a list of unique inspection_ids!'
            )
            return
        # Cleared for partial_inspection
        self._logger_info('ArmSensorInspector: Running partial_inspection')
        # Set output_dir to default if output_dir is not provided
        if output_dir is None:
            timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")
            output_dir = os.getcwd(
            ) + '/partial_inspections/partial_inspection_' + timestamp
        # Curate a mission based on inspection_ids
        curated_mission = self._construct_mission_given_inspection_ids(
            inspection_ids)
        # Check if curated mission is valid
        if not curated_mission:
            self._logger_error('ArmSensorInspector: Invalid Mission!')
            return
        # Set mission params
        self._set_mission_params(curated_mission,
                                 mission_name=self._base_mission.map_name +
                                 '_Partial_Inspection',
                                 dock_at_the_end=dock_at_the_end,
                                 stow_in_between=stow_in_between)
        # Set resolution to '4208x3120'
        self._set_gripper_camera_parameters(mission=curated_mission,
                                            resolution='4208x3120')
        # Initialize the number of inspection points completed
        self._inspection_elements_completed = 0
        # Execute mission on robot
        start_time = time.time()
        success = self._execute_mission_on_robot(curated_mission,
                                                 output_dir=output_dir)
        end_time = time.time()
        inspection_time = end_time - start_time
        # Log status
        self._log_command_status(command_name="partial_inspection",
                                 status=success)
        self._logger_info((
            'ArmSensorInspector: partial_inspection took {} mins and captured {} images!'
        ).format((inspection_time) / 60, self._inspection_elements_completed))
        return success, inspection_time

    def periodic_inspection(self,
                            inspection_interval,
                            number_of_cycles,
                            output_dir=None,
                            using_single_inspection=True):
        ''' A function that commands the robot to perform full_inspection() every given inspection minute
            for given number of cycles. Robot spends (inspection_interval - robot inspection cycle time) minutes
            on the dock charging before proceeding to the next cycle.
            - Args:
                - inspection_interval(double): the periodicity of the inspection in minutes
                - number_of_cycles(int) : the frequency of the inspection in number of cycles
                - output_dir(string): the filepath of the desired output directory to store inspection images
            - Returns:
                - Boolean indicating if periodic_inspection operation is successful
                - inspection_time(seconds): the time it took to complete the inspection in seconds
        '''
        self._logger_info('ArmSensorInspector: Running periodic_inspection')
        # Return False if inputs are not instances of int
        if not isinstance(inspection_interval, float):
            self._logger_error((
                'ArmSensorInspector:  The provided inspection_interval {} is not a float!'
            ).format(inspection_interval))
            return False, 0
        if not isinstance(number_of_cycles, int):
            self._logger_error((
                'ArmSensorInspector:  The provided number_of_cycles {} is not an integer!'
            ).format(number_of_cycles))
            return False, 0
        # Check if inspection_interval and number_of_cycles are valid
        if inspection_interval <= 0 or number_of_cycles <= 0:
            self._logger_error(
                'ArmSensorInspector: Invalid inputs for inspection_interval and/or number_of_cycles. Try numbers > 0!'
            )
            return False, 0
        # Set output_dir to default if output_dir is not provided
        if output_dir is None:
            timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")
            output_dir = os.getcwd(
            ) + '/periodic_inspections/'


        # Set the filepath for the csv
        csv_filepath = Path(output_dir + '.csv')
        # csv_filepath = Path(output_dir + '/inspection_data_' + timestamp +
        #                     '.csv')


        # Write the HEADER to the csv
        self._write_inspection_data(csv_filepath, self._inspection_data_header)
        # Set periodic_mission_start_datetime
        periodic_mission_start_datetime = datetime.now()
        # Initialize cycle number
        cycle = 1
        # Run full_inspection for given number_of_cycles
        while cycle <= number_of_cycles:
            # Initialize time
            start_time = datetime.now()
            inspection_cycle_time = timedelta(minutes=inspection_interval,
                                              seconds=0)
            inspection_cycle_endtime = start_time + inspection_cycle_time
            while datetime.now() < inspection_cycle_endtime:
                # Set the cycle_output_dir as the cycle num to create a separate dir for the images taken in a cycle
                # cycle_output_dir = output_dir + "/cycle_" + str(
                #     cycle) + "_" + datetime.now().strftime("%m%d%Y_%H%M%S")
                cycle_output_dir = output_dir

                self._logger_info(
                    "ArmSensorInspector: Performing inspection cycle#: " +
                    str(cycle))
                # Check the status of the battery before the inspection begins
                start_battery, start_min_temp, start_max_temp = self._run_with_fallback(
                    self._battery_status)
                # Note the start of the inspection cycle
                start_t = datetime.now()
                if using_single_inspection:
                    # Send a single inspection request for each id in _base_inspection_ids
                    for id in self._base_inspection_ids:
                        # Deploy arm and perform inspection
                        self.single_inspection(inspection_id=id,
                                               dock_at_the_end=False,
                                               stow_in_between=False,
                                               output_dir=cycle_output_dir)
                    # Dock the robot after inspecting all ids
                    cycle_success = self.go_to_dock()
                else:
                    # Use full inspection
                    cycle_success, _ = self.full_inspection(
                        output_dir=cycle_output_dir)
                # Note the end of the inspection cycle
                end_t = datetime.now()
                cycle_time_secs = (end_t - start_t).total_seconds()
                # Check the status of the battery after the inspection is done
                end_battery, end_min_temp, end_max_temp = self._run_with_fallback(
                    self._battery_status)
                cycle_time = cycle_time_secs / 60  # mins
                self._logger_info("ArmSensorInspector: Completed cycle#: " +
                                  str(cycle) + " in (mins): " +
                                  str(cycle_time))

                # Calculate the time to spend on the dock before proceeding to the next inspection_cycle
                wait_time = (inspection_cycle_endtime -
                             datetime.now()).total_seconds()  #seconds
                wait_timeout = time.time() + wait_time
                # Wait and charge on the dock
                self._logger_info(
                    "ArmSensorInspector: Waiting on the dock for " +
                    str(wait_time / 60) + " mins...")
                # Log inspection data
                battery_drop = end_battery - start_battery
                # Log failed inspection
                failed_inspections = self._num_of_inspection_elements - self._inspection_elements_completed
                # Update self._inspection_data
                self._inspection_data = [
                    cycle,
                    start_t,
                    end_t,
                    cycle_time,
                    self._num_of_inspection_elements,
                    self._inspection_elements_completed,
                    failed_inspections,
                    self._arm_pointing_failure_count,
                    wait_time / 60,
                    start_battery,
                    end_battery,
                    battery_drop,
                    start_min_temp,
                    start_max_temp,
                    end_min_temp,
                    end_max_temp,
                    cycle_success,
                ]
                # Write the inspection self._inspection_data to the csv
                self._write_inspection_data(csv_filepath,
                                            self._inspection_data)
                while time.time() < wait_timeout:
                    time.sleep(1)
                # Increment cycle number
                cycle += 1
                # Reset inspection point metrics for the upcoming cycle
                self._inspection_elements_completed = 0
                self._arm_pointing_failure_count = 0
        # Set periodic_mission_end_datetime to now
        periodic_mission_end_datetime = datetime.now()
        # Computing periodic Mission Summary metrics
        self._write_periodic_mission_summary(csv_filepath, number_of_cycles,
                                             periodic_mission_start_datetime,
                                             periodic_mission_end_datetime)
        # Compute inspection_time
        inspection_time = (periodic_mission_end_datetime -
                           periodic_mission_start_datetime).total_seconds()
        # Log status
        self._log_command_status(command_name="periodic_inspection",
                                 status=True)
        self._logger_info((
            'ArmSensorInspector: Completed the requested {} inspection cycles in {} mins!'
        ).format(number_of_cycles, (inspection_time) / 60))
        return True, inspection_time

    def go_to_dock(self, dock_id=None):
        ''' A function that commands the robot to go to a given dock_id if the robot is not already
            at that dock_id.
            - Args:
                - dock_id(int): the ID associated with the dock
            - Returns:
                - Boolean indicating if docking operation is successful
        '''
        # Return False if dock_id is not an integer
        if dock_id is not None and not isinstance(dock_id, int):
            self._logger_error((
                'ArmSensorInspector:  The provided dock_id {} is not an integer!'
            ).format(dock_id))
            return False
        self._logger_info('ArmSensorInspector: Running go_to_dock')
        # Create a mission without any element. This should automatically
        # succeed and return to dock
        curated_mission = self._create_identical_mission_without_elements()
        # Set mission params
        self._set_mission_params(curated_mission,
                                 mission_name='Go_To_Dock',
                                 dock_at_the_end=True)
        # Check if the mission contains docks
        if (len(curated_mission.docks) == 0):
            self._logger_info(
                "ArmSensorInspector: Mission has no docks registered. Quit.")
            return False
        # If the mission contains a single dock and dock_id is not specified, go to the dock in the mission
        elif (len(curated_mission.docks) == 1) and (dock_id is None):
            # Check if the robot is docked
            if (self._docking_client.get_docking_state().status ==
                    docking_pb2.DockState.DOCK_STATUS_DOCKED):
                self._logger_info(
                    "ArmSensorInspector: the robot is already on the dock!")
                return True
            success = self._execute_mission_on_robot(curated_mission)
            # Log status
            self._log_command_status(command_name="go_to_dock", status=success)
            return success
        # Check if there are multiple docks in the mission and a dock id is not specified
        elif (len(curated_mission.docks) > 1) and (dock_id is None):
            self._logger_info(
                "ArmSensorInspector: Mission has multiple dock locations. Specify dock number."
            )
            return False
        # Find the specified Dock ID in the mission docks and go to the dock if it exists in the mission
        self._logger_info("ArmSensorInspector: Dock ID is specified as " +
                          str(dock_id))
        for dock in curated_mission.docks:
            if (dock.dock_id == dock_id):
                # Check if the robot is docked on the given dock_id
                if (self._docking_client.get_docking_state().status ==
                        docking_pb2.DockState.DOCK_STATUS_DOCKED):
                    self._logger_info(
                        "ArmSensorInspector: the robot is already on the dock!"
                    )
                    return True
                # Pick this dock as the destination and create a new mission
                mission_name = self._base_mission.map_name + "_Go_To_Dock"
                global_parameters = self._base_mission.global_parameters
                playback_mode = self._base_mission.playback_mode
                curated_mission = Walk(mission_name=mission_name,
                                       global_parameters=global_parameters,
                                       playback_mode=playback_mode,
                                       docks=[dock])
                # command the robot to go to the dock
                success = self._execute_mission_on_robot(curated_mission)
                # Log status
                self._log_command_status(command_name="go_to_dock",
                                         status=success)
                return success
        self._logger_info(
            "ArmSensorInspector: The specified Dock ID is not in the mission")
        return False

    def go_to_inspection_waypoint(self, inspection_id):
        ''' A function that commands the robot to go to a given inspection_id's waypoint.
            - Args:
                - inspection_id(string): the ID associated with the inspection
            - Returns:
                - Boolean indicating if docking operation is successful
        '''
        self._logger_info(
            'ArmSensorInspector: Running go_to_inspection_waypoint for inspection_id '
            + str(inspection_id))
        # Create a mission without any element
        curated_mission = self._create_identical_mission_without_elements()
        # Get mission_element using the inspection_id
        mission_element = self._base_inspection_elements.get(inspection_id)
        # Quit if inspection_id is invalid
        if not mission_element:
            self._logger_info((
                'ArmSensorInspector: Invalid inspection_id: {}! It is not in the list of inspection_ids : {}! '
            ).format(inspection_id, self._base_inspection_ids))
            return
        # Get the target corresponding to the inspection_id
        target = mission_element.target
        # Create a mission element using the info above add it to the empty curated_mission
        element = Element(name="go_to_inspection_id " + str(inspection_id),
                          target=target,
                          action=Action(),
                          action_wrapper=ActionWrapper())
        curated_mission.elements.append(element)
        # Set mission params
        self._set_mission_params(curated_mission,
                                 mission_name='Go_To_Inspection_Waypoint',
                                 dock_at_the_end=False)
        # Command the robot to go_to_inspection_waypoint

        success = self._execute_mission_on_robot(curated_mission)
        # Log status
        self._log_command_status(command_name="go_to_inspection_waypoint",
                                 status=success)
        return True

    def _load_mission(self, walk_file_path):
        ''' A helper function that deserializes a mission file into walks_pb2.Walk and updates the member variable
            base_mission and returns the mission.
            - Args:
                - walk_file_path(string): a filepath to mission file in the serialized ".Walk" format
            - Returns:
                - mission(walks_pb2.Walk): the deserialized mission from the given mission file
        '''
        with open(walk_file_path, "rb") as mission_file:
            # Load the Autowalk .walk file that contains Arm Sensor Pointing actions
            data = mission_file.read()
            mission = Walk()
            mission.ParseFromString(data)
            self._logger_info("ArmInSensorInspector: Loaded AutoWalk File - " +
                              str(walk_file_path))
        # Update member variables
        self._base_mission = mission.__deepcopy__()
        self._base_inspection_elements, self._base_inspection_ids = self._get_base_inspections(
        )
        self._num_of_inspection_elements = self._get_num_of_inspection_elements(
            self._base_mission)
        return mission

    def _write_mission_to_walk_file(
        self,
        mission,
        output_dir,
        output_mission_name,
    ):
        ''' A helper function that writes a mission proto to file in ".walk" format.
            Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - output_dir(string): the filepath of the desired output directory to store the mission file
                - output_mission_name(string): the desired name of the file name for the mission
        '''
        # Write out the mission.
        output_filepath = output_dir + '/' + output_mission_name + '.walk'
        with open(output_filepath, 'wb') as output:
            output.write(mission.SerializeToString())

    def _execute_mission_on_robot(self,
                                  mission,
                                  mission_timeout=60,
                                  output_dir=None,
                                  output_filename=None):
        ''' A helper function that loads and plays a mission.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - mission_timeout(seconds): a time when the mission should pause execution in seconds
                - output_dir(string): the filepath of the desired output directory to store inspection images
                - output_filename(string): the desired name of the file name for a single captured image.
                                           This should only be set if the mission contains a single image.
            - Returns:
                - Boolean indicating if mission execution is successful
        '''
        # Forcibly take the lease
        self._lease_client.take()
        # Load the mission onto the robot
        load_mission_success = self._run_with_fallback(
            self._load_mission_to_robot, mission)
        # Return if mission loading is not successful
        if not load_mission_success:
            self._logger_info("ArmSensorInspector: Mission loading failed!")
            return False
        # Print the relevant mission info
        self._print_mission_info(mission)
        # Play the mission if loading is successful and return status
        return self._run_with_fallback(self._play_mission, mission_timeout,
                                       output_dir, output_filename)

    def _load_mission_to_robot(self, mission):
        ''' A helper function that loads a mission to the robot by sending it to the autowalk service.
            This function ensures that robot motor power is on and robot is localized to uploaded map.
            It also disables battery monitor to prevent battery level requirements to start a mission.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
            - Returns:
                - Boolean indicating if mission loading is successful
        '''
        # Determine if the robot motors are powered on. If not, turn them on.
        # If motor power cannot be turned on, do not proceed!
        assert self._ensure_motor_power_is_on(
        ), "ArmSensorInspector requires robot motors are turned on!"
        # Determine if the robot is localized to the uploaded graph. If not, localize the robot.
        # If robot can't be turned localized, do not proceed!
        assert self._ensure_robot_is_localized(
        ), "ArmSensorInspector requires robot to be localized to the uploaded map!"
        # Prepare body lease in order to load mission to the robot
        body_lease = self._lease_client.lease_wallet.advance()
        # Load the mission to the robot and report the load_autowalk_response
        try:
            load_autowalk_response = self._autowalk_service_client.load_autowalk(
                mission, [body_lease])
        except ResponseError as resp_err:
            load_autowalk_response = resp_err.response
        # Check the load_autowalk_response
        if load_autowalk_response.status == autowalk_pb2.LoadAutowalkResponse.STATUS_OK:
            self._logger_info(
                "ArmSensorInspector: Successfully loaded the mission to robot!"
            )
            # Associate element identifiers to mission element's name
            self._node_map = self._generate_node_map(
                mission.elements, load_autowalk_response.element_identifiers)
            return True
        elif load_autowalk_response.status == autowalk_pb2.LoadAutowalkResponse.STATUS_COMPILE_ERROR:
            self._logger_error("ArmSensorInspector: STATUS_COMPILE_ERROR")
        elif load_autowalk_response.status == autowalk_pb2.LoadAutowalkResponse.STATUS_VALIDATE_ERROR:
            self._logger_error("ArmSensorInspector: STATUS_VALIDATE_ERROR")
        self._logger_error(
            "ArmSensorInspector: Problem loading the mission to robot! Status {} Failed Elements <index,error> : {} Failed Nodes: {} "
            .format(load_autowalk_response.status,
                    load_autowalk_response.failed_elements,
                    load_autowalk_response.failed_nodes))
        return False

    def _play_mission(self,
                      mission_timeout=60,
                      output_dir=None,
                      output_filename=None):
        ''' A helper function that plays a mission that is already on the robot
            - Args:
                - mission_timeout(seconds): a time when the mission should pause execution
                - output_dir(string): the filepath of the desired output directory to store inspection images
                - output_filename(string): the desired name of the file name for a single captured image.
                                           This should only be set if the mission contains a single image.
            - Returns:
                - Boolean indicating if mission playing is successful
        '''
        self._logger_info('ArmSensorInspector: Running mission...')
        # Initialize self._arm_pointing_failure_count
        self._arm_pointing_failure_count = 0
        # Initialize the number of inspection points completed
        self._inspection_elements_completed = 0
        # Initialize the status of the mission
        self._mission_status = self._mission_client.get_state().status
        # Initialize inspection_action_start_time to now
        inspection_action_start_time = time.time()
        # Initialize last_running_action_name and last_completed_action_name
        last_running_action_name = ""
        last_completed_action_name = ""
        # Initialize threads
        threads = []
        # Initialize play request times
        play_request_rate = 10  # seconds
        self._play_request_time = time.time()
        # Play the mission
        while self._mission_status in (mission_pb2.State.STATUS_NONE,
                                       mission_pb2.State.STATUS_RUNNING,
                                       mission_pb2.State.STATUS_PAUSED):
            # Check for element-wise feedback
            mission_element_name, element_feedback = self._run_with_fallback(
                self._element_wise_feedback)
            if mission_element_name is not None:
                # Check if element_feedback is true which indicates the completion of an inspection action
                # Also check if the last_completed_action_name is not the same as the current mission_element_name
                if element_feedback and (last_completed_action_name !=
                                         mission_element_name):
                    # Set inspection_action_end_time to now
                    inspection_action_end_time = time.time()
                    self._logger_info('ArmSensorInspector: Completed ' +
                                      mission_element_name)
                    # Update the last_completed_action_name to mission_element_name
                    last_completed_action_name = mission_element_name
                    # Start a separate thread to retrieve images from the robot
                    # This is to make sure downloading images does not block _element_wise_feedback
                    download_image_thread = threading.Thread(
                        target=self._run_with_fallback,
                        args=(self._download_image_from_robot,
                              inspection_action_start_time,
                              inspection_action_end_time, output_dir,
                              output_filename))
                    download_image_thread.start()
                    # Add download_image_thread to threads
                    threads.append(download_image_thread)
                    # Reset inspection_action_start_time
                    inspection_action_start_time = inspection_action_end_time
                elif last_running_action_name != mission_element_name:
                    self._logger_info('ArmSensorInspector: Running ' +
                                      mission_element_name)
                # Update the last_running_action_name to mission_element_name
                last_running_action_name = mission_element_name
            # Mission fails if any operator questions are persistent
            mission_questions = self._mission_client.get_state().questions
            if mission_questions:
                # Answer mission questions
                if not self._run_with_fallback(self._answer_mission_question,
                                               mission_questions):
                    # If answering the questions did not help, fail the mission
                    self._logger_error(
                        'ArmSensorInspector: Mission failed by triggering operator question.'
                    )
                    return False
            # Send play request every play_request_rate
            if (time.time() >= self._play_request_time):
                # Advance body lease
                body_lease = self._lease_client.lease_wallet.advance()

                # @Todo 미션 설정
                # Send play request
                disable_directed_exploration = False
                path_following_mode = map_pb2.Edge.Annotations.PATH_MODE_STRICT
                play_settings = mission_pb2.PlaySettings(
                    disable_directed_exploration=disable_directed_exploration,
                    path_following_mode=path_following_mode)

                play_mission_response = self._mission_client.play_mission(
                    pause_time_secs=time.time() + mission_timeout,
                    settings=play_settings,
                    leases=[body_lease])

                # Return if play requested fails
                if not play_mission_response:
                    self._logger_error(
                        "ArmSensorInspector: Mission Play Request Failed!")
                    return False
                # Update the next play_request_time
                self._play_request_time = time.time() + play_request_rate
            self._mission_status = self._mission_client.get_state().status
        # Make sure the last action is reported as both running and completed
        if last_running_action_name != last_completed_action_name:
            # Set the end time to now
            inspection_action_end_time = time.time()
            # Query its image
            download_image_thread = threading.Thread(
                target=self._run_with_fallback,
                args=(self._download_image_from_robot,
                      inspection_action_start_time, inspection_action_end_time,
                      output_dir, output_filename))
            download_image_thread.start()
            # Add download_image_thread to threads
            threads.append(download_image_thread)
        # Join all threads to the main thread to make sure image threads are done before mission is over
        for t in threads:
            t.join()
        # Report mission status
        self._logger_info(
            "ArmSensorInspector: Mission Execution Successful? " +
            str(self._mission_status == mission_pb2.State.STATUS_SUCCESS))
        return self._mission_status == mission_pb2.State.STATUS_SUCCESS

    def _pause_mission(self):
        ''' A helper function that pauses a mission that is already being executing on the robot.
            - Returns:
                - Boolean indicating if _pause_mission operation is successful
        '''
        self._mission_status = self._mission_client.get_state().status
        if self._mission_status in (mission_pb2.State.STATUS_NONE,
                                    mission_pb2.State.STATUS_RUNNING):
            self._mission_client.pause_mission()
            self._logger_info("ArmSensorInspector: Paused mission!")
            # Update self._mission_status
            self._mission_status = self._mission_client.get_state().status
            return True
        else:
            self._logger_warning(
                "ArmSensorInspector: Pausing a mission is not allowed if mission is not running!"
            )
            return False

    def _resume_mission(self, mission_timeout=60):
        ''' A helper function that resumes a mission that has been paused.
            Args:
                - mission_timeout(seconds): a time when the mission should pause execution
            - Returns:
                - Boolean indicating if _resume_mission operation is successful
        '''
        self._mission_status = self._mission_client.get_state().status
        # Return if the mission is not paused
        if self._mission_status != mission_pb2.State.STATUS_PAUSED:
            self._logger_warning(
                "ArmSensorInspector: Resuming a mission is not allowed if mission is not paused!"
            )
            return False
        # Send a play mission request to resume
        while self._mission_status == mission_pb2.State.STATUS_PAUSED:
            # Advance body lease
            body_lease = self._lease_client.lease_wallet.advance()
            # Send play request
            play_mission_response = self._mission_client.play_mission(
                pause_time_secs=time.time() + mission_timeout,
                leases=[body_lease])
            # Return if play requested fails
            if not play_mission_response.status == mission_pb2.PlayMissionResponse.STATUS_OK:
                self._logger_error(
                    "ArmSensorInspector: Mission Resume Request Failed!")
                return False
            # Update self._mission_status
            self._mission_status = self._mission_client.get_state().status
            # Update the self._play_request_time
            self._play_request_time = time.time()
        self._logger_info("ArmSensorInspector: Resumed mission!")
        return True

    def _answer_mission_question(self, questions):
        ''' A helper function that answers questions raised during mission execution on the robot.
            - Args:
                - questions(list of mission_pb2.State.Question): a list of mission questions obtained via self._mission_client.get_state().questions
            - Returns:
                - Boolean indicating if we have answered the mission question successful
        '''
        for question in questions:
            if (question.text.find("is waiting") != -1):
                # If the mission question involves information about the robot waiting for battery threshold or moving object
                return True
            if (question.text.find(ACTION_NAME) != -1):
                # Increment self._arm_pointing_failure_count
                self._arm_pointing_failure_count += 1
            # Stow the arm to make sure that the arm is not deployed while robot is executing the next mission node
            self._stow_arm()
            self._logger_error('ArmSensorInspector: ' + str(question.text))
            answer_code = self._get_answer_code_to_mission_question(
                question.options, MISSION_QUESTION_ANSWER_CHOICE)
            self._mission_client.answer_question(question.id, answer_code)
            self._logger_info(
                'ArmSensorInspector: Answered mission question  with ' +
                str(MISSION_QUESTION_ANSWER_CHOICE))
        # Check if mission questions are still persistent
        if self._mission_client.get_state().questions:
            self._logger_error(
                'ArmSensorInspector: Mission questions are still persistent!')
            return False
        return True

    def _get_answer_code_to_mission_question(self, options, answer_string):
        ''' A helper function that returns the answer code associated with a string.
            - Args:
                - answer_string(string): a string input used to query for answer code to a mission question
                    - Choices = ["Try Again","Skip","Return to dock and terminate mission"]
                - options(list of nodes_pb2.Prompt.Option): answer options for mission questions
                                                           obtained via self._mission_client.get_state().questions[i].options
            - Returns:
                - answer_code(int): a code associated with the string if string exists if not returns 2 which is "Try Again"
        '''
        answer_code = 2  # default as 2 which is "Try Again"
        for option in options:
            if (option.text.find(answer_string) != -1):
                # We have found the answer we want. Go ahead assign the answer_code associated
                answer_code = option.answer_code
        return answer_code

    def _element_wise_feedback(self):
        ''' A helper function that provide element-wise feedback during mission execution.
            - Returns:
                - mission_element_name(string):  return the name of the mission element that is being executed
                - Boolean indicating if an element is successful
        '''

        # Return if there are no inspections
        if not self._node_map:
            return None, False
        # Get mission state
        mission_state = self._mission_client.get_state()
        if mission_state.history:
            # Look at the most recent mission_state.history which is always the first index
            for node_state in mission_state.history[0].node_states:
                # Query for element name given the node_state.id
                mission_element_name = self._node_map.get(node_state.id)
                # Return the mission_element_name and result if node_state.id is in self._node_map
                if mission_element_name is not None:
                    return mission_element_name, (
                        node_state.result == util_pb2.RESULT_SUCCESS)
        # Did not find node_state.id is in self._node_map
        return None, False

    def _generate_node_map(self, mission_elements, element_identifiers):
        ''' A helper function that generates a map that associates mission element's name to element identifiers
            to provide element-wise feedback for missions.
            - Args:
                - mission_elements(a list of autowalk_pb2.Element):  a list of mission elements that correspond to the mission loaded onto the robot
                - element_identifiers(autowalk_pb2.ElementIdentifier):  element_identifiers obtained from load_autowalk response
            - Returns:
                - node_map(dict): a dictionary with key:element_identifier.action_id.node_id and value: inspection_id
        '''
        # Check the number of elements is equivalent to the number of element_identifiers
        if len(mission_elements) != len(element_identifiers):
            return None
        # Generate a node map that associates mission element names with their corresponding element_identifiers
        node_map = {}
        for i in range(len(element_identifiers)):
            element_identifier = element_identifiers[i]
            # Add the node id associated with the element_identifier's action id
            if (len(element_identifier.action_id.user_data_id) > 0):
                node_map[element_identifier.action_id.
                         node_id] = mission_elements[i].name
        return node_map

    def _run_with_fallback(self, cmd_func, *input_to_cmd_func):
        ''' A helper function that runs and handles exceptions for an input function given its argument.
            This is helpful when calling ui_functions that may have transient errors at the robot level that
            may self-resolve (as opposed to at the mission level), for example comms issues.
            - Args:
                - cmd_func(Function): the name of the function as defined
                - input_to_cmd_func(Function Input): a single argument for cmd_func
            - Returns:
                - return_value(Function return) : the return value associated it with cmd_func
        '''
        return_value = None
        success = False
        attempt_number = 0
        num_retries = 4
        while attempt_number < num_retries and not success:
            attempt_number += 1
            try:
                return_value = cmd_func(*input_to_cmd_func)
                success = True
            except Exception as err:
                # Log Exception
                text_message = "ArmSensorInspector: Exception raised running [{}] : [{}] {} - file: {} at line ({}) Trying again!".format(
                    str(cmd_func), type(err), str(err),
                    err.__traceback__.tb_frame.f_code.co_filename,
                    err.__traceback__.tb_lineno)
                self._logger_error(text_message)
            time.sleep(1) if not success else time.sleep(0)
        return return_value

    def _create_identical_mission_without_elements(self):
        ''' A helper function that creates a new mission that has the same fields as the loaded mission, but has no elements
            - Returns:
                - curated_mission(walks_pb2.Walk): a new mission that has the same fields as the loaded mission excluding mission elements
        '''
        mission_name = self._base_mission.mission_name
        docks = self._base_mission.docks
        global_parameters = self._base_mission.global_parameters
        # Create a new mission without elements
        curated_mission = Walk(mission_name=mission_name,
                               global_parameters=global_parameters,
                               docks=docks)
        # Set playback mode to once
        self._set_playback_mode_once(curated_mission)
        return curated_mission

    def _extract_inspection_id_from_mission_element_name(
            self, mission_element_name):
        ''' A helper function that returns the inspection_id given the mission element name
            - Args:
                - mission_element_name(string): the string linked with the mission_element_name
            - Returns:
                - inspection_id(string) corresponding to the mission_element_name
        '''
        # For now ASP is printing as 'Arm Pointing - 1' so its easier to find the digit as follows
        return ''.join(filter(str.isdigit, mission_element_name))

    def _construct_mission_given_inspection_ids(self, inspection_ids):
        ''' A helper function that returns the mission consisting of elements associated with the
            inspection_ids. This function should fail if all elements requested are not present in the
            mission.
            - Args:
                - inspection_ids(list of int): a list of ints that indicate an inspection point ID number.
            - Returns:
                - curated_mission(walks_pb2.Walk): a mission that has only the inspection_elements
                                                    corresponding to the inspection_ids
        '''
        # Create an mission without elements
        curated_mission = self._create_identical_mission_without_elements()
        # Fill with elements that correspond to the inspection ids.
        chosen_elements = self._select_inspection_elements(inspection_ids)
        # Check if chosen_elements is None
        if not chosen_elements:
            self._logger_info(
                'ArmSensorInspector: All elements requested are not present in the mission.'
            )
            return
        # Given the chosen elements append each to curated_mission.elements
        for chosen_element in chosen_elements:
            curated_mission.elements.append(chosen_element)
        return curated_mission

    def _get_base_inspections(self):
        ''' A helper function that returns a dictionary of inspection mission elements with
            their respective inspection_id and a list of inspection IDs.
            - Returns:
                - arm_sensor_pointing_elements(dict): a dict  with key - inspection_id and value - Autowalk Element
                - inspection_ids(list): a list of ids associated with each inspection mission element
         '''
        arm_sensor_pointing_elements = {}
        inspection_ids = []
        self.inspection_arm_poses = []
        for mission_element in self._base_mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                # We have found the action name we are interested in
                # So go ahead and parse the line to extract waypoints
                inspection_id = mission_element.name
                # Add the mission element to the arm_sensor_pointing_elements dict
                arm_sensor_pointing_elements[inspection_id] = mission_element
                # Add the inspection_id to inspection_ids list
                inspection_ids.append(inspection_id)

                arm_pose = mission_element.action.data_acquisition.record_time_images[0].shot.transforms_snapshot.child_to_parent_edge_map['arm0.link_wr1'].parent_tform_child
                self.inspection_arm_poses.append(arm_pose)

        return arm_sensor_pointing_elements, inspection_ids

    def _select_inspection_elements(self, inspection_ids):
        ''' A helper function that returns the mission elements associated with the
            inspection_ids. This function should fail if all elements requested are not present in the
            mission.
            - Args:
                - inspection_ids(list of int): a list of ints that indicate an inspection point ID number.
            - Returns:
                - inspection_elements(list of AutoWalk Element): a list of AutoWalk Elements corresponding to the inspection_ids
         '''
        # Using the self._base_inspection_elements find the mission elements corresponding to inspection_ids
        inspection_elements = []
        for inspection_id in inspection_ids:
            inspection_element = self._base_inspection_elements.get(
                inspection_id)
            # Quit if inspection_id is invalid
            if not inspection_element:
                self._logger_info((
                    'ArmSensorInspector: Invalid inspection_id: {}! It is not in the list of inspection_ids : {}! '
                ).format(inspection_id, self._base_inspection_ids))
                return
            # Append if inspection_element is not None
            inspection_elements.append(inspection_element)
        return inspection_elements

    def _clear_graph(self):
        ''' A helper function that clears the state of the map on the robot, removing all waypoints and edges.
            - Returns:
                - Boolean indicating if the given map is cleared successfully or not.
        '''
        self._logger_info(
            "ArmSensorInspector: Cleared the pre-existing map on the robot")
        return self._graph_nav_client.clear_graph()

    def _upload_map_and_localize(self):
        ''' A helper function that uploads the graph and snapshots to the robot and localizes the robot to the map.
           - Returns:
                - Boolean indicating if the given map is uploaded and localized to the robot successfully or not.
        '''
        # Clear the preexisting map on the robot
        self._clear_graph()
        # Forcibly take the lease
        self._lease_client.take()
        # Determine if the robot motors are powered on. If not, turn them on.
        # If motor power cannot be turned on, do not proceed!
        assert self._ensure_motor_power_is_on(
        ), "ArmSensorInspector requires robot motors are turned on!"
        # For RGB body camera, we can't localize to the dock fiducial while docked
        # So, undock the robot before localizing
        get_docking_state = self._docking_client.get_docking_state()
        if get_docking_state.status == docking_pb2.DockState.DOCK_STATUS_DOCKED:
            blocking_undock(self._robot)
            get_docking_state = self._docking_client.get_docking_state()
            if get_docking_state.status == docking_pb2.DockState.DOCK_STATUS_UNDOCKED:
                self._logger_info(
                    "ArmSensorInspector: Robot is undocked and ready to initialize localization"
                )
        with open(self._walk_folder_path + "/graph", "rb") as graph_file:
            # Load the graph from disk.
            data = graph_file.read()
            self._current_graph = map_pb2.Graph()
            self._current_graph.ParseFromString(data)

        # @Todo: 미션 설정
        disable_alternate_route_finding = True
        if disable_alternate_route_finding:
            for edge in self._current_graph.edges:
                edge.annotations.disable_alternate_route_finding = True

        for waypoint in self._current_graph.waypoints:
            # Load the waypoint snapshots from disk.
            with open(
                    self._walk_folder_path +
                    "/waypoint_snapshots/{}".format(waypoint.snapshot_id),
                    "rb") as snapshot_file:
                waypoint_snapshot = map_pb2.WaypointSnapshot()
                waypoint_snapshot.ParseFromString(snapshot_file.read())
                self._current_waypoint_snapshots[
                    waypoint_snapshot.id] = waypoint_snapshot

        for edge in self._current_graph.edges:
            if len(edge.snapshot_id) == 0:
                continue
            # Load the edge snapshots from disk.
            with open(
                    self._walk_folder_path +
                    "/edge_snapshots/{}".format(edge.snapshot_id),
                    "rb") as snapshot_file:
                edge_snapshot = map_pb2.EdgeSnapshot()
                edge_snapshot.ParseFromString(snapshot_file.read())
                self._current_edge_snapshots[edge_snapshot.id] = edge_snapshot

        # Upload the graph to the robot.
        true_if_empty = not len(self._current_graph.anchoring.anchors)
        response = self._graph_nav_client.upload_graph(
            graph=self._current_graph, generate_new_anchoring=true_if_empty)
        # Return if status is not okay
        if response.status != graph_nav_pb2.UploadGraphResponse.STATUS_OK:
            self._logger_error(
                "ArmSensorInspector: Problem uploading graph to robot!")
            return False
        # Upload the snapshots to the robot.
        for snapshot_id in response.unknown_waypoint_snapshot_ids:
            waypoint_snapshot = self._current_waypoint_snapshots[snapshot_id]
            self._graph_nav_client.upload_waypoint_snapshot(waypoint_snapshot)
        for snapshot_id in response.unknown_edge_snapshot_ids:
            edge_snapshot = self._current_edge_snapshots[snapshot_id]
            self._graph_nav_client.upload_edge_snapshot(edge_snapshot)
        # Uploaded graph, waypoint_snapshots, and edge_snapshots
        self._logger_info(
            "ArmSensorInspector: Uploaded graph, waypoint_snapshots, and edge_snapshots from "
            + str(self._walk_folder_path))
        # Localize the robot to the map
        return self._ensure_robot_is_localized()

    def _take_image_with_daq(self, output_dir=None, output_filename=None):
        ''' A helper function that saves the hand color image using the data acquisition service.
            - Args:
                - output_dir(string): the filepath of the desired output directory to store inspection images
                - output_filename(string): the desired name of the file name for a single captured image.
                                           This should only be set if the mission contains a single image.
            - Returns:
                - Boolean indicating if _take_image_with_daq operation is successful
        '''
        # DAQ service
        acquisition_requests = data_acquisition_pb2.AcquisitionRequestList()
        acquisition_requests.image_captures.extend([
            data_acquisition_pb2.ImageSourceCapture(
                image_service="image", image_source="hand_color_image")
        ])
        # Wait to allow the camera to focus
        time.sleep(3)
        # NOTE: we provide an empty dictionary for the metadata because we have no metadata to save, and
        # we need to pass something to work around a client side bug where it fails when "metadata=None".
        start_t = time.time()
        success = acquire_and_process_request(self._data_acquisition_client,
                                              acquisition_requests,
                                              group_name="ArmSensorInspector",
                                              action_name="inspection",
                                              metadata={})
        end_t = time.time()
        self._log_command_status(command_name="take_image_with_daq",
                                 status=success)
        if not success:
            return False
        # Download the captured image
        return self._run_with_fallback(self._download_image_from_robot,
                                       start_t, end_t, output_dir,
                                       output_filename)

    def _download_image_from_robot(self,
                                   start_time,
                                   end_time,
                                   output_dir=None,
                                   output_filename=None,
                                   additional_params=None):
        ''' A helper function to retrieve all images from the DataBuffer REST API and write them to files in local disk.
            - Args:
                - start_time(timestamp): the timestamp of the desired start time needed to download images
                - end_time(timestamp): the timestamp of the desired end time needed to download images
                - output_dir(string): the filepath of the desired output directory to store inspection images
                - output_filename(string): the desired name of the file name for a single captured image.
                                           This should only be set if the mission contains a single image.
                - additional_params(dict): Additional GET parameters to append to the URL.
            - Returns:
                - Boolean indicating if the data was downloaded successfully or not.
        '''
        # Query parameters to use to retrieve metadata from the DataStore service.
        query_params = make_time_query_params(start_time, end_time,
                                              self._robot)
        # Hostname to specify in URL where the DataBuffer service is running.
        hostname = self._robot.address
        # User token to specify in https GET request for authentication.
        token = self._robot.user_token
        # Folder where to download the data.
        if output_dir is None:
            output_dir = os.getcwd()
        # REST API to query an image from the robot
        url = 'https://{}/v1/data-buffer/daq-data/'.format(hostname)
        headers = {"Authorization": "Bearer {}".format(token)}
        get_params = additional_params or {}
        if query_params.HasField('time_range'):
            get_params.update({
                'from_nsec':
                query_params.time_range.from_timestamp.ToNanoseconds(),
                'to_nsec':
                query_params.time_range.to_timestamp.ToNanoseconds()
            })
        chunk_size = 10 * (1024**2)  # This value is not guaranteed.
        url = url + '?{}'.format(urlencode(get_params))
        request = Request(url, headers=headers)
        context = ssl._create_unverified_context()
        with urlopen(request, context=context) as resp:
            # This is the default file name used to download data, updated from response.
            if resp.status == 204:
                self._logger_info("ArmSensorInspector: " + str(
                    "No content available for the specified download time range (in seconds): "
                    "[%d, %d]" %
                    (query_params.time_range.from_timestamp.ToNanoseconds() /
                     1.0e9,
                     query_params.time_range.to_timestamp.ToNanoseconds() /
                     1.0e9)))
                return False
            # Check whether the  specified path is an existing file
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            zip_folder_name = "download_" + datetime.now().strftime(
                "%m%d%Y_%H%M%S") + ".zip"
            download_file = Path(output_dir, zip_folder_name)
            content = resp.headers['Content-Disposition']
            if not content or len(content) < 2:
                self._logger_error(
                    "ArmSensorInspector: Content-Disposition is not set correctly"
                )
                return False
            else:
                start_ind = content.find('\"')
                if start_ind == -1:
                    self._logger_error(
                        "ArmSensorInspector: Content-Disposition does not have a \""
                    )
                    return False
                else:
                    start_ind += 1

            with open(str(download_file), 'wb') as fid:
                while True:
                    chunk = resp.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    print('.', end='', flush=True)
                    fid.write(chunk)
        # Data downloaded and saved to local disc successfully in a zip.
        count = 0
        with zipfile.ZipFile(download_file, 'r') as zip_folder:
            files = zip_folder.namelist()
            # Extract the image file to its corresponding folder
            for file_name in files:
                if file_name.endswith('.jpg'):
                    zip_folder.extract(file_name, output_dir)
                    # Check if the user has provided an output_filename
                    new_img_name = ""
                    if output_filename is None:
                        # Split the file_name by "/" and query the image name
                        img_name = file_name.split("/")[1]
                        # Extract the image name without the jpg extension
                        img_name_without_jpg_ext = img_name.split(".")[0]
                        # Define timestamp
                        timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")
                        # Apppend the timestamp to create new_img_name
                        new_img_name = img_name_without_jpg_ext + "_" + str(
                            timestamp) + ".jpg"
                    else:
                        # Using the output_filename
                        new_img_name = output_filename + ".jpg"
                    # Rename filename such that the image moves up a directory
                    os.rename(output_dir + '/' + file_name,
                              output_dir + '/' + new_img_name)
                    self._logger_info("Saved " + str(output_dir) + "/" +
                                      str(new_img_name))
                    # Remove the folder that the image came in from the robot
                    os.rmdir(output_dir + '/' + file_name.split("/")[0])
                    count += 1
        # If the user provided an output_filename and robot returned multiple images
        # for the given start and end time, we return False since this is an error.
        if output_filename and count > 1:
            self._logger_error((
                "ArmSensorInspector: Downloaded {} image(s) from the robot! However, an output_filename was provided! This is an unexpected behavior!"
            ).format(count))
            return False
        # Update the number of inspection points completed
        self._inspection_elements_completed += count
        self._logger_info(
            ("ArmSensorInspector: Downloaded {} image(s) from the robot!"
             ).format(count))
        # Remove the zip folder after extraction
        os.remove(download_file)
        return True

    def _battery_status(self, silent_print=False):
        ''' A helper function that provides the status of the robot battery.
            - Args:
                - silent_print(boolean): a boolean to silence printing the battery status
            - Returns:
                - battery_level(double): the current battery level percentage
                - min_battery_temp(double): the current min temperature for the battery
                - max_battery_temp(double): the current max temperature for the battery
        '''
        robot_state = self._robot_state_client.get_robot_state()
        battery_states = robot_state.battery_states
        # Check if battery_states is available
        if not battery_states:
            self._logger_error(
                "ArmSensorInspector: Problem in querying for battery_states!")
            # -1 indicates an error
            battery_level = min_battery_temp = max_battery_temp = -1
            return battery_level, min_battery_temp, max_battery_temp
        # Take a look at the most recent battery_state
        battery_state = battery_states[0]
        # Query the battery status
        status = battery_state.Status.Name(battery_state.status)
        # Get rid of the STATUS_ prefix
        status = status[7:]
        battery_temperatures = battery_state.temperatures
        # Check if battery_temperatures is available
        if battery_temperatures:
            min_battery_temp = min(battery_temperatures)
            max_battery_temp = max(battery_temperatures)
        else:
            # -1 indicates an invalid temp
            min_battery_temp = max_battery_temp = -1
        battery_level = battery_state.charge_percentage.value
        # Check if battery level is available
        if battery_level:
            bar_len = int(battery_state.charge_percentage.value) // 10
            bat_bar = '|{}{}|'.format('=' * bar_len, ' ' * (10 - bar_len))
        else:
            # -1 indicates an invalid battery level
            battery_level = -1
            bat_bar = ''
        time_left = ''
        # Check if battery_state.estimated_runtime is available
        if battery_state.estimated_runtime:
            time_left = ' ({})'.format(
                secs_to_hms(battery_state.estimated_runtime.seconds))
        # Print the battery status if print is not silenced
        if not silent_print:
            print_1 = (' Battery: {}{}{}{}'.format(status, bat_bar,
                                                   battery_level, time_left))
            print_2 = (" Min Battery Temp: {} Max Battery Temp: {}".format(
                min_battery_temp, max_battery_temp))
            print_3 = " Battery voltage: " + str(battery_state.voltage.value)
            text_message = "ArmSensorInspector: " + print_1 + print_2 + print_3
            self._logger_info(text_message)
        return battery_level, min_battery_temp, max_battery_temp

    def _write_inspection_data(self, csv_filepath, data):
        ''' A helper function that writes inspection data to a csv file.
            - Args:
                - csv_filepath(string): the desired path of the csv
                - data(list): a list of values to be printed to the csv
        '''
        # If folder path is not given use the current working dir
        if csv_filepath is None:
            timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")
            csv_filepath = os.getcwd(
            ) + '/inspection_data' + timestamp + '.csv'
        # Check whether the specified directory is an existing file
        output_dir = os.path.dirname(csv_filepath)
        if not os.path.isdir(output_dir):
            # Create the directory
            os.makedirs(output_dir, exist_ok=True)
        with open(csv_filepath, 'a+', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(data)

    def _write_periodic_mission_summary(self, csv_filepath, number_of_cycles,
                                        periodic_mission_start_datetime,
                                        periodic_mission_end_datetime):
        ''' A helper function that computes metrics and provides a summary for a  periodic_mission.
            - Args:
                - csv_filepath(string): the file path to the mission data stored as a csv file
                - number_of_cycles(int) : the number of cycles used to run the periodic_mission
                - periodic_mission_start_datetime(datetime): a datetime object created when the periodic_mission started
                - periodic_mission_end_datetime(datetime): a datetime object created when the periodic_mission ended
            - Returns:
                - Boolean indicating if writing periodic_mission_summary is successful
        '''
        try:
            # Assign csv_header to the data header for inspection data saved in csv
            csv_header = self._inspection_data_header
            # Read the data saved in the output_filename
            inspection_data = pd.read_csv(csv_filepath)
            # Periodic_mission Stats
            periodic_mission_duration = (
                periodic_mission_end_datetime -
                periodic_mission_start_datetime).total_seconds() / 3600  #hrs
            # Cycle stats. Note that cycles_completed_index should refer to 'Mission Succeeded?'
            cycles_completed_index = csv_header.index("Mission Succeeded?")
            cycles_required = number_of_cycles
            # Initialize cycles_completed
            cycles_completed = 0
            # Compute the frequency of strings linked with cycles_completed_index
            value_counts = inspection_data[
                csv_header[cycles_completed_index]].value_counts()
            # Only change the cycles_completed if the "Mission Succeeded?" column has the field "True"
            if value_counts.get(True):
                cycles_completed = value_counts[True]
            cycles_failed = cycles_required - cycles_completed
            # Inspection stats.
            # Note that inspections_required_index '# of required inspections'
            inspections_required_index = csv_header.index(
                "# of required inspections")
            inspections_required = inspection_data[
                csv_header[inspections_required_index]].sum()
            # Note that inspections_completed_index should refer to '# of completed inspections'
            inspections_completed_index = csv_header.index(
                "# of completed inspections")
            inspections_completed = inspection_data[
                csv_header[inspections_completed_index]].sum()
            # Note that inspections_failed_index should refer to '# of failed inspections'
            inspections_failed_index = csv_header.index(
                "# of failed inspections")
            inspections_failed = inspection_data[
                csv_header[inspections_failed_index]].sum()
            # Arm pointing failure stats. Note that inspections_completed_index should refer to '# of arm pointing failures'
            inspections_failure_index = csv_header.index(
                "# of arm pointing failures")
            arm_pointing_failures = inspection_data[
                csv_header[inspections_failure_index]].sum()
            # Cycle time stats. Note that csv_header[3] should refer to 'Cycle Time in min'
            cycle_time_index = csv_header.index("Cycle Time in min")
            cycle_times = inspection_data[csv_header[cycle_time_index]]
            average_cycle_time = cycle_times.mean()
            median_cycle_time = cycle_times.median()
            std_cycle_time = cycle_times.std()
            cycle_time_Q1 = cycle_times.quantile(0.25)
            cycle_time_Q3 = cycle_times.quantile(0.75)
            min_cycle_time = cycle_times.min()
            max_cycle_time = cycle_times.max()
            # Battery stats. Note that battery_index should refer to 'Battery Consumption'
            battery_index = csv_header.index("Battery Consumption")
            battery_data = inspection_data[csv_header[battery_index]]
            battery_mean = abs(battery_data).mean()
            battery_median = abs(battery_data).median()
            battery_std = abs(battery_data).std()
            battery_Q1 = abs(battery_data).quantile(0.25)
            battery_Q3 = abs(battery_data).quantile(0.75)
            battery_min = abs(battery_data).min()
            battery_max = abs(battery_data).max()
            # Prepare summary data for csv
            summary_data = [
                periodic_mission_start_datetime, periodic_mission_end_datetime,
                periodic_mission_duration, cycles_required, cycles_completed,
                cycles_failed, inspections_required, inspections_completed,
                inspections_failed, arm_pointing_failures, average_cycle_time,
                median_cycle_time, std_cycle_time, cycle_time_Q1,
                cycle_time_Q3, min_cycle_time, max_cycle_time, battery_mean,
                battery_median, battery_std, battery_Q1, battery_Q3,
                battery_min, battery_max
            ]
            self._write_inspection_data(csv_filepath, self._summary_header)
            # Write the summary data to the csv
            self._write_inspection_data(csv_filepath, summary_data)
            return True
        except Exception as err:
            # Log Exception
            text_message = "ArmSensorInspector: Problem in writing in _periodic_mission_summary! Exception raised: [{}] {} - file: {} at line ({})".format(
                type(err), str(err),
                err.__traceback__.tb_frame.f_code.co_filename,
                err.__traceback__.tb_lineno)
            self._logger_error(text_message)
            return False

    def _get_global_parameters(self, mission):
        ''' A function that returns the global_parameters used for inspection missions.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
            - Returns:
                - The field named "global_parameters" in the given mission
        '''
        return mission.global_parameters

    def _get_mission_name(self, mission):
        ''' A function that returns the mission_name.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
            - Returns:
                - The field named "mission_name" in the given mission
        '''
        return mission.mission_name

    def _get_playback_mode(self, mission):
        ''' A function that returns the playback_mode for the mission.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
            - Returns:
                - The field named "playback_mode" in the given mission
        '''
        return mission.playback_mode

    def _get_num_of_inspection_elements(self, mission):
        ''' A function that returns the number of mission elements that have arm sensor pointing actions.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
            - Returns:
                - num_of_inspection_elements(int): number of inspection mission elements
         '''
        # Initialize count
        num_of_inspection_elements = 0
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                # we have found action name we are interested in
                # so go ahead increment the num_of_inspection_elements
                num_of_inspection_elements += 1
        return num_of_inspection_elements

    def _get_gripper_camera_parameters_for_all_elements(self, mission):
        ''' A helper function that gets the gripper camera parameters for all mission elements.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
            Returns:
                - inspection_id_camera_param_map(dict): a dictionary with key:inspection_id and value: gripper_camera_param_pb2.GripperCameraParams
        '''
        inspection_id_camera_param_map = {}
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                inspection_id = mission_element.name
                # Now get the cam params for this element and add it the
                gripper_camera_params = mission_element.action_wrapper.gripper_camera_params.params
                inspection_id_camera_param_map[
                    inspection_id] = gripper_camera_params
        self._logger_info(
            "ArmSensorInspector: Completed getting gripper camera parameters for all mission elements."
        )
        return inspection_id_camera_param_map

    def _get_gripper_camera_parameters_using_id(self, mission,
                                                inspection_id_input):
        ''' A helper function that gets the gripper camera parameters using the inspection_id_input.
            If inspection_id_input is not in the mission, it returns None.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - inspection_id_input(int): the desired inspection_id
            Returns:
                - gripper_camera_params(gripper_camera_param_pb2.GripperCameraParams): the desired gripper camera params
                                                                                        parsed as GripperCameraParams proto
        '''
        # Find the mission element that corresponds to the given inspection id
        gripper_camera_params = None
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                inspection_id = mission_element.name
                # Check if inspection_id_input is not provided
                if inspection_id_input == inspection_id:
                    # Now get the cam params for this element
                    gripper_camera_params = mission_element.action_wrapper.gripper_camera_params.params
                    self._logger_info((
                        "ArmSensorInspector: Completed getting gripper camera parameters for inspection ID: {}!"
                    ).format(inspection_id_input))
                    return gripper_camera_params
        # Return false with an error if we did not find the corresponding mission_element for inspection_id_input
        self._logger_error((
            'ArmSensorInspector: Invalid inspection_id: {}! It is not in the list of inspection_ids! '
        ).format(inspection_id_input))
        return gripper_camera_params

    def _print_mission_info(self, mission):
        ''' A function that prints relevant info based on the provided mission.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        self._logger_info((
            'ArmSensorInspector: Mission Name : {} Number of Inspection Actions: {} Playback Mode: {} Global Params: {}'
        ).format(self._get_mission_name(mission),
                 self._get_num_of_inspection_elements(mission),
                 self._get_playback_mode(mission),
                 self._get_global_parameters(mission)))

    def _set_mission_params(self,
                            mission,
                            mission_name=None,
                            dock_at_the_end=False,
                            stow_in_between=True,
                            joint_move_speed="FAST",
                            travel_speed="FAST",
                            behavior_action="proceed_if_able",
                            behavior_navigation="proceed_if_able",
                            retry_count=1,
                            prompt_duration_secs=10,
                            try_again_delay_secs=60,
                            self_right_attempts=0,
                            moving_object_autonomy_behavior='off'):
        ''' A helper function that set a number of mission params.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - mission_name(string): the desired mission_name
                - dock_at_the_end(str): tells the Robot to dock after completion
                - stow_in_between(boolean): stows the arm between inspection actions
                - joint_move_speed(string): the speed used by the robot to deploy the arm via a joint move
                    - The base settings are:
                        - maximum_velocity = 4.0 rad/s
                        - maximum_acceleration = 50.0 rad/s^2
                    - Choices:
                        - "FAST":  100% base settings
                        - "MEDIUM":66% base settings
                        - "SLOW":  33% base settings
                - travel_speed(string): the speed used by the robot to navigate the map.
                    - The base speeds are:
                        - robot_velocity_max_yaw = 1.13446 rad/s
                        - robot_velocity_max_x = 1.6  m/s
                        - robot_velocity_max_y = 0.5  m/s
                    - Choices:
                        - "FAST":  100% base speed
                        - "MEDIUM":66% base speed
                        - "SLOW":  33% base speed
                - behavior_action(string): the desired failure behavior for inspection actions
                    - "safe_power_off": the robot will sit down and power off. This is the safest option.
                    - "proceed_if_able": the robot will proceed to the next action if able to do so.
                    - "return_to_start_and_terminate": the robot will return to the start, dock and terminate the mission if able to do so. Only available in missions with a dock!
                    - "return_to_start_and_try_again_later": the robot will return to the start and dock. If successful, the robot will try again later after try_again_delay_secs.
                - behavior_navigation(string): the desired failure behavior for navigation
                    - "safe_power_off": the robot will sit down and power off. This is the safest option.
                    - "proceed_if_able": the robot will proceed to the next action if able to do so.
                    - "return_to_start_and_terminate": the robot will return to the start, dock and terminate the mission if able to do so. Only available in missions with a dock!
                    - "return_to_start_and_try_again_later": the robot will return to the start and dock. If successful, the robot will try again later after try_again_delay_secs.
                - retry_count(int): the number of times the robot should try running the mission element
                - prompt_duration_secs(seconds - min 10s): the duration of the prompt for user
                                                           before defaulting to failure behaviors.
                - try_again_delay_secs(seconds- min 60s): the wait time before trying again.
                - moving_object_autonomy_behavior(str): determines the autonomy behavior around moving objects
                    - choices:
                        - "off": no special behavior
                        - "nearby": the robot will slow down and stop for people and moving objects nearby
                        - "nearby_and_ahead": the robot will slow down and stop for people and moving objects that are nearby or which cross the path ahead
        '''
        # Set the mission_name
        if mission_name:
            self._set_mission_name(mission, mission_name)
        # Determine docking behavior at the end of missions
        if dock_at_the_end:
            # Tell Robot to dock after completion
            self._enable_dock_after_completion(mission)
        else:
            # Tell Robot not to dock after completion
            self._disable_dock_after_completion(mission)
        # Determine stowing behavior in between inspection actions
        if stow_in_between:
            # Force stow arm in between inspection actions
            self._enable_stow_arm_in_between_inspection_actions(mission)
        else:
            # Tell Robot not to stow arm in between inspection actions
            self._disable_stow_arm_in_between_inspection_actions(mission)
        # Set the speed for the joint move
        self._set_joint_move_speed(mission, joint_move_speed)
        # Set travel_speed
        self._set_travel_speed(mission, travel_speed)
        # Set failure behaviors
        self._set_failure_behavior(mission, behavior_action,
                                   behavior_navigation, retry_count,
                                   prompt_duration_secs, try_again_delay_secs)
        # Set global mission parameters
        self._set_global_parameters(mission, self_right_attempts)
        # Disable battery monitor
        self._disable_battery_monitor(mission)
        # Ensure shortcut navigation is on
        self._ensure_shortcuts_are_on(mission)
        # Set moving_object_autonomy_behavior
        self._set_moving_object_autonomy_behavior(
            mission, moving_object_autonomy_behavior)

    def _set_mission_name(self, mission, mission_name):
        ''' A function that sets mission_name for a given mission.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - mission_name(string): the desired mission_name
        '''
        mission.mission_name = mission_name
        self._logger_info(
            ("ArmSensorInspector: Completed setting mission name to {} !"
             ).format(mission_name))

    def _set_global_parameters(self, mission, self_right_attempts=0):
        ''' A function that sets global_parameters.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - self_right_attempts(int): attempts to automatically self-rights the robot
                                          if robot experiences a fall.
        '''
        mission.global_parameters.self_right_attempts = self_right_attempts
        self._logger_info((
            "ArmSensorInspector: Completed setting mission global parameters! self_right_attempts = {}"
        ).format(self_right_attempts))

    def _set_failure_behavior(self,
                              mission,
                              behavior_action="proceed_if_able",
                              behavior_navigation="proceed_if_able",
                              retry_count=1,
                              prompt_duration_secs=10,
                              try_again_delay_secs=60):
        ''' A helper function that sets failure behaviors for the robot to handle
            failures during a mission execution.
            - Some of the possible failures that could happen are the following.
                - System Faults:   indicates a hardware or software fault on the robot.
                - Behavior Faults: faults related to behavior commands and issue warnings
                                    if a certain behavior fault will prevent execution of subsequent commands.
                - Service Faults:  third party payloads and services may encounter unexpected issues
                                on hardware or software connected to Spot.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - behavior_action(string): the desired failure behavior for inspection actions
                    - "safe_power_off": the robot will sit down and power off. This is the safest option.
                    - "proceed_if_able": the robot will proceed to the next action if able to do so.
                    - "return_to_start_and_terminate": the robot will return to the start, dock and terminate the mission if able to do so. Only available in missions with a dock!
                    - "return_to_start_and_try_again_later": the robot will return to the start and dock. If successful, the robot will try again later after try_again_delay_secs.
                - behavior_navigation(string): the desired failure behavior for navigation
                    - "safe_power_off": the robot will sit down and power off. This is the safest option.
                    - "proceed_if_able": the robot will proceed to the next action if able to do so.
                    - "return_to_start_and_terminate": the robot will return to the start, dock and terminate the mission if able to do so. Only available in missions with a dock!
                    - "return_to_start_and_try_again_later": the robot will return to the start and dock. If successful, the robot will try again later after try_again_delay_secs.
                - retry_count(int): the number of times the robot should try running the mission element
                - prompt_duration_secs(seconds - min 10s): the duration of the prompt for user
                                                           before defaulting to failure behaviors.
                - try_again_delay_secs(seconds- min 60s): the wait time before trying again.
        '''
        behavior_choices = [
            "safe_power_off", "proceed_if_able",
            "return_to_start_and_terminate",
            "return_to_start_and_try_again_later"
        ]
        # Check the validity of provided behavior
        if behavior_action not in behavior_choices:
            text = " Choose [safe_power_off, proceed_if_able, return_to_start_and_terminate, return_to_start_and_try_again_later] "
            self._logger_error(
                "ArmSensorInspector: " + str(behavior_action) +
                " is an invalid input!" + text +
                "Continuing with the failure behaviors value set at mission recording!"
            )
            return
        if behavior_navigation not in behavior_choices:
            text = " Choose [safe_power_off, proceed_if_able, return_to_start_and_terminate, return_to_start_and_try_again_later] "
            self._logger_error(
                "ArmSensorInspector: " + str(behavior_navigation) +
                " is an invalid input!" + text +
                "Continuing with the failure behaviors value set at mission recording!"
            )
            return
        # Set prompt_duration and try_again_delay in seconds
        prompt_duration = duration_pb2.Duration(seconds=prompt_duration_secs)
        try_again_delay = duration_pb2.Duration(seconds=try_again_delay_secs)
        # Set retry count and prompt duration for the action failure_behavior
        action_failure_behavior = FailureBehavior(
            retry_count=retry_count, prompt_duration=prompt_duration)
        # Determine the action failure behavior requested
        if behavior_action == "safe_power_off":
            action_failure_behavior.safe_power_off.SetInParent()
        elif behavior_action == "proceed_if_able":
            action_failure_behavior.proceed_if_able.SetInParent()
        elif behavior_action == "return_to_start_and_terminate":
            action_failure_behavior.return_to_start_and_terminate.SetInParent()
        elif behavior_action == "return_to_start_and_try_again_later":
            action_failure_behavior.return_to_start_and_try_again_later.try_again_delay.CopyFrom(
                try_again_delay)
        # Set retry count and prompt duration for the navigation failure_behavior
        navigation_failure_behavior = FailureBehavior(
            retry_count=retry_count, prompt_duration=prompt_duration)
        # Determine the navigation failure behavior requested
        if behavior_navigation == "safe_power_off":
            navigation_failure_behavior.safe_power_off.SetInParent()
        elif behavior_navigation == "proceed_if_able":
            navigation_failure_behavior.proceed_if_able.SetInParent()
        elif behavior_navigation == "return_to_start_and_terminate":
            navigation_failure_behavior.return_to_start_and_terminate.SetInParent(
            )
        elif behavior_navigation == "return_to_start_and_try_again_later":
            navigation_failure_behavior.return_to_start_and_try_again_later.try_again_delay.CopyFrom(
                try_again_delay)
        # Set failure_behaviors to mission_elements in the given mission
        for mission_element in mission.elements:
            # Action is what the robot should do at that location. Here, we are setting its failure behavior.
            mission_element.action_failure_behavior.CopyFrom(
                action_failure_behavior)
            # Target is the location the robot should navigate to. Here, we are setting its failure behavior.
            mission_element.target_failure_behavior.CopyFrom(
                navigation_failure_behavior)
        self._logger_info(
            "ArmSensorInspector: Completed setting action and target failure behavior to "
            + str(action_failure_behavior) + " and " +
            str(navigation_failure_behavior) + " !")

    def _set_moving_object_autonomy_behavior(self, mission,
                                             moving_object_autonomy_behavior):
        ''' A helper function that sets the moving object autonomy behavior.
            - Args:
                - moving_object_autonomy_behavior(str): determines the autonomy behavior around moving objects
                    - choices:
                        - "off": no special behavior
                        - "nearby": the robot will slow down and stop for people and moving objects nearby
                        - "nearby_and_ahead": the robot will slow down and stop for people and moving objects that are nearby or which cross the path ahead
        '''
        # Collect all field names for the message Target
        fields = Target().DESCRIPTOR.fields
        field_names = []
        for field in fields:
            field_names.append(field.name)
        # Check if walk_pb2 contains the fields related with moving_object_autonomy_behavior
        if not ("entity_params" in field_names):
            self._logger_warning(
                "ArmSensorInspector: Can't set moving_object_autonomy_behavior to "
                + moving_object_autonomy_behavior +
                " because walks.proto does not have the required fields! Ensure you have the desired bosdyn Python package."
            )
            return
        # Set moving object autonomy behavior to mission_elements in the given mission
        for mission_element in mission.elements:
            # Get the target attribute
            mission_element_target_oneof = getattr(
                mission_element.target,
                mission_element.target.WhichOneof('target'))
            # Set moving object autonomy behavior choices
            moving_object_choices = ["off", "nearby", "nearby_and_ahead"]
            # Check the validity of the provided moving_object_autonomy_behavior
            if moving_object_autonomy_behavior not in moving_object_choices:
                text = " Choose from: " + str(moving_object_choices)
                self._logger_error(
                    str(moving_object_autonomy_behavior) +
                    " is an invalid input!" + text +
                    "Continuing with default moving object behaviors set during map recording!"
                )
            elif moving_object_autonomy_behavior == "off":
                # Turn off moving_object_autonomy_behavior
                mission_element_target_oneof.travel_params.entity_behavior_config.Clear(
                )
                mission_element_target_oneof.travel_params.entity_wait_config.Clear(
                )
                mission_element.target.entity_params.Clear()
            elif moving_object_autonomy_behavior == "nearby" or moving_object_autonomy_behavior == "nearby_and_ahead":
                # Turn on moving_object_autonomy_behavior
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.enable_slowdown = True
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.slowdown_zone.box.size.x = 3.5
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.slowdown_zone.box.size.y = 3
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.slowdown_zone.frame_name = "body"
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.slowdown_zone.frame_name_tform_box.position.x = -0.5
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.slowdown_zone.frame_name_tform_box.position.y = -1.5
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_slowdown_config.slowdown_zone.frame_name_tform_box.rotation.w = 1
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_obstacle_config.enable_entity_obstacles = True
                mission_element_target_oneof.travel_params.entity_behavior_config.entity_obstacle_config.entity_obstacle_radius = 0.75
                mission_element_target_oneof.travel_params.entity_wait_config.enabled.value = True
                mission_element_target_oneof.travel_params.entity_wait_config.start_waiting_after_entities_ahead_time.nanos = 250000000
                mission_element_target_oneof.travel_params.entity_wait_config.entity_near_path_distance.value = 1.25
                mission_element_target_oneof.travel_params.entity_wait_config.close_safety_zone_size.value = 1
                mission_element.target.entity_params.max_wait_time.seconds = 10
                mission_element.target.entity_params.min_time_between_wait_prompts.seconds = 5
                mission_element.target.entity_params.entity_suppression_dist = 10
                if moving_object_autonomy_behavior == "nearby":
                    # Nearby Movers
                    mission_element_target_oneof.travel_params.entity_wait_config.entity_lookahead_distance.value = 0
                elif moving_object_autonomy_behavior == "nearby_and_ahead":
                    # Nearby Movers + Movers Ahead
                    mission_element_target_oneof.travel_params.entity_wait_config.entity_lookahead_distance.value = 8
        self._logger_info(
            "ArmSensorInspector: Completed setting moving_object_autonomy_behavior to "
            + moving_object_autonomy_behavior + " !")

    def _set_gripper_camera_parameters_with_proto(self, mission,
                                                  inspection_id_input,
                                                  gripper_camera_params):
        ''' A helper function that sets the gripper camera parameters using the provided settings.
            If inspection_id_input is provided, this function changes the gripper camera params for
            the inspection action that corresponds with the inspection_id_input.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - inspection_id_input(int): the desired inspection_id
                - gripper_camera_params(gripper_camera_param_pb2.GripperCameraParams): the desired gripper camera params
                                                                                        parsed as GripperCameraParams proto
            Returns:
                - Boolean indicating if the setting gripper camera parameters succeeded
        '''
        # Find the mission element that corresponds to the given inspection id
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                inspection_id = mission_element.name
                # Check if inspection_id_input is not provided
                if inspection_id_input is None:
                    # Now set the cam params for this element using gripper_camera_params input
                    mission_element.action_wrapper.gripper_camera_params.params.CopyFrom(
                        gripper_camera_params)
                    self._logger_info((
                        "ArmSensorInspector: Completed setting gripper camera parameters for inspection ID: {}!"
                    ).format(inspection_id_input))
                # Check if mission element associated with inspection_id is identical to inspection_id_input
                elif inspection_id_input == inspection_id:
                    # Now set the cam params for this element using gripper_camera_params input
                    mission_element.action_wrapper.gripper_camera_params.params.CopyFrom(
                        gripper_camera_params)
                    self._logger_info((
                        "ArmSensorInspector: Completed setting gripper camera parameters for inspection ID: {}!"
                    ).format(inspection_id_input))
                    return True
        # Return false with an error if we did not find the corresponding mission_element for inspection_id_input
        self._logger_error((
            'ArmSensorInspector: Invalid inspection_id: {}! It is not in the list of inspection_ids! '
        ).format(inspection_id_input))
        return False

    def _set_gripper_camera_parameters(self,
                                       mission,
                                       inspection_id_input=None,
                                       resolution=None,
                                       brightness=None,
                                       contrast=None,
                                       gain=None,
                                       saturation=None,
                                       manual_focus=None,
                                       auto_focus=None,
                                       exposure=None,
                                       auto_exposure=None,
                                       hdr_mode=None,
                                       led_mode=None,
                                       led_torch_brightness=None,
                                       gamma=None,
                                       sharpness=None,
                                       white_balance_temperature=None,
                                       white_balance_temperature_auto=None):
        ''' A helper function that sets the gripper camera parameters using the provided settings.
            If inspection_id_input is provided, this function changes the gripper camera params for
            the inspection action that corresponds with the inspection_id_input. If not provided, the
            function applies the given camera params to all inspection actions.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - inspection_id_input(int): the desired inspection_id
                - resolution(string): resolution of the camera
                    - choices: '640x480', '1280x720','1920x1080', '3840x2160', '4096x2160', '4208x3120'
                - brightness(double): brightness value in (0.0 - 1.0)
                - contrast(double):   contrast value in (0.0 - 1.0)
                - gain(double):       gain value in (0.0 - 1.0)
                - saturation(double): saturation value in (0.0 - 1.0)
                - manual_focus(double): manual focus value in (0.0 - 1.0)
                - auto_focus(string): Enable/disable auto-focus
                    - choices: 'on', 'off'
                - exposure(double):   exposure value in (0.0 - 1.0)
                - auto_exposure(string): enable/disable auto-exposure
                    - choices: 'on', 'off'
                - hdr_mode(string):   on-camera high dynamic range (HDR) setting.  manual1-4 modes enable HDR with 1 the minimum HDR setting and 4 the maximum'
                    - choices: 'off','auto','manual1','manual2','manual3','manual4'
                - led_mode(string):   LED mode.
                    - choices:
                        - 'off': off all the time.
                        - 'torch': on all the time.
                        - 'flash': on during snapshots.
                        - 'both': on all the time and at a different brightness for snapshots.
                - led_torch_brightness(double): LED brightness value in (0.0 - 1.0) when led_mode is on all the time
                - gamma(double): Gamma value in (0.0 - 1.0)
                - sharpness(double): Sharpness value in (0.0 - 1.0)
                - white_balance_temperature-auto(string): Enable/disable white-balance-temperature-auto
                    - choices: 'on', 'off'
                - white_balance_temperature'(double): Manual white-balance-temperature value in (0.0 - 1.0)
            '''
        # Find the mission element that corresponds to the given inspection id
        mission_element_for_inspection_id_input = None
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                inspection_id = mission_element.name
                # Check if inspection_id_input is not provided
                if inspection_id_input is None:
                    # Change the gripper camera params for all mission elements related with arm sensor pointing
                    self._set_gripper_camera_parameters_for_mission_element(
                        mission_element, resolution, brightness, contrast,
                        gain, saturation, manual_focus, auto_focus, exposure,
                        auto_exposure, hdr_mode, led_mode,
                        led_torch_brightness, gamma, sharpness,
                        white_balance_temperature,
                        white_balance_temperature_auto)
                # Check if mission element associated with inspection_id is identical to inspection_id_input
                elif inspection_id_input == inspection_id:
                    # Now set the cam params for this element
                    mission_element_for_inspection_id_input = mission_element
                    self._set_gripper_camera_parameters_for_mission_element(
                        mission_element_for_inspection_id_input, resolution,
                        brightness, contrast, gain, saturation, manual_focus,
                        auto_focus, exposure, auto_exposure, hdr_mode,
                        led_mode, led_torch_brightness, gamma, sharpness,
                        white_balance_temperature,
                        white_balance_temperature_auto)
        # Return with an error if we did not find the corresponding mission_element for an
        # inspection_id_input not equal to none
        if not mission_element_for_inspection_id_input and inspection_id_input is not None:
            self._logger_error((
                'ArmSensorInspector: Invalid inspection_id: {}! It is not in the list of inspection_ids! '
            ).format(inspection_id_input))
            return
        # Log status
        self._logger_info(
            "ArmSensorInspector: Completed setting gripper camera parameters!")

    def _set_gripper_camera_parameters_for_mission_element(
            self,
            mission_element,
            resolution=None,
            brightness=None,
            contrast=None,
            gain=None,
            saturation=None,
            manual_focus=None,
            auto_focus=None,
            exposure=None,
            auto_exposure=None,
            hdr_mode=None,
            led_mode=None,
            led_torch_brightness=None,
            gamma=None,
            sharpness=None,
            white_balance_temperature=None,
            white_balance_temperature_auto=None):
        ''' A helper function that sets the gripper camera parameters using the provided settings
            a given mission element.
            - Args:
                - mission_element(walks_pb2.Element): the desired mission_element
                - resolution(string): resolution of the camera
                    - choices: '640x480', '1280x720','1920x1080', '3840x2160', '4096x2160', '4208x3120'
                - brightness(double): brightness value in (0.0 - 1.0)
                - contrast(double):   contrast value in (0.0 - 1.0)
                - gain(double):       gain value in (0.0 - 1.0)
                - saturation(double): saturation value in (0.0 - 1.0)
                - manual_focus(double): manual focus value in (0.0 - 1.0)
                - auto_focus(string): Enable/disable auto-focus
                    - choices: 'on', 'off'
                - exposure(double):   exposure value in (0.0 - 1.0)
                - auto_exposure(string): enable/disable auto-exposure
                    - choices: 'on', 'off'
                - hdr_mode(string):   on-camera high dynamic range (HDR) setting.  manual1-4 modes enable HDR with 1 the minimum HDR setting and 4 the maximum'
                    - choices: 'off','auto','manual1','manual2','manual3','manual4'
                - led_mode(string):   LED mode.
                    - choices:
                        - 'off': off all the time.
                        - 'torch': on all the time.
                        - 'flash': on during snapshots.
                        - 'both': on all the time and at a different brightness for snapshots.
                - led_torch_brightness(double): LED brightness value in (0.0 - 1.0) when led_mode is on all the time
                - gamma(double): Gamma value in (0.0 - 1.0)
                - sharpness(double): Sharpness value in (0.0 - 1.0)
                - white_balance_temperature-auto(string): Enable/disable white-balance-temperature-auto
                    - choices: 'on', 'off'
                - white_balance_temperature'(double): Manual white-balance-temperature value in (0.0 - 1.0)
            '''
        # For this specific inspection ID set the following GripperCameraParams if they are provided
        # Set the resolution
        if resolution is not None:
            if resolution in ('640x480', '1280x720', '1920x1080', '3840x2160',
                              '4096x2160', '4208x3120'):
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
                mission_element.action_wrapper.gripper_camera_params.params.camera_mode = camera_mode
            else:
                text = " Choose ['640x480', '1280x720', '1920x1080', '3840x2160', '4096x2160','4208x3120'] "
                self._logger_error(
                    "ArmSensorInspector: " + str(led_mode) +
                    " is an invalid input!" + text +
                    "Continuing with the led mode value set at mission recording!"
                )
        # Set the brightness
        if brightness is not None:
            mission_element.action_wrapper.gripper_camera_params.params.brightness.value = brightness
        # Set the contrast
        if contrast is not None:
            mission_element.action_wrapper.gripper_camera_params.params.contrast.value = contrast
        # Set the saturation
        if saturation is not None:
            mission_element.action_wrapper.gripper_camera_params.params.saturation.value = saturation
        # Set the gain
        if gain is not None:
            mission_element.action_wrapper.gripper_camera_params.params.gain.value = gain
        #  Check manual_focus and auto_focus restrictions
        if manual_focus is not None and auto_focus and auto_focus == 'on':
            self._logger_warning(
                'ArmSensorInspector: Can not specify both a manual focus value and enable auto-focus. Setting auto_focus = off now'
            )
            # Set  auto_focus off
            mission_element.action_wrapper.gripper_camera_params.params.focus_auto.value = False
        # Set the manual_focus
        if manual_focus:
            mission_element.action_wrapper.gripper_camera_params.params.focus_absolute.value = manual_focus
            # Set  auto_focus off because we can not specify both a manual focus value and enable auto-focus
            mission_element.action_wrapper.gripper_camera_params.params.focus_auto.value = False
        # Set  auto_focus
        if auto_focus is not None:
            if auto_focus in ('on', 'off'):
                auto_focus_enabled = (auto_focus == 'on')
                mission_element.action_wrapper.gripper_camera_params.params.focus_auto.value = auto_focus_enabled
            else:
                text = " Choose ['on','off'] "
                self._logger_error(
                    "ArmSensorInspector: " + str(auto_focus) +
                    " is an invalid input!" + text +
                    "Continuing with the auto focus value set at mission recording!"
                )
        if exposure is not None and auto_exposure and auto_exposure == 'on':
            self._logger_warning(
                'ArmSensorInspector: Can not specify both manual exposure &enable auto-exposure. Setting auto_exposure = off now'
            )
            # Set  auto_exposure off
            mission_element.action_wrapper.gripper_camera_params.params.exposure_auto.value = False
        if exposure is not None:
            # Set the exposure
            mission_element.action_wrapper.gripper_camera_params.params.exposure_absolute.value = exposure
            # Set auto_exposure off because we can not specify both manual exposure &enable auto-exposure
            mission_element.action_wrapper.gripper_camera_params.params.exposure_auto.value = False
        # Set  auto_exposure
        if auto_exposure:
            if auto_exposure in ('on', 'off'):
                auto_exposure_enabled = (auto_exposure == 'on')
                mission_element.action_wrapper.gripper_camera_params.params.exposure_auto.value = auto_exposure_enabled
            else:
                text = " Choose ['on','off'] "
                self._logger_error(
                    "ArmSensorInspector: " + str(auto_exposure) +
                    " is an invalid input!" + text +
                    "Continuing with the auto exposure value set at mission recording!"
                )
        # Set the hdr mode
        if hdr_mode is not None:
            if hdr_mode in ('off', 'auto', 'manual1', 'manual2', 'manual3',
                            'manual4'):
                if hdr_mode == 'off':
                    hdr = gripper_camera_param_pb2.HDR_OFF
                elif hdr_mode == 'auto':
                    hdr = gripper_camera_param_pb2.HDR_AUTO
                elif hdr_mode == 'manual1':
                    hdr = gripper_camera_param_pb2.HDR_MANUAL_1
                elif hdr_mode == 'manual2':
                    hdr = gripper_camera_param_pb2.HDR_MANUAL_2
                elif hdr_mode == 'manual3':
                    hdr = gripper_camera_param_pb2.HDR_MANUAL_3
                elif hdr_mode == 'manual4':
                    hdr = gripper_camera_param_pb2.HDR_MANUAL_4
                mission_element.action_wrapper.gripper_camera_params.params.hdr = hdr
            else:
                text = " Choose ['off', 'auto', 'manual1', 'manual2', 'manual3', 'manual4'] "
                self._logger_error(
                    "ArmSensorInspector: " + str(hdr_mode) +
                    " is an invalid input!" + text +
                    "Continuing with the hdr mode value set at mission recording!"
                )
        # Set the led_mode
        if led_mode is not None:
            if led_mode in ('off', 'torch', 'flash', 'both'):
                if led_mode == 'off':
                    led = gripper_camera_param_pb2.GripperCameraParams.LED_MODE_OFF
                elif led_mode == 'torch':
                    led = gripper_camera_param_pb2.GripperCameraParams.LED_MODE_TORCH
                elif led_mode == 'flash':
                    led = gripper_camera_param_pb2.GripperCameraParams.LED_MODE_FLASH
                elif led_mode == 'both':
                    led = gripper_camera_param_pb2.GripperCameraParams.LED_MODE_FLASH_AND_TORCH
                mission_element.action_wrapper.gripper_camera_params.params.led_mode = led
            else:
                text = " Choose ['off', 'torch', 'flash', 'both'] "
                self._logger_error(
                    "ArmSensorInspector: " + str(led_mode) +
                    " is an invalid input!" + text +
                    "Continuing with the led mode value set at mission recording!"
                )
        # Set the led_torch_brightness
        if led_torch_brightness is not None:
            mission_element.action_wrapper.gripper_camera_params.params.led_torch_brightness.value = led_torch_brightness
        # Set the gamma
        if gamma is not None:
            mission_element.action_wrapper.gripper_camera_params.params.gamma.value = gamma
        # Set the sharpness
        if sharpness is not None:
            mission_element.action_wrapper.gripper_camera_params.params.sharpness.value = sharpness
        # Set the white_balance_temperature
        if white_balance_temperature is not None and white_balance_temperature_auto and white_balance_temperature_auto == 'on':
            self._logger_warning(
                'ArmSensorInspector: cannot specify both a manual white_balance_temperature value and enable white_balance_temperature_auto. Setting white_balance_temperature_auto = off now'
            )
            # Set  white_balance_temperature_auto off
            mission_element.action_wrapper.gripper_camera_params.params.white_balance_temperature_auto.value = False
        # Set the white_balance_temperature
        if white_balance_temperature is not None:
            mission_element.action_wrapper.gripper_camera_params.params.white_balance_temperature.value = white_balance_temperature
            mission_element.action_wrapper.gripper_camera_params.params.white_balance_temperature_auto.value = False

        if white_balance_temperature_auto:
            if white_balance_temperature_auto in ('on', 'off'):
                white_balance_temperature_auto_enabled = (
                    white_balance_temperature_auto == 'on')
                mission_element.action_wrapper.gripper_camera_params.params.white_balance_temperature_auto.value = white_balance_temperature_auto_enabled
            else:
                text = " Choose ['on','off'] "
                self._logger_error(
                    "ArmSensorInspector: " +
                    str(white_balance_temperature_auto) +
                    " is an invalid input!" + text +
                    "Continuing with the white_balance_temperature_auto value set at mission recording!"
                )

    def _set_travel_speed(self, mission, travel_speed="MEDIUM"):
        ''' A helper function that sets travel parameters for navigation.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - travel_speed(string): the speed used by the robot to navigate the map.
                    - The base speeds are:
                        - robot_velocity_max_yaw = 1.13446 rad/s
                        - robot_velocity_max_x = 1.6  m/s
                        - robot_velocity_max_y = 0.5  m/s
                    - Choices:
                        - "FAST":  100% base speed
                        - "MEDIUM":66% base speed
                        - "SLOW":  33% base speed
        '''
        # Base robot travel speeds
        robot_velocity_max_yaw = 1.13446  # rad/s
        robot_velocity_max_x = 2.0  # m/s
        robot_velocity_max_y = 0.5  # m/s
        # Velocity limits for navigation (optional)
        if travel_speed == "FAST":
            nav_velocity_max_yaw = robot_velocity_max_yaw
            nav_velocity_max_x = robot_velocity_max_x
            nav_velocity_max_y = robot_velocity_max_y
            self._logger_info(
                "ArmSensorInspector: Travel speed is set to FAST!")
        elif travel_speed == "MEDIUM":
            nav_velocity_max_yaw = 0.66 * robot_velocity_max_yaw
            nav_velocity_max_x = 0.66 * robot_velocity_max_x
            nav_velocity_max_y = 0.66 * robot_velocity_max_y
            self._logger_info(
                "ArmSensorInspector: Travel speed is set to MEDIUM!")
        elif travel_speed == "SLOW":
            nav_velocity_max_yaw = 0.33 * robot_velocity_max_yaw
            nav_velocity_max_x = 0.33 * robot_velocity_max_x
            nav_velocity_max_y = 0.33 * robot_velocity_max_y
            self._logger_info(
                "ArmSensorInspector: Travel speed is set to SLOW!")
        else:
            self._logger_error(
                "ArmSensorInspector: " + str(travel_speed) +
                " is an invalid input! Choose ['FAST', 'MEDIUM', 'SLOW'] Continuing with the travel speed value set at mission recording!"
            )
            return
        nav_velocity_limits = geometry_pb2.SE2VelocityLimit(
            max_vel=geometry_pb2.SE2Velocity(linear=geometry_pb2.Vec2(
                x=nav_velocity_max_x, y=nav_velocity_max_y),
                                             angular=nav_velocity_max_yaw),
            min_vel=geometry_pb2.SE2Velocity(linear=geometry_pb2.Vec2(
                x=-nav_velocity_max_x, y=-nav_velocity_max_y),
                                             angular=-nav_velocity_max_yaw))
        # Apply the nav_velocity_limits to mission elements
        for mission_element in mission.elements:
            if (mission_element.target.HasField("navigate_route")):
                mission_element.target.navigate_route.travel_params.velocity_limit.CopyFrom(
                    nav_velocity_limits)
            else:
                mission_element.target.navigate_to.travel_params.velocity_limit.CopyFrom(
                    nav_velocity_limits)
        # Apply the nav_velocity_limits to mission docks
        for dock in mission.docks:
            if (dock.target_prep_pose.HasField("navigate_route")):
                dock.target_prep_pose.navigate_route.travel_params.velocity_limit.CopyFrom(
                    nav_velocity_limits)
            else:
                dock.target_prep_pose.navigate_to.travel_params.velocity_limit.CopyFrom(
                    nav_velocity_limits)

    def _set_joint_move_speed(self, mission, joint_move_speed="MEDIUM"):
        ''' A helper function that sets the speed for the arm joint move.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - joint_move_speed(string): the speed used by the robot to deploy the arm via a joint move
                    - The base settings are:
                        - maximum_velocity = 4.0 rad/s
                        - maximum_acceleration = 50.0 rad/s^2
                    - Choices:
                        - "FAST":  100% base settings
                        - "MEDIUM":66% base settings
                        - "SLOW":  33% base settings
            '''
        # Velocity limits for arm movements
        if joint_move_speed == "FAST":
            maximum_velocity = 4.0  # rad/s
            maximum_acceleration = 50.0  #rad/s^2
            self._logger_info(
                "ArmSensorInspector: Joint move speed is set to FAST!")
        elif joint_move_speed == "MEDIUM":
            maximum_velocity = 2.64  # rad/s
            maximum_acceleration = 33.0  #rad/s^2
            self._logger_info(
                "ArmSensorInspector: Joint move speed is set to MEDIUM!")
        elif joint_move_speed == "SLOW":
            maximum_velocity = 1.32  # rad/s
            maximum_acceleration = 16.5  #rad/s^2
            self._logger_info(
                "ArmSensorInspector: Joint move speed is set to SLOW!")
        else:
            self._logger_error(
                "ArmSensorInspector: " + str(joint_move_speed) +
                " is an invalid input! Choose ['FAST', 'MEDIUM', 'SLOW'] Continuing with the joint move speed value set at mission recording!"
            )
            return
        # Using the above setting, set arm velocity and accelerations
        self._set_max_arm_velocity_and_acceleration(mission, maximum_velocity,
                                                    maximum_acceleration)

    def _set_max_arm_velocity_and_acceleration(self,
                                               mission,
                                               maximum_velocity=2.5,
                                               maximum_acceleration=15):
        ''' A helper function that sets the maximum_velocity and maximum_acceleration for the arm joint move.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - maximum_velocity(double): the maximum velocity in rad/s that any joint is allowed to achieve.
                                          If this field is not set, the default value 2.5  will be used.
                - maximum_acceleration(double): the maximum acceleration in rad/s^2 that any joint is allowed to
                                              achieve. If this field is not set, the default value 15 will be used
        '''
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                mission_element.action_wrapper.arm_sensor_pointing.joint_trajectory.maximum_velocity.value = maximum_velocity
                mission_element.action_wrapper.arm_sensor_pointing.joint_trajectory.maximum_acceleration.value = maximum_acceleration
        self._logger_info(
            "ArmSensorInspector: Completed '_set_max_arm_velocity_and_acceleration'!"
        )

    def _enable_stow_arm_in_between_inspection_actions(self, mission):
        ''' A helper function that forces the arm to stow in between inspection actions.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                mission_element.action_wrapper.arm_sensor_pointing.force_stow_override = True
        self._logger_info(
            "ArmSensorInspector: Completed '_enable_stow_arm_in_between_inspection_actions'!"
        )

    def _disable_stow_arm_in_between_inspection_actions(self, mission):
        ''' A helper function that forces the arm to stow in between inspection actions.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        for mission_element in mission.elements:
            if (mission_element.action_wrapper.HasField("arm_sensor_pointing")
                ):
                mission_element.action_wrapper.arm_sensor_pointing.force_stow_override = False
        self._logger_info(
            "ArmSensorInspector: Completed '_disable_stow_arm_in_between_inspection_actions'!"
        )

    def _disable_battery_monitor(self, mission):
        ''' A helper function that disables battery monitor before starting mission execution.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        for mission_element in mission.elements:
            mission_element.battery_monitor.CopyFrom(
                BatteryMonitor(battery_start_threshold=0,
                               battery_stop_threshold=0))
        self._logger_info(
            "ArmSensorInspector: Completed '_disable_battery_monitor'!")

    def _enable_battery_monitor(self,
                                mission,
                                battery_start_threshold=60,
                                battery_stop_threshold=10):
        ''' A helper function that enables battery monitor before starting mission execution given
            the thresholds for start and stop.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - battery_start_threshold(double): the robot will continue charging on the dock
                                                until the robot battery is above this threshold
                - battery_stop_threshold(double): the robot will stop and return to the dock
                                                if the robot battery is below this threshold
                                                (Note: this only works in continuous missions at this time.)
        '''
        for mission_element in mission.elements:
            mission_element.battery_monitor.CopyFrom(
                BatteryMonitor(battery_start_threshold=battery_start_threshold,
                               battery_stop_threshold=battery_stop_threshold))
        self._logger_info(
            "ArmSensorInspector: Completed '_enable_battery_monitor '!")

    def _disable_dock_after_completion(self, mission):
        ''' A helper function that tells the robot to not dock after completion.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        mission.playback_mode.once.skip_docking_after_completion = True
        self._logger_info(
            "ArmSensorInspector: Completed '_disable_dock_after_completion'!")

    def _enable_dock_after_completion(self, mission):
        ''' A helper function that tells the robot to dock after completion.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        mission.playback_mode.once.skip_docking_after_completion = False
        self._logger_info(
            "ArmSensorInspector: Completed '_enable_dock_after_completion '!")

    def _set_playback_mode_once(self, mission):
        ''' A helper function that sets the autowalk playback_mode to once.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        mission.playback_mode.once.SetInParent()
        self._logger_info(
            "ArmSensorInspector: Completed '_set_playback_mode_once'!")

    def _set_playback_mode_periodic(self, mission, inspection_interval,
                                    number_of_cycles):
        ''' A function that sets the autowalk playback_mode to periodic.
            Mission runs periodically every given interval for the given number of cycles.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
                - inspection_interval(double): the periodicity of the mission playback in minutes
                - number_of_cycles(int) : the frequency of the inspection in number of cycles
        '''
        interval_seconds = int(inspection_interval * 60)
        duration = duration_pb2.Duration(seconds=interval_seconds // 1,
                                         nanos=int(
                                             (interval_seconds % 1) * 1e9))
        mission.playback_mode.periodic.interval.CopyFrom(duration)
        mission.playback_mode.periodic.repetitions = number_of_cycles
        self._logger_info(
            "ArmSensorInspector: Completed '_set_playback_mode_periodic'!")

    def _set_playback_mode_continuous(self, mission):
        ''' A helper function that sets the autowalk playback_mode to continuous.
            Mission runs continuously, only stopping when it needs to.
            - Args:
                - mission(walks_pb2.Walk): a mission input to be executed on the robot
        '''
        mission.playback_mode.continuous.SetInParent()
        self._logger_info(
            "ArmSensorInspector: Completed '_set_playback_mode_continuous'!")

    def _ensure_robot_is_localized(self):
        ''' A helper function that localizes robot to the uploaded graph if not localized already.
            Make sure the robot is in front of the dock or other fiducials within the map.
            Typically done to provide the initial localization.
            - Returns:
                - Boolean indicating if the robot is localized to the uploaded map
        '''
        localization_state = self._graph_nav_client.get_localization_state()
        # Return True if robot is already localized
        if localization_state.localization.waypoint_id:
            self._logger_info(
                'ArmSensorInspector: the robot is localized already!')
            self._initial_guess_localization = localization_state.localization
            return True
        # Localize the robot since it is not already localized
        self._logger_info(
            'ArmSensorInspector: the robot is not localized to the uploaded graph. Localizing now!'
        )
        localization = nav_pb2.Localization()
        self._graph_nav_client.set_localization(
            initial_guess_localization=localization)
        self._logger_info("ArmSensorInspector: the robot is localized!")
        self._initial_guess_localization = self._graph_nav_client.get_localization_state(
        ).localization
        return True

    def _ensure_shortcuts_are_on(self, mission):
        ''' A helper function that turn shortcut navigation on for mission elements
            and docking elements.
        '''
        for dock in mission.docks:
            if dock.target_prep_pose.HasField("navigate_route"):
                waypoint_ids = dock.target_prep_pose.navigate_route.route.waypoint_id
                # Check if waypoint_ids are not empty
                if waypoint_ids:
                    destination_waypoint_id = waypoint_ids[-1]
                    dock.target_prep_pose.navigate_to.travel_params.CopyFrom(
                        dock.target_prep_pose.navigate_route.travel_params)
                    dock.target_prep_pose.navigate_to.destination_waypoint_id = destination_waypoint_id

        for mission_element in mission.elements:
            if mission_element.target.HasField("navigate_route"):
                waypoint_ids = mission_element.target.navigate_route.route.waypoint_id
                # Check if waypoint_ids are not empty
                if waypoint_ids:
                    destination_waypoint_id = waypoint_ids[-1]
                    mission_element.target.navigate_to.travel_params.CopyFrom(
                        mission_element.target.navigate_route.travel_params)
                    mission_element.target.navigate_to.destination_waypoint_id = destination_waypoint_id

        self._logger_info(
            "ArmSensorInspector: shortcuts are on for navigation!")

    def _ensure_motor_power_is_on(self):
        ''' A helper function that powers robot motors on if not powered on already.
            - Returns:
                - Boolean indicating if the motors are on
        '''
        power_state = self._robot_state_client.get_robot_state().power_state
        is_powered_on = (
            power_state.motor_power_state == power_state.MOTOR_POWER_STATE_ON)
        if is_powered_on:
            self._logger_info(
                'ArmSensorInspector: the robot motors are on already!')
            return True
        if not is_powered_on:
            self._logger_info(
                'ArmSensorInspector: the robot motors are off! Turning robot motors on now!'
            )
            # Power on the robot up before proceeding with mission execution
            power_on_motors(self._power_client)
            motors_on = False
            # Wait until motors are on within the feedback_end_time
            fdbk_end_time = 60
            feedback_end_time = time.time() + fdbk_end_time
            while (time.time() < feedback_end_time) or not motors_on:
                future = self._robot_state_client.get_robot_state_async()
                state_response = future.result(
                    timeout=10
                )  # 10 second timeout for waiting for the state response.
                # Set motors_on state
                motors_on = (state_response.power_state.motor_power_state ==
                             robot_state_pb2.PowerState.MOTOR_POWER_STATE_ON)
                if motors_on:
                    self._logger_info(
                        'ArmSensorInspector: the robot motors are on!')
                    return True
                else:
                    # Motors are not yet fully powered on.
                    time.sleep(.25)
            self._logger_error(
                'ArmSensorInspector: Turn motor power on command timeout!')
            return False

    def _log_command_status(self, command_name, status):
        ''' A helper function that logs the status of a given command.
            - Args:
                - command_name(string): the name of the command
                - status(boolean): indicates if the given command is successful
        '''
        if not status:
            self._logger_info(
                ('ArmSensorInspector: Failed to run {}').format(command_name))
        else:
            self._logger_info(
                ('ArmSensorInspector: Completed {} ').format(command_name))

    def _logger_info(self, text_message):
        ''' A helper function that logs an info message to robot logs and prints on terminal.
            - Args:
                - text_message(string): the desired info message
        '''
        self._log_text(text_message, severity='info')

    def _logger_warning(self, text_message):
        ''' A helper function that logs a warning message to robot logs and prints on terminal.
            - Args:
                - text_message(string): the desired warning message
        '''
        self._log_text(text_message, severity='warning')

    def _logger_error(self, text_message):
        ''' A helper function that logs an error message to robot logs and prints on terminal.
            - Args:
                - text_message(string): the desired error message
        '''
        self._log_text(text_message, severity='error')

    def _log_text(self, text_message, severity='info'):
        ''' A helper function that logs a text message to robot logs and prints on terminal.
            - Args:
                - text_message(string): the desired text message
                - severity(string): the severity of the message
                    - Choices = ["info", "warning", "warning"]
        '''
        # Add text message to txt_msg_proto
        txt_msg_proto = data_buffer_protos.TextMessage(
            message=text_message,
            timestamp=self._robot.time_sync.robot_timestamp_from_local_secs(
                time.time()))
        # Log txt_msg_proto to _data_buffer_client
        self._data_buffer_client.add_text_messages([txt_msg_proto])
        # Print text message based on severity
        if severity == 'info':
            self._robot.logger.info(text_message)
        elif severity == 'warning':
            self._robot.logger.warning(text_message)
        elif severity == 'error':
            self._robot.logger.error(text_message)
        else:
            self._robot.logger.info(text_message)

    def _stow_arm(self):
        ''' A helper function that stows the arm.
            - Returns:
                - Boolean indicating if inspection is successful
        '''
        state = self._robot_state_client.get_robot_state()
        # return if already stowed
        if state.manipulator_state.stow_state == ManipulatorState.STOWSTATE_STOWED:
            self._logger_info("ArmSensorInspector: Arm is already stowed!")
            return
        stow = RobotCommandBuilder.arm_stow_command()
        close_and_stow = RobotCommandBuilder.claw_gripper_close_command(stow)
        self._robot_command_client.robot_command(close_and_stow)

        # Wait until the arm arrives at the goal within the feedback_end_time
        fdbk_end_time = 10
        feedback_end_time = time.time() + fdbk_end_time
        while (time.time() < feedback_end_time):
            state = self._robot_state_client.get_robot_state()
            if state.manipulator_state.stow_state != ManipulatorState.STOWSTATE_STOWED:
                self._logger_info("ArmSensorInspector: Arm is stowed!")
                return True
            time.sleep(0.1)
        self._logger_info(
            "ArmSensorInspector: _stow_arm command timeout exceeded!")
        return False
