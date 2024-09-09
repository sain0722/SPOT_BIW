import json
import os
from copy import deepcopy

import cv2
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, \
    QListWidget, QGraphicsScene, QGraphicsPixmapItem, QStackedWidget, QFormLayout, QLineEdit, \
    QComboBox, QSpinBox, QCheckBox, QDoubleSpinBox, QListView, QFileDialog, QScrollArea, QMessageBox, QDialog
from PySide6.QtGui import QPixmap

import DefineGlobal
from main_operator import MainOperator
from biw_utils import util_functions, rule_inspection, pointcloud_functions
from biw_utils.SpotPointcloud import SpotPointcloud
from biw_utils.decorators import spot_connection_check, user_input_decorator
from widget.common.ArmPositionSettingWidget import ArmPositionSettingWidget
from widget.common.GraphicView import GraphicView
from widget.HoleInspection.TemplateDisplayWidget import TemplateDisplayWidget

class HoleInspectionWidget(QWidget):
    def __init__(self, main_operator: MainOperator, position):
        super().__init__()
        self.main_operator = main_operator
        # self.setObjectName("WidgetHoleInspection")

        self.position = 2

        # Load default values from the configuration file
        self.selected_image = None
        self.depth_inspection_image = None
        self.region = (0, 0, 0, 0)
        self.template_box = None

        # Arm Correction Master Files
        self.master_pointcloud = None
        self.master_hand_color = None
        self.master_hand_depth = None

        # region UI Setup
        # Main dialog setup
        self.hlayout_main = QHBoxLayout()
        # self.hlayout_main.setObjectName("MainLayout")
        self.hlayout_main.setSpacing(0)
        self.vlayout_main = QVBoxLayout()

        # Font setup
        # self.font = QtGui.QFont()
        # self.font.setFamily("현대하모니 M")
        # self.font.setPointSize(10)
        # self.setFont(self.font)

        # stylesheet setup
        # self.label_stylesheet = "font: 10.5pt \"현대하모니 M\";"
        # self.setStyleSheet(f"QLabel {{{self.label_stylesheet}}}")

        self.arm_teaching_widget = ArmPositionSettingWidget()
        self.define_arm_teaching_events()

        # Widget Definition
        self.widget_input = QWidget()

        # Scroll Area for left side
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.widget_input)

        self.stackedWidget_viewer = QStackedWidget()
        self.stackedWidget_viewer.setStyleSheet("padding: 0px; margin: 0px;")

        self.vlayout_input = QVBoxLayout(self.widget_input)
        # self.vlayout_input.setObjectName("vlayout_input")

        flayout_settings = QFormLayout()
        self.hlayout_waypoint = QHBoxLayout()

        self.cbx_inspection_waypoint1 = QComboBox()
        self.cbx_inspection_waypoint2 = QComboBox()

        self.lbl_resolution = QLabel("Resolution")
        self.cbx_resolution = QComboBox()

        self.cbx_resolution.addItem("640x480")
        self.cbx_resolution.addItem("1280x720")
        self.cbx_resolution.addItem("1920x1080")
        self.cbx_resolution.addItem("3840x2160")
        self.cbx_resolution.addItem("4096x2160")
        self.cbx_resolution.addItem("4208x3120")

        self.hlayout_focus_absolute = QHBoxLayout()
        self.lbl_focus_absolute = QLabel("focus absolute")
        self.sbx_focus_absolute = QDoubleSpinBox()
        self.sbx_focus_absolute.setValue(0.22)
        self.sbx_focus_absolute.setDecimals(2)
        self.sbx_focus_absolute.setMaximum(1)
        self.sbx_focus_absolute.setSingleStep(0.01)

        flayout_settings.addRow(QLabel("Waypoint1"), self.cbx_inspection_waypoint1)
        flayout_settings.addRow(QLabel("Waypoint2"), self.cbx_inspection_waypoint2)
        flayout_settings.addRow(self.lbl_resolution, self.cbx_resolution)
        flayout_settings.addRow(self.lbl_focus_absolute, self.sbx_focus_absolute)

        self.hlayout_apply_button = QHBoxLayout()
        self.btn_load_settings = QPushButton("Load")
        self.btn_apply_settings = QPushButton("Apply")

        self.btn_load_settings.clicked.connect(self.load_setting)
        self.btn_apply_settings.clicked.connect(self.apply_setting)
        self.hlayout_apply_button.addStretch(1)
        self.hlayout_apply_button.addWidget(self.btn_load_settings)
        self.hlayout_apply_button.addWidget(self.btn_apply_settings)

        self.lbl_algorithm = QLabel("Algorithm", self.widget_input)
        self.cbx_algorithm = QComboBox(self.widget_input)
        # self.cbx_algorithm.setFont(self.font)
        self.cbx_algorithm.setEnabled(True)
        # self.cbx_algorithm.setObjectName("cbx_algorithm")
        self.cbx_algorithm.addItem("Rule")
        self.cbx_algorithm.addItem("AI")

        self.widget_rule = QWidget(self.widget_input)
        self.widget_AI = QWidget(self.widget_input)

        # self.widget_rule.setObjectName("WidgetHoleInspection_widget_rule")
        # self.widget_AI.setObjectName("WidgetHoleInspection_widget_AI")

        # Rule Widget
        self.vlayout_rule = QVBoxLayout()
        # self.vlayout_rule.setObjectName("vlayout_rule")
        self.lbl_setting_rule = QLabel("Rule Setting", self.widget_rule)
        self.btn_load_image_rule = QPushButton("Load Image", self.widget_rule)
        self.btn_apply_region = QPushButton("Setting ROI", self.widget_rule)
        self.btn_apply_template = QPushButton("Setting Template", self.widget_rule)

        self.cbx_save_template = QCheckBox("Save Template Directly", self.widget_rule)
        # self.cbx_save_template.setFont(self.font)

        self.widget_template_filename = QWidget(self.widget_rule)
        # self.widget_template_filename.setObjectName("WidgetHoleInspection_widget_template_filename")
        self.flayout_template_filename = QFormLayout(self.widget_rule)
        self.lbl_template_filename = QLabel("Save File Name", self.widget_rule)
        self.lbl_template_filename.setStyleSheet("font: 10pt \"현대하모니 M\";")
        self.line_edit_template_filename = QLineEdit("ROI", self.widget_rule)
        self.flayout_template_filename.addRow(self.lbl_template_filename, self.line_edit_template_filename)
        self.widget_template_filename.setLayout(self.flayout_template_filename)
        self.widget_template_filename.hide()

        self.btn_show_template = QPushButton("Check Templates", self.widget_rule)
        self.btn_inspection_rule = QPushButton("Inspect Loaded Image", self.widget_rule)

        # self.lbl_rule_region = QLabel("설정된 검사 구역", self.widget_rule)
        # self.lbl_rule_region_value = QLineEdit(self.widget_rule)
        # self.lbl_rule_region_value.setReadOnly(True)

        self.hlayout_rule_threshold = QHBoxLayout()
        self.lbl_rule_threshold = QLabel("Threshold Setting", self.widget_rule)
        self.sbx_rule_threshold = QDoubleSpinBox(self.widget_rule)
        self.sbx_rule_threshold.setValue(0.7)
        self.sbx_rule_threshold.setDecimals(2)
        self.sbx_rule_threshold.setMaximum(1)
        self.sbx_rule_threshold.setSingleStep(0.01)

        self.hlayout_rule_threshold.addWidget(self.lbl_rule_threshold)
        self.hlayout_rule_threshold.addWidget(self.sbx_rule_threshold)
        self.hlayout_rule_threshold.setStretch(0, 1)
        self.hlayout_rule_threshold.setStretch(1, 0)

        self.vlayout_rule.addWidget(self.lbl_setting_rule)
        self.vlayout_rule.addWidget(self.btn_load_image_rule)
        self.vlayout_rule.addWidget(self.btn_apply_region)
        self.vlayout_rule.addWidget(self.btn_apply_template)
        self.vlayout_rule.addWidget(self.cbx_save_template)
        self.vlayout_rule.addWidget(self.widget_template_filename)
        self.vlayout_rule.addWidget(self.btn_show_template)
        self.vlayout_rule.addWidget(self.btn_inspection_rule)
        # self.vlayout_rule.addWidget(self.lbl_rule_region)
        # self.vlayout_rule.addWidget(self.lbl_rule_region_value)
        self.vlayout_rule.addLayout(self.hlayout_rule_threshold)

        self.widget_rule.setLayout(self.vlayout_rule)

        # AI Widget
        self.vlayout_AI = QVBoxLayout(self.widget_AI)
        # self.vlayout_AI.setObjectName("vlayout_rule")

        self.lbl_setting_AI = QLabel("AI Setting (Beta)", self.widget_AI)
        self.btn_load_image_AI = QPushButton("Load Image", self.widget_AI)
        self.btn_inspection_AI = QPushButton("Inspect", self.widget_AI)

        self.lbl_AI_result = QLabel("Inspect Result", self.widget_AI)
        self.lbl_AI_result_detail1 = QLabel("IS HOLE: Y", self.widget_AI)
        self.lbl_AI_result_detail2 = QLabel("Description: {}", self.widget_AI)

        self.vlayout_AI.addWidget(self.lbl_setting_AI)
        self.vlayout_AI.addWidget(self.btn_load_image_AI)
        self.vlayout_AI.addWidget(self.btn_inspection_AI)
        self.vlayout_AI.addWidget(self.lbl_AI_result)
        self.vlayout_AI.addWidget(self.lbl_AI_result_detail1)
        self.vlayout_AI.addWidget(self.lbl_AI_result_detail2)

        # Add widgets
        self.vlayout_input.addLayout(flayout_settings)
        self.vlayout_input.addLayout(self.hlayout_apply_button)
        self.vlayout_input.addWidget(self.arm_teaching_widget)
        self.vlayout_input.addWidget(self.lbl_algorithm)
        self.vlayout_input.addWidget(self.cbx_algorithm)
        self.vlayout_input.addWidget(self.widget_rule)
        self.vlayout_input.addWidget(self.widget_AI)

        # Arm Correction Setting
        self.cbx_arm_correction = QCheckBox("Use Arm Correction", self.widget_input)
        # self.cbx_arm_correction.setFont(self.font)

        self.widget_arm_correction = QWidget(self.widget_input)
        # self.widget_arm_correction.setObjectName("WidgetHoleInspection_widget_arm_correction")
        self.vlayout_arm_correction = QVBoxLayout(self.widget_arm_correction)
        self.vlayout_arm_correction.setSpacing(10)

        self.lbl_master_path_str = QLabel("Master Data Path", self.widget_arm_correction)
        self.lbl_master_path = QLineEdit()
        self.lbl_master_path.setReadOnly(True)
        self.lbl_check_master = QLabel("Show Master Data", self.widget_arm_correction)
        self.btn_show_pcd_master = QPushButton("Show Master PointCloud", self.widget_arm_correction)
        self.btn_show_image_master = QPushButton("Show Master Image", self.widget_arm_correction)
        self.lbl_setting_params = QLabel("Set Parameters", self.widget_arm_correction)

        self.vlayout_icp = QVBoxLayout()
        self.vlayout_icp.setSpacing(6)
        self.lbl_icp_setting = QLabel("ICP Algorithm Setting", self.widget_arm_correction)

        self.hlayout_icp_threshold = QHBoxLayout()
        self.lbl_icp_threshold = QLabel("ICP Threshold", self.widget_arm_correction)
        self.vlayout_icp.addWidget(self.lbl_icp_setting)
        self.hlayout_icp_threshold.addWidget(self.lbl_icp_threshold)
        self.sbx_icp_threshold = QDoubleSpinBox(self.widget_arm_correction)
        self.sbx_icp_threshold.setEnabled(True)
        self.sbx_icp_threshold.setDecimals(3)
        self.sbx_icp_threshold.setMaximum(1.0)
        self.sbx_icp_threshold.setSingleStep(0.001)
        self.sbx_icp_threshold.setProperty("value", 0.02)
        self.hlayout_icp_threshold.addWidget(self.sbx_icp_threshold)
        self.hlayout_loss_sigma = QHBoxLayout()
        self.lbl_loss_sigma = QLabel("Loss Sigma", self.widget_arm_correction)
        self.hlayout_loss_sigma.addWidget(self.lbl_loss_sigma)
        self.sbx_loss_sigma = QDoubleSpinBox(self.widget_arm_correction)
        self.sbx_loss_sigma.setEnabled(True)
        self.sbx_loss_sigma.setMaximum(1.0)
        self.sbx_loss_sigma.setSingleStep(0.01)
        self.sbx_loss_sigma.setProperty("value", 0.05)
        self.hlayout_loss_sigma.addWidget(self.sbx_loss_sigma)

        self.hlayout_icp_iteration = QHBoxLayout()
        self.hlayout_icp_iteration.setSpacing(6)
        self.lbl_icp_iteration = QLabel("ICP Iteration", self.widget_arm_correction)
        self.sbx_icp_iteration = QSpinBox(self.widget_arm_correction)
        self.sbx_icp_iteration.setEnabled(True)
        self.sbx_icp_iteration.setProperty("value", 10)
        self.hlayout_icp_iteration.addWidget(self.lbl_icp_iteration)
        self.hlayout_icp_iteration.addWidget(self.sbx_icp_iteration)

        self.vlayout_icp.addLayout(self.hlayout_icp_threshold)
        self.vlayout_icp.addLayout(self.hlayout_loss_sigma)
        self.vlayout_icp.addLayout(self.hlayout_icp_iteration)

        self.vlayout_arm_correction.addWidget(self.lbl_master_path_str)
        self.vlayout_arm_correction.addWidget(self.lbl_master_path)
        self.vlayout_arm_correction.addWidget(self.lbl_check_master)
        self.vlayout_arm_correction.addWidget(self.btn_show_pcd_master)
        self.vlayout_arm_correction.addWidget(self.btn_show_image_master)
        self.vlayout_arm_correction.addWidget(self.lbl_setting_params)
        self.vlayout_arm_correction.addLayout(self.vlayout_icp)

        self.vlayout_input.addWidget(self.cbx_arm_correction)
        self.vlayout_input.addStretch()

        self.vlayout_input.addWidget(self.widget_arm_correction)

        # spacerItem = QtWidgets.QSpacerItem(20, 96, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.vlayout_input.addItem(spacerItem)

        # Viewer Widget
        self.widget_viewer_1 = QWidget(self.stackedWidget_viewer)
        # self.widget_viewer_1.setObjectName("WidgetHoleInspection_widget_viewer_1")
        self.vlayout_image = QVBoxLayout(self.widget_viewer_1)

        # self.view = MyQGraphicsView()
        self.view = GraphicView()
        self.view.setObjectName("image")
        # 이미지 확대/축소를 위한 스크롤바 설정
        # self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.vlayout_image.addWidget(self.view)

        self.scene = QGraphicsScene()
        self.stackedWidget_viewer.addWidget(self.widget_viewer_1)

        # self.hlayout_main.addWidget(self.widget_input)
        self.hlayout_main.addWidget(self.scroll_area)
        self.hlayout_main.addWidget(self.stackedWidget_viewer)

        self.hlayout_main.setStretch(0, 2)
        self.hlayout_main.setStretch(1, 5)

        self.setLayout(self.hlayout_main)
        # self.vlayout_main.addItem(spacerItem)
        # endregion

        self.hide_widget()
        self.init_signals()
        self.load_setting()

    def init_signals(self):
        self.btn_load_image_rule.clicked.connect(self.load_image)
        self.btn_show_template.clicked.connect(self.show_roi_images)
        self.btn_apply_region.clicked.connect(self.apply_region)
        self.btn_apply_template.clicked.connect(self.apply_template)
        self.btn_inspection_rule.clicked.connect(self.inspection_rule)

        self.cbx_save_template.stateChanged.connect(self.toggle_save_template)

        # Depth Inspection
        # self.btn_load_image_depth.clicked.connect(self.load_image_depth_inspection)

        self.cbx_algorithm.currentIndexChanged.connect(self.toggle_widgets)
        self.cbx_arm_correction.stateChanged.connect(self.toggle_arm_correction)

        self.btn_show_pcd_master.clicked.connect(self.show_master_pointcloud)
        self.btn_show_image_master.clicked.connect(self.show_master_image)

    def define_arm_teaching_events(self):
        self.arm_teaching_widget.apply_current_position(self.hole_get_current_arm_pose)
        self.arm_teaching_widget.execute_joint_move(self.move_current_arm_pose)
        self.arm_teaching_widget.execute_stow(self.spot_arm_stow)
        self.arm_teaching_widget.execute_capture(self.capture)
        self.arm_teaching_widget.execute_load_arm_status(self.load_arm_status)
        self.arm_teaching_widget.execute_save_arm_status(self.save_arm_status)

    # region UI Functions
    def load_setting(self):
        if DefineGlobal.SELECTED_BODY_TYPE == DefineGlobal.BODY_TYPE.ME:
            self.main_operator.spot_manager.update_data()
        inspection_settings = self.main_operator.spot_manager.get_position_setting(self.position)

        waypoint1 = inspection_settings.get("waypoint1", "-")
        waypoint2 = inspection_settings.get("waypoint2", "-")
        resolution = inspection_settings.get("resolution", "-")
        arm_position = inspection_settings.get("arm_position", None)
        focus_absolute = inspection_settings.get("focus_absolute", 0)

        # Apply UI
        self.cbx_inspection_waypoint1.setCurrentText(waypoint1)
        self.cbx_inspection_waypoint2.setCurrentText(waypoint2)
        self.cbx_resolution.setCurrentText(resolution)
        self.sbx_focus_absolute.setValue(focus_absolute)

        self.cbx_inspection_waypoint1.setCurrentText(waypoint1)
        self.cbx_inspection_waypoint2.setCurrentText(waypoint2)
        self.cbx_resolution.setCurrentText(resolution)
        self.sbx_focus_absolute.setValue(focus_absolute)

        if arm_position is not None:
            self.arm_teaching_widget.line_edit_sh0_value.setText(str(arm_position['sh0']))
            self.arm_teaching_widget.line_edit_sh1_value.setText(str(arm_position['sh1']))
            self.arm_teaching_widget.line_edit_el0_value.setText(str(arm_position['el0']))
            self.arm_teaching_widget.line_edit_el1_value.setText(str(arm_position['el1']))
            self.arm_teaching_widget.line_edit_wr0_value.setText(str(arm_position['wr0']))
            self.arm_teaching_widget.line_edit_wr1_value.setText(str(arm_position['wr1']))

            hole_inspection_data = self.main_operator.spot_manager.get_hole_inspection_setting()
            arm_correction_data = self.main_operator.spot_manager.get_arm_calibration_data()
            # hole_inspection_setting
            region = hole_inspection_data['region']
            is_arm_correction = hole_inspection_data['is_arm_correction']

            self.lbl_master_path.setText(DefineGlobal.SPOT_MASTER_DATA_PATH)
            self.region = region
            self.cbx_arm_correction.setChecked(is_arm_correction)

        else:
            self.arm_teaching_widget.line_edit_sh0_value.setText("-")
            self.arm_teaching_widget.line_edit_sh1_value.setText("-")
            self.arm_teaching_widget.line_edit_el0_value.setText("-")
            self.arm_teaching_widget.line_edit_el1_value.setText("-")
            self.arm_teaching_widget.line_edit_wr0_value.setText("-")
            self.arm_teaching_widget.line_edit_wr1_value.setText("-")

    @user_input_decorator
    def apply_setting(self):
        setting = {
            "waypoint1": self.cbx_inspection_waypoint1.currentText(),
            "waypoint2": self.cbx_inspection_waypoint2.currentText(),
            "resolution": self.cbx_resolution.currentText(),
            "focus_absolute": self.sbx_focus_absolute.value(),
            "arm_position": {
                "sh0": float(self.arm_teaching_widget.line_edit_sh0_value.text()),
                "sh1": float(self.arm_teaching_widget.line_edit_sh1_value.text()),
                "el0": float(self.arm_teaching_widget.line_edit_el0_value.text()),
                "el1": float(self.arm_teaching_widget.line_edit_el1_value.text()),
                "wr0": float(self.arm_teaching_widget.line_edit_wr0_value.text()),
                "wr1": float(self.arm_teaching_widget.line_edit_wr1_value.text())
            }
        }

        self.main_operator.spot_manager.set_position_settings(setting, self.position)

    def hide_widget(self):
        # self.widget_rule.setHidden(True)
        self.widget_AI.setHidden(True)
        self.widget_arm_correction.setHidden(True)

    def toggle_widgets(self):
        # ComboBox의 현재 선택 항목을 가져옴
        selected_item = self.cbx_algorithm.currentText()

        # 선택 항목에 따라 Widget을 보이거나 숨김
        if selected_item == "Rule":
            self.widget_rule.show()
            self.widget_AI.hide()

        elif selected_item == "AI":
            self.widget_rule.hide()
            self.widget_AI.show()

    def toggle_save_template(self, state):
        if state == 2:  # 체크된 상태
            self.widget_template_filename.show()
        else:
            self.widget_template_filename.hide()

    def toggle_arm_correction(self, state):
        # hole_inspection_setting = config_utils.read_hole_inspection()
        if state == 2:  # 체크된 상태
            self.widget_arm_correction.show()
            # hole_inspection_setting['is_arm_correction'] = 'True'
        else:
            self.widget_arm_correction.hide()
            # hole_inspection_setting['is_arm_correction'] = 'False'

        # config_utils.write_hole_inspection(hole_inspection_setting)
    # endregion

    def load_image(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Image Files (*.png *.jpg)")
        if dialog.exec_():
            selected_files = dialog.selectedFiles()[0]
            if selected_files:
                self.selected_image = cv2.imread(selected_files)
                image = deepcopy(self.selected_image)
                # pt1 = (self.region[0], self.region[1])
                # pt2 = (self.region[0] + self.region[2], self.region[1] + self.region[3])

                image_pixmap = QPixmap(selected_files)
                scene = QGraphicsScene()
                scene.addItem(QGraphicsPixmapItem(image_pixmap))
                self.view.setScenePixmap(scene, QGraphicsPixmapItem(image_pixmap))

                # utils.draw_box(image, pt1, pt2, color=(0, 255, 0))
                # utils.set_graphic_view_image(image, self.view)

    def show_roi_images(self):
        # Config에 저장된 HoleInspection의 경로에 등록된 ROI 이미지들을 불러온다.
        hole_inspection_setting = self.main_operator.spot_manager.get_hole_inspection_setting()

        # 1. ROI가 저장된 파일 경로
        roi_file_path = hole_inspection_setting.get("template_image_path", {})

        # 2. 해당 경로의 이미지 리스트
        rois_file_names = util_functions.read_roi_images(roi_file_path)
        if rois_file_names is FileNotFoundError:
            QMessageBox.information(self, "Alarm", "Template Path is Empty.")
            return
        rois = [cv2.imread(file) for file in rois_file_names]

        roi_dialog = QDialog()
        roi_dialog.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        roi_dialog.setWindowTitle("ROI Image")
        roi_dialog.resize(400, 400)
        widget_roi_image_display = TemplateDisplayWidget()
        vlayout_roi_main = QVBoxLayout(roi_dialog)
        vlayout_roi_main.addWidget(widget_roi_image_display)
        roi_dialog.setLayout(vlayout_roi_main)

        for roi, file_name in zip(rois, rois_file_names):
            pixmap_image = util_functions.convert_image_to_pixmap(roi)
            pixmap_item = QGraphicsPixmapItem(pixmap_image)
            scene = QGraphicsScene()
            scene.addItem(pixmap_item)
            view = widget_roi_image_display.gview_image
            view.setScenePixmap(scene, pixmap_item)
            widget_roi_image_display.addImageToList(pixmap_image, os.path.basename(file_name))

        roi_dialog.exec_()

    def apply_region(self):
        if self.selected_image is None:
            QMessageBox.critical(self, "Fail", "No Selected Image")
            return

        region = util_functions.select_roi(self.selected_image)
        if region == (0, 0, 0, 0):
            return

        self.region = region
        image = deepcopy(self.selected_image)
        x, y, w, h = self.region

        pt1 = (x, y)
        pt2 = (x + w, y + h)
        util_functions.draw_box(image, pt1, pt2, color=(0, 255, 0))

        if self.template_box is not None:
            x, y, w, h = self.template_box

            pt1 = (x, y)
            pt2 = (x + w, y + h)
            util_functions.draw_box(image, pt1, pt2, color=(0, 0, 255))

        util_functions.set_graphic_view_image(image, self.view)
        self.main_operator.spot_manager.set_template_region(self.region)
        # self.lbl_rule_region_value.setText(str(self.region))

    def apply_template(self):
        if self.selected_image is None:
            QMessageBox.critical(self, "Fail", "No Selected Image")
            return

        image = deepcopy(self.selected_image)
        drawed_image = deepcopy(image)

        self.template_box = util_functions.select_roi(image)

        x, y, w, h = self.template_box
        template_image = image[y:y+h, x:x+w]

        if template_image.size == 0:
            return

        template_path = self.main_operator.spot_manager.get_template_path()

        if self.cbx_save_template.isChecked():
            filename = self.line_edit_template_filename.text()
            ext = ".png"
            saved_name = filename + ext
            saved_path = os.path.join(template_path, saved_name)
            cv2.imwrite(saved_path, template_image)

        pt1 = (x, y)
        pt2 = (x+w, y+h)
        util_functions.draw_box(drawed_image, pt1, pt2, color=(0, 0, 255))

        x, y, w, h = self.region

        pt1 = (x, y)
        pt2 = (x + w, y + h)
        util_functions.draw_box(drawed_image, pt1, pt2, color=(0, 255, 0))

        util_functions.set_graphic_view_image(drawed_image, self.view)

    def inspection_rule(self):
        if self.selected_image is None:
            QMessageBox.critical(self, "Fail", "No Selected Image")
            return

        template_path = self.main_operator.spot_manager.get_template_path()
        # 2. 해당 경로의 이미지 리스트
        rois_file_names = util_functions.read_roi_images(template_path)

        if rois_file_names is FileNotFoundError:
            QMessageBox.information(self, "Alarm", "Template Path is Empty.")
            return

        rois = [cv2.imread(file) for file in rois_file_names if not os.path.isdir(file)]

        best_roi = None
        max_val = -1  # 초기 최대값 설정
        best_top_left = None
        best_bottom_right = None

        rule_result = []
        for roi, roi_file_name in zip(rois, rois_file_names):
            top_left, bottom_right, curr_max_val = rule_inspection.template_match(self.selected_image, self.region, roi)
            rule_result.append([top_left, bottom_right, curr_max_val, roi_file_name])
            if curr_max_val > max_val:
                max_val = curr_max_val
                best_roi = roi
                best_top_left = top_left
                best_bottom_right = bottom_right

        drawed_image = deepcopy(self.selected_image)
        rule_result_image = rule_inspection.draw_match_result(drawed_image, best_top_left, best_bottom_right, max_val,
                                                              best_roi.shape[1], best_roi.shape[0])

        x, y, w, h = self.region
        pt1 = (x, y)
        pt2 = (x + w, y + h)
        util_functions.draw_box(rule_result_image, pt1, pt2, color=(0, 255, 0))
        util_functions.set_graphic_view_image(rule_result_image, self.view)
        self.show_rule_result(rule_result)

    @staticmethod
    def show_rule_result(rule_result):
        message = ""
        sorted_rule_result = sorted(rule_result, key=lambda x: x[2], reverse=True)

        for rank, result in enumerate(sorted_rule_result):
            top_left, bottom_right, max_val, roi_file_name = result
            file_name = os.path.basename(roi_file_name)
            result_str = f"{rank+1:2} {file_name:-<30} {max_val:.4f}\n"
            message += result_str

        msg_box = QMessageBox()
        msg_box.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg_box.information(None, "Inspection Result", message, QMessageBox.Ok)

    # Depth inspection
    def load_image_depth_inspection(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("Image Files (*.png *.jpg)")
        if dialog.exec_():
            selected_files = dialog.selectedFiles()[0]
            if selected_files:
                image = cv2.imread(selected_files, cv2.IMREAD_UNCHANGED)
                util_functions.set_graphic_view_image(image, self.view)
                self.depth_inspection_image = image

    def show_master_pointcloud(self):
        arm_correction_data = self.main_operator.spot_manager.get_arm_calibration_data()

        master_depth_path = os.path.join(DefineGlobal.SPOT_MASTER_DATA_PATH, arm_correction_data["hand_depth"])
        master_depth_color_path = os.path.join(DefineGlobal.SPOT_MASTER_DATA_PATH, arm_correction_data["depth_color"])

        master_depth = cv2.imread(master_depth_path, cv2.IMREAD_UNCHANGED)
        master_depth_color = cv2.imread(master_depth_color_path)
        util_functions.set_graphic_view_image(master_depth_color, self.view)

        depth_settings = self.main_operator.spot_manager.get_depth_settings()
        spot_pointcloud = SpotPointcloud()
        spot_pointcloud.prepare(master_depth)

        if depth_settings['is_sor']:
            spot_pointcloud.apply_sor_filter()

        pointcloud_functions.show(spot_pointcloud.pointcloud)

    def show_master_image(self):
        arm_correction_data = self.main_operator.spot_manager.get_arm_calibration_data()

        master_hand_color_path = os.path.join(DefineGlobal.SPOT_MASTER_DATA_PATH, arm_correction_data["hand_color"])
        master_hand_color = cv2.imread(master_hand_color_path)

        util_functions.set_graphic_view_image(master_hand_color, self.view)

    def get_hole_inspection_parameter(self):
        rule_threshold = self.sbx_rule_threshold.value()
        focus_absolute = self.sbx_focus_absolute.value()

        return rule_threshold, focus_absolute

    @spot_connection_check
    def hole_get_current_arm_pose(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText("Apply current arm pose values?")
        msg_box.setWindowTitle("Confirm Registration")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        result = msg_box.exec_()

        if result == QMessageBox.Yes:
            hand_pose = self.main_operator.spot_robot.get_hand_position_dict()
            joint_state = self.main_operator.spot_robot.get_current_joint_state()

            self.arm_teaching_widget.line_edit_sh0_value.setText(str(joint_state['sh0']))
            self.arm_teaching_widget.line_edit_sh1_value.setText(str(joint_state['sh1']))
            self.arm_teaching_widget.line_edit_el0_value.setText(str(joint_state['el0']))
            self.arm_teaching_widget.line_edit_el1_value.setText(str(joint_state['el1']))
            self.arm_teaching_widget.line_edit_wr0_value.setText(str(joint_state['wr0']))
            self.arm_teaching_widget.line_edit_wr1_value.setText(str(joint_state['wr1']))

    def move_current_arm_pose(self):
        sh0 = float(self.arm_teaching_widget.line_edit_sh0_value.text())
        sh1 = float(self.arm_teaching_widget.line_edit_sh1_value.text())
        el0 = float(self.arm_teaching_widget.line_edit_el0_value.text())
        el1 = float(self.arm_teaching_widget.line_edit_el1_value.text())
        wr0 = float(self.arm_teaching_widget.line_edit_wr0_value.text())
        wr1 = float(self.arm_teaching_widget.line_edit_wr1_value.text())
        params = [sh0, sh1, el0, el1, wr0, wr1]
        result = self.main_operator.spot_joint_move_manual(params)
        self.main_operator.write_log(result)

    @spot_connection_check
    def spot_arm_stow(self):
        result = self.main_operator.spot_robot.robot_arm_manager.stow()
        self.main_operator.write_log(result)

    def load_arm_status(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter("JSON Files (*.json)")
        joint_pos_dict = None
        if dialog.exec_():
            selected_files = dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                with open(file_path, 'r') as file:
                    joint_pos_dict = json.load(file)

        if not joint_pos_dict:
            return

        # self.main_operator.spot_manager.set_arm_pose_setting(joint_pos_dict, self.position)
        self.setup_arm_values(joint_pos_dict.values())

    def setup_arm_values(self, values):
        labels = ["sh0", "sh1", "el0", "el1", "wr0", "wr1"]

        for label, value in zip(labels, values):
            label_name = f"line_edit_{label}_value"
            label_widget = getattr(self.arm_teaching_widget, label_name, None)
            label_widget.setText(str(value))

    def save_arm_status(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Arm Status", "", "JSON Files (*.json)", options=options)

        if not file_path:
            return

        joint_params_dict = self.main_operator.spot_manager.get_arm_setting(self.position)
        # joint_params_dict = {
        #     'sh0': float(joint_params[0]),
        #     'sh1': float(joint_params[1]),
        #     'el0': float(joint_params[2]),
        #     'el1': float(joint_params[3]),
        #     'wr0': float(joint_params[4]),
        #     'wr1': float(joint_params[5])
        # }

        # 입력된 파일 경로의 확장자 검사
        if not file_path.endswith(".json"):
            file_path += '.json'

        with open(file_path, 'w') as file:
            json.dump(joint_params_dict, file, indent=4)

        msg_box = QMessageBox()
        msg_box.information(None, "Save", "Save Complete.")

    def capture(self):
        image = self.main_operator.spot_capture_bgr()
        if image is not None:
            self.view.set_bgr_image(image)
