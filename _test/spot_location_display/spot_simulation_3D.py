import sys
import argparse
import vtk
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import QTimer
import bosdyn.client
import bosdyn.client.util
from bosdyn.client.robot_state import RobotStateClient
from bosdyn.client.local_grid import LocalGridClient
from bosdyn.client.world_object import WorldObjectClient
from bosdyn.client.image import ImageClient
from visualization_utils import (add_numpy_to_vtk_object, get_default_color_map, get_vtk_cube_source,
                                 get_vtk_polydata_from_numpy, make_spot_vtk_hexahedron, se3pose_proto_to_vtk_tf)
from bosdyn.api import world_object_pb2
from bosdyn.client.frame_helpers import *
from vtk.util import numpy_support

# Import additional required modules
from spot_sdk_example import (WorldObjectTimedCallbackEvent, RobotStateTimedCallbackEvent,
                              ImageServiceTimedCallbackEvent,
                              LocalGridTimedCallbackEvent)


class MainWindow(QMainWindow):
    def __init__(self, robot_state_client, local_grid_client, world_object_client, image_service_client, options):
        super().__init__()

        self.setWindowTitle("Spot SDK Visualization")
        self.setGeometry(100, 100, 1280, 720)

        # Create VTK widget
        self.vtk_widget = QVTKRenderWindowInteractor(self)

        # Status label
        self.status_label = QLabel('상태: 대기 중', self)
        self.status_label.setAlignment(Qt.AlignCenter)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.vtk_widget)
        layout.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Set up VTK renderer and interactor
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.05, 0.1, 0.15)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()

        # Create the renderer and camera.
        self.camera = self.renderer.GetActiveCamera()
        self.camera.SetViewUp(0, 0, 1)
        self.camera.SetPosition(0, 0, 5)

        # Set up the time-based event callbacks for each vtk actor to be visualized.
        self.robot_state_timer = RobotStateTimedCallbackEvent(robot_state_client)
        robot_state_actor = self.robot_state_timer.get_actor()
        self.renderer.AddActor(robot_state_actor)

        self.local_grid_timer = LocalGridTimedCallbackEvent(local_grid_client, robot_state_client, options.local_grid)
        grid_actors = self.local_grid_timer.get_actors()
        for actor in grid_actors:
            self.renderer.AddActor(actor)

        self.world_object_timer = WorldObjectTimedCallbackEvent(world_object_client)
        world_object_actors = self.world_object_timer.get_actors()
        for actor in world_object_actors:
            self.renderer.AddActor(actor)

        if robot_state_client.has_arm() and options.show_hand_depth:
            self.image_service_timer = ImageServiceTimedCallbackEvent(image_service_client, ['hand_depth'])
            image_service_actor = self.image_service_timer.get_actor()
            self.renderer.AddActor(image_service_actor)

        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

        # Initialize the render windows and set the timed callbacks.
        self.iren.Initialize()
        self.iren.AddObserver(vtk.vtkCommand.TimerEvent, self.robot_state_timer.update_state_actor)
        self.iren.AddObserver(vtk.vtkCommand.TimerEvent, self.local_grid_timer.update_local_grid_actors)
        self.iren.AddObserver(vtk.vtkCommand.TimerEvent, self.world_object_timer.update_world_object_actor)
        if robot_state_client.has_arm() and options.show_hand_depth:
            self.iren.AddObserver(vtk.vtkCommand.TimerEvent, self.image_service_timer.update_image_actor)

        self.timer_id = self.iren.CreateRepeatingTimer(100)

    def closeEvent(self, event):
        self.iren.DestroyTimer(self.timer_id)
        event.accept()


def main():
    """Main rendering loop for the API streaming visualizer."""
    # Set up the robot.
    parser = argparse.ArgumentParser()
    bosdyn.client.util.add_base_arguments(parser)
    parser.add_argument('--local-grid', choices=['no-step', 'obstacle-distance', 'terrain'],
                        help='Which local grid to visualize', default=['terrain'], action='append')
    parser.add_argument('--show-hand-depth',
                        help='Draw the hand depth data as a point cloud (requires SpotArm)',
                        action='store_true')
    options = parser.parse_args()
    sdk = bosdyn.client.create_standard_sdk('SpotViz')
    robot = sdk.create_robot(options.hostname)
    bosdyn.client.util.authenticate(robot)
    robot.time_sync.wait_for_sync()

    # Set up the clients for getting Spot's perception scene.
    local_grid_client = robot.ensure_client(LocalGridClient.default_service_name)
    robot_state_client = robot.ensure_client(RobotStateClient.default_service_name)
    world_object_client = robot.ensure_client(WorldObjectClient.default_service_name)
    image_service_client = robot.ensure_client(ImageClient.default_service_name)

    app = QApplication(sys.argv)
    window = MainWindow(robot_state_client, local_grid_client, world_object_client, image_service_client, options)
    window.show()
    app.exec_()


if __name__ == '__main__':
    if not main():
        sys.exit(1)
