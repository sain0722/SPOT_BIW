import sys
import random
import vtk
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

# 지정된 waypoints
waypoints = {
    'waypoint_1': (20, 20, 0),
    'waypoint_2': (20, 40, 0),
    'waypoint_3': (20, 60, 0),
    'waiting': (20, 10, 0),
    'docking_station': (10, 10, 0)
}

# Waypoint 순서 (inspection 추가)
waypoint_order = ['waypoint_1', 'inspection', 'waypoint_2', 'inspection', 'waypoint_3', 'inspection', 'waiting',
                  'docking_station']


# 가짜 데이터 생성 함수
def generate_fake_robot_state():
    # 가짜 위치 데이터 생성
    position = (random.uniform(0, 100), random.uniform(0, 100), 0)
    return position


def generate_fake_local_grid():
    # 가짜 로컬 그리드 데이터 생성
    num_points = 100
    points = vtk.vtkPoints()
    for i in range(num_points):
        x, y = random.uniform(0, 100), random.uniform(0, 100)
        z = 0
        points.InsertNextPoint(x, y, z)

    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)
    return polydata


class DataThread(QThread):
    location_update = Signal(float, float, float, str)
    status_update = Signal(str)
    battery_update = Signal(int)

    def __init__(self):
        super().__init__()
        self.current_waypoint_index = 0
        self.battery_level = 100  # 초기 배터리 상태
        self.docking = False

    def run(self):
        while True:
            # 배터리 상태 업데이트
            self.battery_level -= random.randint(1, 5)
            if self.battery_level < 0:
                self.battery_level = 100  # 배터리 충전 시뮬레이션
            self.battery_update.emit(self.battery_level)

            # 배터리 상태에 따른 위치 업데이트
            if self.battery_level <= 20:
                waypoint_name = 'docking_station'
                self.docking = True
                self.status_update.emit('도킹 중...')
            else:
                if self.docking:
                    # 배터리가 20% 이상으로 충전되었으면 docking 상태 해제
                    self.docking = False
                    self.current_waypoint_index = 0
                waypoint_name = waypoint_order[self.current_waypoint_index]

            if waypoint_name == 'inspection':
                # Inspection 중임을 알리기 위해 특별한 신호를 보냄
                self.location_update.emit(None, None, None, 'inspection')
                self.status_update.emit('검사 중...')
            else:
                new_x, new_y, new_z = waypoints[waypoint_name]
                self.location_update.emit(new_x, new_y, new_z, waypoint_name)
                self.status_update.emit('이동 중...')

            if not self.docking:
                self.current_waypoint_index += 1
                if self.current_waypoint_index >= len(waypoint_order) - 1:  # docking_station은 제외
                    self.current_waypoint_index = 0

            self.msleep(2000)  # 2초마다 업데이트


class MainWindow(QMainWindow):
    def __init__(self):
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
        self.camera.SetViewUp(0, 1, 0)  # 카메라의 view-up 벡터 설정
        self.camera.SetPosition(50, 50, 150)  # 카메라의 위치 설정
        self.camera.SetFocalPoint(50, 50, 0)  # 카메라의 초점 설정

        # Set up the time-based event callbacks for each vtk actor to be visualized.
        self.robot_actor = self.create_robot_actor()
        self.renderer.AddActor(self.robot_actor)

        self.local_grid_actor = self.create_local_grid_actor()
        self.renderer.AddActor(self.local_grid_actor)

        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

        # Initialize the render windows and set the timed callbacks.
        self.iren.Initialize()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)  # 1초마다 업데이트

        # self.data_thread = DataThread()
        # self.data_thread.location_update.connect(self.update_robot_position)
        # self.data_thread.status_update.connect(self.update_status)
        # self.data_thread.battery_update.connect(self.update_battery)
        # self.data_thread.start()

    def create_robot_actor(self):
        # 로봇을 나타내는 큐브 생성
        cube = vtk.vtkCubeSource()
        cube.SetXLength(2)
        cube.SetYLength(2)
        cube.SetZLength(2)

        # Mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())

        # Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0, 1, 0)  # 녹색

        return actor

    def create_local_grid_actor(self):
        # 가짜 로컬 그리드 데이터 생성
        polydata = generate_fake_local_grid()

        # Mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)

        # Actor
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        return actor

    def update_robot_position(self, x, y, z, waypoint_name):
        if waypoint_name == 'inspection':
            self.robot_actor.GetProperty().SetColor(1, 0, 0)  # 빨간색 (검사 중)
        else:
            self.robot_actor.GetProperty().SetColor(0, 1, 0)  # 녹색 (이동 중)

        if x is not None and y is not None and z is not None:
            self.robot_actor.SetPosition(x, y, z)

        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def update_status(self, status):
        self.status_label.setText(f'상태: {status}')

    def update_battery(self, battery_level):
        self.setWindowTitle(f"Spot Simulation - Battery: {battery_level}%")

    def update_data(self):
        # 가짜 로봇 상태 업데이트
        position = generate_fake_robot_state()
        self.update_robot_position(*position, '이동 중')

        # 가짜 로컬 그리드 데이터 업데이트
        polydata = generate_fake_local_grid()
        self.local_grid_actor.GetMapper().SetInputData(polydata)
        self.vtk_widget.GetRenderWindow().Render()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
