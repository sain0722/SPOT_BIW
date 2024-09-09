from PySide6.QtWidgets import QWidget, QFormLayout, QLabel, QLineEdit, QFrame, QComboBox, QPushButton, QVBoxLayout


class SpotCameraParameterWidget(QWidget):
    def __init__(self, main_operator):
        super().__init__()
        self.main_operator = main_operator
        self.param_manager = self.main_operator.spot_robot.robot_camera_param_manager
        self.initUI()

    def initUI(self):
        self.lbl_title = QLabel("■ Camera Parameters")
        self.vlayout_camera_param = QVBoxLayout()

        self.flayout_camera_param = QFormLayout()
        self.lbl_resolution = QLabel("Resolution")
        self.cbx_resolution = QComboBox()
        self.cbx_resolution.addItem("640x480")
        self.cbx_resolution.addItem("1280x720")
        self.cbx_resolution.addItem("1920x1080")
        self.cbx_resolution.addItem("3840x2160")
        self.cbx_resolution.addItem("4096x2160")
        self.cbx_resolution.addItem("4208x3120")
        self.cbx_resolution.currentIndexChanged.connect(self.handle_resolution_change)

        self.lbl_brightness = QLabel("Brightness")
        self.line_edit_brightness = QLineEdit()
        self.line_edit_brightness.setReadOnly(True)

        self.lbl_hdr = QLabel("HDR")
        self.line_edit_hdr = QLineEdit()
        self.line_edit_hdr.setReadOnly(True)

        self.lbl_gain = QLabel("Gain")
        self.line_edit_gain = QLineEdit()
        self.line_edit_gain.setReadOnly(True)

        self.lbl_contrast = QLabel("Contrast")
        self.line_edit_contrast = QLineEdit()
        self.line_edit_contrast.setReadOnly(True)

        self.lbl_saturation = QLabel("Saturation")
        self.line_edit_saturation = QLineEdit()
        self.line_edit_saturation.setReadOnly(True)

        self.lbl_focus_auto = QLabel("Focus")
        self.line_edit_focus_auto = QLineEdit()
        self.line_edit_focus_auto.setReadOnly(True)

        self.lbl_exposure_auto = QLabel("Exposure")
        self.line_edit_exposure_auto = QLineEdit()
        self.line_edit_exposure_auto.setReadOnly(True)

        self.flayout_camera_param.addRow(self.lbl_resolution, self.cbx_resolution)
        self.flayout_camera_param.addRow(self.lbl_brightness, self.line_edit_brightness)
        self.flayout_camera_param.addRow(self.lbl_contrast, self.line_edit_contrast)
        self.flayout_camera_param.addRow(self.lbl_gain, self.line_edit_gain)
        self.flayout_camera_param.addRow(self.lbl_saturation, self.line_edit_saturation)
        self.flayout_camera_param.addRow(self.lbl_hdr, self.line_edit_hdr)
        self.flayout_camera_param.addRow(self.lbl_focus_auto, self.line_edit_focus_auto)
        self.flayout_camera_param.addRow(self.lbl_exposure_auto, self.line_edit_exposure_auto)

        self.btn_check_camera_param = QPushButton("Renew Camera Parameters")
        self.btn_check_camera_param.clicked.connect(self.initialize)

        self.vlayout_camera_param.addWidget(self.lbl_title)
        self.vlayout_camera_param.addLayout(self.flayout_camera_param)
        self.vlayout_camera_param.addWidget(self.btn_check_camera_param)

        self.setLayout(self.vlayout_camera_param)
        self.initialize()

    def initialize(self):
        if self.param_manager.gripper_camera_param_client is None:
            return

        s_resolution = self.param_manager.get_resolution()
        f_brightness = self.param_manager.get_brightness().value
        s_hdr        = self.param_manager.get_hdr()
        f_gain       = self.param_manager.get_gain().value
        f_contrast   = self.param_manager.get_contrast().value
        f_saturation = self.param_manager.get_saturation().value
        gb_exposure_auto, gf_exposure_absolute = self.param_manager.get_exposure()
        gb_focus_auto,    gf_focus_absolute    = self.param_manager.get_focus()

        b_exposure_auto = gb_exposure_auto.value
        b_focus_auto = gb_focus_auto.value

        self.ui_set_parameter(s_resolution, f_brightness, s_hdr, f_gain, f_contrast, f_saturation, b_exposure_auto, gf_exposure_absolute, b_focus_auto, gf_focus_absolute)

    def ui_set_parameter(self, resolution, brightness, hdr, gain, contrast, saturation, ex_auto, ex_abs, focus_auto, focus_abs):
        """
        s_hdr_mode:
            'OFF', 'Auto', 'Low', 'Med', 'High', 'Max'
        """
        hdr_mode = {
            0: 'OFF',
            1: 'Auto',
            2: 'Low',
            3: 'Med',
            4: 'High',
            5: 'Max'
        }
        # self.line_edit_resolution.setText(str(resolution))
        self.cbx_resolution.setCurrentText(str(resolution))
        self.line_edit_brightness.setText(str(brightness))
        self.line_edit_hdr.setText(hdr_mode[hdr])
        self.line_edit_gain.setText(str(gain))
        self.line_edit_contrast.setText(str(contrast))
        self.line_edit_saturation.setText(str(saturation))

        if ex_auto:
            self.line_edit_exposure_auto.setText("Auto")
        else:
            self.line_edit_exposure_auto.setText(f"Manual: {ex_abs.value}")

        if focus_auto:
            self.line_edit_focus_auto.setText("Auto")
        else:
            self.line_edit_focus_auto.setText(f"Manual: {focus_abs.value}")

    def handle_resolution_change(self):
        selected_resolution = self.cbx_resolution.currentText()  # 현재 선택된 항목의 텍스트 가져오기
        self.param_manager.set_resolution(selected_resolution)
        # config_utils.write_camera_resolution(selected_resolution)
