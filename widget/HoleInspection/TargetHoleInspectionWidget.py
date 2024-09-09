from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox, \
    QPushButton, QFormLayout, QCheckBox, QLineEdit, QSpinBox, QMessageBox

from widget.common.ArmPositionSettingWidget import ArmPositionSettingWidget


class TargetHoleInspectionWidget(QScrollArea):
    def __init__(self):
        super().__init__()

        # Scroll Area for left side
        self.setWidgetResizable(True)

        self.initUI()
        self.init_signal()

    def initUI(self):
        self.main_widget = QWidget()
        self.vlayout_input = QVBoxLayout()
        self.vlayout_input.setObjectName("vlayout_input")

        self.hlayout_waypoint = QHBoxLayout()
        self.lbl_inspection_waypoint = QLabel("Waypoint")
        self.cbx_inspection_waypoint = QComboBox()
        self.cbx_inspection_waypoint.setObjectName("combobox")

        self.hlayout_waypoint.addWidget(self.lbl_inspection_waypoint)
        self.hlayout_waypoint.addWidget(self.cbx_inspection_waypoint)
        self.hlayout_waypoint.setStretch(0, 1)
        self.hlayout_waypoint.setStretch(1, 1)

        self.hlayout_resolution = QHBoxLayout()
        self.lbl_resolution = QLabel("Resolution")
        self.cbx_resolution = QComboBox()
        self.cbx_resolution.setObjectName("combobox")

        self.cbx_resolution.addItem("640x480")
        self.cbx_resolution.addItem("1280x720")
        self.cbx_resolution.addItem("1920x1080")
        self.cbx_resolution.addItem("3840x2160")
        self.cbx_resolution.addItem("4096x2160")
        self.cbx_resolution.addItem("4208x3120")

        self.hlayout_resolution.addWidget(self.lbl_resolution)
        self.hlayout_resolution.addWidget(self.cbx_resolution)

        self.hlayout_focus_absolute = QHBoxLayout()
        self.lbl_focus_absolute = QLabel("focus absolute")
        self.sbx_focus_absolute = QDoubleSpinBox()
        self.sbx_focus_absolute.setValue(0.22)
        self.sbx_focus_absolute.setDecimals(2)
        self.sbx_focus_absolute.setMaximum(1)
        self.sbx_focus_absolute.setSingleStep(0.01)

        self.hlayout_focus_absolute.addWidget(self.lbl_focus_absolute)
        self.hlayout_focus_absolute.addWidget(self.sbx_focus_absolute)
        self.hlayout_focus_absolute.setStretch(0, 1)
        self.hlayout_focus_absolute.setStretch(1, 0)

        self.arm_teaching_widget = ArmPositionSettingWidget()
        self.arm_teaching_widget.apply_current_position(self.hole_get_current_arm_pose)

        self.lbl_algorithm = QLabel("알고리즘 선택", )
        self.cbx_algorithm = QComboBox()
        # self.cbx_algorithm.setFont(self.font)
        self.cbx_algorithm.setEnabled(True)
        self.cbx_algorithm.setObjectName("cbx_algorithm")
        self.cbx_algorithm.addItem("Rule")
        self.cbx_algorithm.addItem("AI")

        self.widget_rule = QWidget()
        self.widget_AI = QWidget()

        self.widget_rule.setObjectName("WidgetHoleInspection_widget_rule")
        self.widget_AI.setObjectName("WidgetHoleInspection_widget_AI")

        # Rule Widget
        self.vlayout_rule = QVBoxLayout()
        self.vlayout_rule.setObjectName("vlayout_rule")
        self.lbl_setting_rule = QLabel("Rule 설정", self.widget_rule)
        self.btn_load_image_rule = QPushButton("이미지 Load", self.widget_rule)
        self.btn_apply_region = QPushButton("검사 구역 설정", self.widget_rule)
        self.btn_apply_template = QPushButton("템플릿 설정", self.widget_rule)

        self.cbx_save_template = QCheckBox("템플릿 바로 저장", self.widget_rule)
        # self.cbx_save_template.setFont(self.font)

        self.widget_template_filename = QWidget(self.widget_rule)
        self.widget_template_filename.setObjectName("WidgetHoleInspection_widget_template_filename")
        self.flayout_template_filename = QFormLayout(self.widget_rule)
        self.lbl_template_filename = QLabel("저장 파일명", self.widget_rule)
        self.lbl_template_filename.setStyleSheet("font: 10pt \"현대하모니 M\";")
        self.line_edit_template_filename = QLineEdit("ROI", self.widget_rule)
        self.flayout_template_filename.addRow(self.lbl_template_filename, self.line_edit_template_filename)
        self.widget_template_filename.setLayout(self.flayout_template_filename)
        self.widget_template_filename.hide()

        self.btn_show_template = QPushButton("설정된 템플릿 확인", self.widget_rule)
        self.btn_inspection_rule = QPushButton("검사", self.widget_rule)

        # self.lbl_rule_region = QLabel("설정된 검사 구역", self.widget_rule)
        # self.lbl_rule_region_value = QLineEdit(self.widget_rule)
        # self.lbl_rule_region_value.setReadOnly(True)

        self.hlayout_rule_threshold = QHBoxLayout()
        self.lbl_rule_threshold = QLabel("Threshold 설정", self.widget_rule)
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
        self.vlayout_AI.setObjectName("vlayout_rule")
        self.lbl_setting_AI = QLabel("AI 설정 (Beta)", self.widget_AI)
        self.btn_load_image_AI = QPushButton("이미지 Load", self.widget_AI)
        self.btn_inspection_AI = QPushButton("검사", self.widget_AI)

        self.lbl_AI_result = QLabel("검사 결과", self.widget_AI)
        self.lbl_AI_result_detail1 = QLabel("부품명: {부품명}", self.widget_AI)
        self.lbl_AI_result_detail2 = QLabel("검사 결과: Y", self.widget_AI)

        self.vlayout_AI.addWidget(self.lbl_setting_AI)
        self.vlayout_AI.addWidget(self.btn_load_image_AI)
        self.vlayout_AI.addWidget(self.btn_inspection_AI)
        self.vlayout_AI.addWidget(self.lbl_AI_result)
        self.vlayout_AI.addWidget(self.lbl_AI_result_detail1)
        self.vlayout_AI.addWidget(self.lbl_AI_result_detail2)

        # Add widgets
        self.vlayout_input.addLayout(self.hlayout_waypoint)
        self.vlayout_input.addLayout(self.hlayout_resolution)
        self.vlayout_input.addLayout(self.hlayout_focus_absolute)
        self.vlayout_input.addWidget(self.arm_teaching_widget)
        self.vlayout_input.addWidget(self.lbl_algorithm)
        self.vlayout_input.addWidget(self.cbx_algorithm)
        self.vlayout_input.addWidget(self.widget_rule)
        self.vlayout_input.addWidget(self.widget_AI)
        self.vlayout_input.addStretch()

        # Arm Correction Setting
        self.cbx_arm_correction = QCheckBox("Arm 위치 보정 사용", )
        # self.cbx_arm_correction.setFont(self.font)

        self.widget_arm_correction = QWidget()
        self.widget_arm_correction.setObjectName("WidgetHoleInspection_widget_arm_correction")
        self.vlayout_arm_correction = QVBoxLayout(self.widget_arm_correction)
        self.vlayout_arm_correction.setSpacing(10)

        self.lbl_master_path_str = QLabel("등록된 마스터 경로", self.widget_arm_correction)
        self.lbl_master_path = QLineEdit()
        self.lbl_master_path.setReadOnly(True)
        self.lbl_check_master = QLabel("Master 확인", self.widget_arm_correction)
        self.btn_show_pcd_master = QPushButton("Master PointCloud 확인", self.widget_arm_correction)
        self.btn_show_image_master = QPushButton("Master 이미지 확인", self.widget_arm_correction)
        self.lbl_setting_params = QLabel("파라미터 설정", self.widget_arm_correction)

        self.vlayout_icp = QVBoxLayout()
        self.vlayout_icp.setSpacing(6)
        self.lbl_icp_setting = QLabel("ICP 알고리즘 Setting", self.widget_arm_correction)

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
        self.lbl_icp_iteration = QLabel("ICP 반복 횟수", self.widget_arm_correction)
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
        self.vlayout_input.addWidget(self.widget_arm_correction)

        # spacerItem = QtWidgets.QSpacerItem(20, 96, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        # self.vlayout_input.addItem(spacerItem)

        self.main_widget.setLayout(self.vlayout_input)
        self.setWidget(self.main_widget)

    def init_signal(self):
        self.cbx_arm_correction.stateChanged.connect(self.toggle_arm_correction)

    def load_setting(self):
        inspection_settings = self.main_operator.spot_manager.get_position2_settings()

        waypoint = inspection_settings.get("waypoint", {})
        resolution = inspection_settings.get("resolution", {})
        arm_position = inspection_settings.get("arm_position", {})

        # Apply UI
        self.cbx_inspection_waypoint.setCurrentText(waypoint)
        self.cbx_resolution.setCurrentText(resolution)

        self.arm_teaching_widget.line_edit_sh0_value.setText(str(arm_position['sh0']))
        self.arm_teaching_widget.line_edit_sh1_value.setText(str(arm_position['sh1']))
        self.arm_teaching_widget.line_edit_el0_value.setText(str(arm_position['el0']))
        self.arm_teaching_widget.line_edit_el1_value.setText(str(arm_position['el1']))
        self.arm_teaching_widget.line_edit_wr0_value.setText(str(arm_position['wr0']))
        self.arm_teaching_widget.line_edit_wr1_value.setText(str(arm_position['wr1']))

    def hide_widget(self):
        # self.widget_rule.setHidden(True)
        self.widget_target1.widget_AI.setHidden(True)
        self.widget_target2.widget_AI.setHidden(True)
        self.widget_target1.widget_arm_correction.setHidden(True)
        self.widget_target2.widget_arm_correction.setHidden(True)

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

    def hole_get_current_arm_pose(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText("현재 Arm 위치를 등록하시겠습니까?")
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
