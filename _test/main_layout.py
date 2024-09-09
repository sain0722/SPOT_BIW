import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, \
    QGridLayout, QProgressBar, QListWidget, QRadioButton, QButtonGroup
from PySide6.QtGui import QPalette, QLinearGradient, QColor, QFont, QPixmap, QPainter, QPainterPath
from PySide6.QtCore import Qt, QSize

from custom_widget import RoundLabel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Hyundai BIW Inspection Display')
        # self.setGeometry(100, 100, 1600, 900)

        self.hyundai_fontM = QFont("현대하모니 M", 14)
        self.hyundai_fontL = QFont("현대하모니 L", 14)

        self.setFont(self.hyundai_fontL)

        self.initUI()
        self.applyGradientBackground()
        self.applyStylesheet()

    def applyGradientBackground(self):
        palette = QPalette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0, 44, 47))  # Hyundai blue
        gradient.setColorAt(1.0, QColor(0, 44, 95))  # 깊은 하늘색
        palette.setBrush(QPalette.Window, gradient)
        self.setPalette(palette)

    def applyStylesheet(self):
        with open('../style/styles.css', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())

    def initUI(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Header
        header_widget = QWidget()
        header_widget.setObjectName("header")
        header_layout = QHBoxLayout(header_widget)

        # 로고
        logo_label = QLabel()
        logo_label.setObjectName("logo")
        logo_label.setFixedWidth(300)
        pixmap = QPixmap('../resources/Hyundai_Motor_Company_logo.svg')  # 현대 로고 이미지 파일 경로
        scaled_pixmap = pixmap.scaled(logo_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignVCenter)

        # VIN 번호
        vin_label = QLabel("BI 083744")
        vin_label.setObjectName("header")
        vin_label.setAlignment(Qt.AlignCenter)
        vin_label.setProperty("title", True)

        # 제목
        title_label = QLabel("차체 BIW 검사 AI KEEPER")
        title_label.setObjectName("header")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setProperty("title", True)

        # 타임스탬프
        timestamp_label = QLabel("2024-05-20 19:50:38")
        timestamp_label.setObjectName("header")
        timestamp_label.setAlignment(Qt.AlignCenter)
        timestamp_label.setAlignment(Qt.AlignRight)
        timestamp_label.setProperty("title", True)

        header_layout.addWidget(logo_label)
        header_layout.addStretch()
        header_layout.addWidget(vin_label)
        header_layout.addStretch()
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(timestamp_label)

        header_layout.setStretch(0, 0)
        header_layout.setStretch(1, 3)
        header_layout.setStretch(2, 3)
        header_layout.setStretch(3, 3)
        header_layout.setStretch(4, 3)
        header_layout.setStretch(5, 3)
        header_layout.setStretch(6, 3)

        # Body layout
        body_widget = QWidget()
        body_widget.setObjectName("body")
        body_layout = QGridLayout(body_widget)

        # 왼쪽 섹션 (SPOT 및 MES Communication)
        left_layout = QVBoxLayout()

        # SPOT 정보
        spot_layout = QVBoxLayout()

        spot_title_layout = QHBoxLayout()

        self.spot_logo = QLabel()
        self.spot_logo.setObjectName("logo")
        self.spot_logo.setFixedSize(100, 100)  # 정사각형으로 고정
        self.spot_logo.setStyleSheet("border-radius: 50px; padding: 0px; margin: 0px")  # 반지름을 QLabel 크기의 절반으로 설정하여 동그랗게 만듦
        self.update_pixmap('../resources/spotimage.jpg', self.spot_logo)  # 이미지 경로를 전달

        spot_title = QLabel("SPOT")
        spot_title.setObjectName("body")
        spot_title.setProperty("title", True)
        # spot_title.setAlignment(Qt.AlignCenter)

        spot_title_layout.addWidget(self.spot_logo)
        spot_title_layout.addWidget(spot_title)
        spot_title_layout.setStretch(0, 1)
        spot_title_layout.setStretch(1, 9)

        spot_info_layout = QVBoxLayout()
        spot_info_layout.setAlignment(Qt.AlignTop)

        spot_layout_1 = QHBoxLayout()
        spot_status_1 = QLabel()
        spot_status_1.setObjectName("body")
        spot_status_1.setFixedSize(20, 20)
        spot_status_1.setStyleSheet("background-color: green; border-radius: 10px;")
        spot_robot_label_title_1 = QLabel("SPOT-BD-16037445")
        spot_robot_label_title_1.setObjectName("body")
        spot_progress_1 = QProgressBar()
        spot_progress_1.setObjectName("body")
        spot_progress_1.setValue(98)
        spot_progress_1.setFormat("%p%")
        spot_progress_1.setAlignment(Qt.AlignCenter)
        spot_live_button_1 = QPushButton("LIVE")
        spot_live_button_1.setObjectName("body")
        spot_layout_1.addWidget(spot_status_1)
        spot_layout_1.addWidget(spot_robot_label_title_1)
        spot_layout_1.addWidget(spot_progress_1)
        spot_layout_1.addWidget(spot_live_button_1)

        spot_layout_2 = QHBoxLayout()
        spot_status_2 = QLabel()
        spot_status_2.setObjectName("body")
        spot_status_2.setFixedSize(20, 20)
        spot_status_2.setStyleSheet("background-color: green; border-radius: 10px;")
        spot_robot_label_title_2 = QLabel("SPOT-BD-16037446")
        spot_robot_label_title_2.setObjectName("body")
        spot_progress_2 = QProgressBar()
        spot_progress_2.setObjectName("body")
        spot_progress_2.setValue(86)
        spot_progress_2.setFormat("%p%")
        spot_progress_2.setAlignment(Qt.AlignCenter)
        spot_live_button_2 = QPushButton("LIVE")
        spot_live_button_2.setObjectName("body")
        spot_layout_2.addWidget(spot_status_2)
        spot_layout_2.addWidget(spot_robot_label_title_2)
        spot_layout_2.addWidget(spot_progress_2)
        spot_layout_2.addWidget(spot_live_button_2)

        spot_info_layout.addLayout(spot_layout_1)
        spot_info_layout.addLayout(spot_layout_2)
        spot_layout.addLayout(spot_title_layout)
        spot_layout.addLayout(spot_info_layout)

        left_layout.addLayout(spot_layout)

        # MES Communication 정보
        mes_layout = QVBoxLayout()

        mes_title_layout = QHBoxLayout()

        self.mes_logo = QLabel()
        self.mes_logo.setObjectName("logo")
        self.mes_logo.setFixedSize(100, 100)  # 정사각형으로 고정
        self.mes_logo.setStyleSheet("padding: 0px; margin: 0px")

        mes_pixmap = QPixmap("../resources/communication.png")
        scaled_mes_pixmap = mes_pixmap.scaled(QSize(100, 100), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.mes_logo.setPixmap(scaled_mes_pixmap)

        # self.mes_logo.setStyleSheet("padding: 0px; margin: 0px")  # 반지름을 QLabel 크기의 절반으로 설정하여 동그랗게 만듦
        # self.update_pixmap('resources/communication.png', self.mes_logo)  # 이미지 경로를 전달

        mes_title = QLabel("MES Communication")
        mes_title.setObjectName("body")
        mes_title.setProperty("title", True)
        # mes_title.setAlignment(Qt.AlignCenter)
        # mes_layout.addWidget(mes_title)

        mes_title_layout.addWidget(self.mes_logo)
        mes_title_layout.addWidget(mes_title)

        mes_layout.addLayout(mes_title_layout)

        mes_grid_layout = QGridLayout()
        mes_status_icon = QLabel()
        mes_status_icon.setObjectName("body")
        mes_status_icon.setFixedSize(20, 20)
        mes_status_icon.setStyleSheet("background-color: green; border-radius: 10px;")

        mes_grid_layout.addWidget(mes_status_icon, 1, 0, 1, 2)   # 1행 0열에서 1행 2열을 차지.

        mes_label_title_1, mes_label_value_1 = self.createLabel("VIN Number", "BI 083744")
        mes_label_title_1.setObjectName("body")
        mes_label_value_1.setObjectName("body")

        mes_grid_layout.addWidget(mes_label_title_1, 0, 1)
        mes_grid_layout.addWidget(mes_label_value_1, 0, 2)

        mes_label_title_2, mes_label_value_2 = self.createLabel("Timestamp", "202405201920")
        mes_label_title_2.setObjectName("body")
        mes_label_value_2.setObjectName("body")

        mes_grid_layout.addWidget(mes_label_title_2, 1, 1)
        mes_grid_layout.addWidget(mes_label_value_2, 1, 2)

        mes_label_title_3, mes_label_value_3 = self.createLabel("QR Code", "Y")
        mes_label_title_3.setObjectName("body")
        mes_label_value_3.setObjectName("body")

        mes_grid_layout.addWidget(mes_label_title_3, 2, 1)
        mes_grid_layout.addWidget(mes_label_value_3, 2, 2)

        mes_grid_layout.setColumnStretch(0, 1)
        mes_grid_layout.setColumnStretch(1, 8)
        mes_grid_layout.setColumnStretch(2, 8)

        log_layout = QVBoxLayout()
        log_list = QListWidget()
        log_list.setObjectName("customFrame")
        log_list.addItem("Log entry 1")
        log_list.addItem("Log entry 2")
        log_list.addItem("Log entry 3")

        log_layout.addWidget(log_list)

        mes_layout.addLayout(mes_grid_layout)
        left_layout.addLayout(mes_layout)
        left_layout.addLayout(log_layout)

        # 오른쪽 섹션 (Image 및 QR Code 정보)
        right_layout = QVBoxLayout()

        # region LH
        LH_section = QHBoxLayout()

        LH_image_label = QLabel("LH spot image")
        LH_image_label.setObjectName("image")
        LH_image_label.setFrameStyle(QFrame.Box)
        LH_image_label.setAlignment(Qt.AlignCenter)
        # image_label_LH.setFixedSize(640, 360)  # 16:9 비율로 고정

        LH_section_info = QVBoxLayout()

        LH_qr_code_1_layout = QHBoxLayout()
        LH_qr_code_1 = QLabel("QR Code (1)")
        LH_qr_code_1_info = QLabel("infomations...\ninfo1\ninfo2\ninfo3")
        LH_qr_code_1.setObjectName("body")
        LH_qr_code_1_info.setObjectName("body")
        LH_qr_code_1_layout.addWidget(LH_qr_code_1)
        LH_qr_code_1_layout.addWidget(LH_qr_code_1_info)
        LH_hole_layout = QHBoxLayout()
        LH_hole_label = QLabel("Hole Inspection")
        LH_hole_label.setObjectName("body")
        LH_hole_inspection_result = QLabel()
        LH_hole_inspection_result.setObjectName("body")
        LH_hole_inspection_result.setFixedSize(20, 20)
        LH_hole_inspection_result.setStyleSheet("background-color: green; border-radius: 10px;")
        LH_hole_inspection_content = QLabel("hole inspection result..\nscore:0.997")
        LH_hole_inspection_content.setObjectName("body")
        LH_hole_layout.addWidget(LH_hole_label)
        LH_hole_layout.addWidget(LH_hole_inspection_result)
        LH_hole_layout.addWidget(LH_hole_inspection_content)
        LH_qr_code_2_layout = QHBoxLayout()
        LH_qr_code_2 = QLabel("QR Code (2)")
        LH_qr_code_2_info = QLabel("infomations...\ninfo1\ninfo2\ninfo3")
        LH_qr_code_2.setObjectName("body")
        LH_qr_code_2_info.setObjectName("body")
        LH_qr_code_2_layout.addWidget(LH_qr_code_2)
        LH_qr_code_2_layout.addWidget(LH_qr_code_2_info)

        LH_section_info.addLayout(LH_qr_code_1_layout)
        LH_section_info.addLayout(LH_hole_layout)
        LH_section_info.addLayout(LH_qr_code_2_layout)

        LH_section.addWidget(LH_image_label)
        LH_section.addLayout(LH_section_info)
        #endregion

        # region RH
        RH_section = QHBoxLayout()

        RH_image_label = QLabel("RH spot image")
        RH_image_label.setObjectName("image")
        RH_image_label.setFrameStyle(QFrame.Box)
        RH_image_label.setAlignment(Qt.AlignCenter)
        # image_label_LH.setFixedSize(640, 360)  # 16:9 비율로 고정

        RH_section_info = QVBoxLayout()

        RH_qr_code_1_layout = QHBoxLayout()
        RH_qr_code_1 = QLabel("QR Code (1)")
        RH_qr_code_1_info = QLabel("infomations...\ninfo1\ninfo2\ninfo3")
        RH_qr_code_1.setObjectName("body")
        RH_qr_code_1_info.setObjectName("body")
        RH_qr_code_1_layout.addWidget(RH_qr_code_1)
        RH_qr_code_1_layout.addWidget(RH_qr_code_1_info)
        RH_hole_layout = QHBoxLayout()
        RH_hole_label = QLabel("Hole Inspection")
        RH_hole_label.setObjectName("body")
        RH_hole_inspection_result = QLabel()
        RH_hole_inspection_result.setObjectName("body")
        RH_hole_inspection_result.setFixedSize(20, 20)
        RH_hole_inspection_result.setStyleSheet("background-color: green; border-radius: 10px;")
        RH_hole_inspection_content = QLabel("hole inspection result..\nscore:0.997")
        RH_hole_inspection_content.setObjectName("body")
        RH_hole_layout.addWidget(RH_hole_label)
        RH_hole_layout.addWidget(RH_hole_inspection_result)
        RH_hole_layout.addWidget(RH_hole_inspection_content)
        RH_qr_code_2_layout = QHBoxLayout()
        RH_qr_code_2 = QLabel("QR Code (2)")
        RH_qr_code_2_info = QLabel("infomations...\ninfo1\ninfo2\ninfo3")
        RH_qr_code_2.setObjectName("body")
        RH_qr_code_2_info.setObjectName("body")
        RH_qr_code_2_layout.addWidget(RH_qr_code_2)
        RH_qr_code_2_layout.addWidget(RH_qr_code_2_info)

        RH_section_info.addLayout(RH_qr_code_1_layout)
        RH_section_info.addLayout(RH_hole_layout)
        RH_section_info.addLayout(RH_qr_code_2_layout)
        RH_section.addWidget(RH_image_label)
        RH_section.addLayout(RH_section_info)
        #endregion

        right_layout.addLayout(LH_section)
        right_layout.addLayout(RH_section)

        body_layout.addLayout(left_layout, 0, 0)
        body_layout.addLayout(right_layout, 0, 1)

        # Set column stretch factors to 3:7 ratio
        body_layout.setColumnStretch(0, 3)
        body_layout.setColumnStretch(1, 7)

        # Add header and body to the main layout
        main_layout.addWidget(header_widget)
        main_layout.addWidget(body_widget)

        # Set stretch factors
        main_layout.setStretchFactor(header_widget, 1)
        main_layout.setStretchFactor(body_widget, 9)

    def createLabel(self, title, value):
        title_label = QLabel(title)
        value_label = QLabel(value)
        return title_label, value_label

    def update_pixmap(self, image_path, logo: QLabel):
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print("Error: Unable to load image")
            return

        scaled_pixmap = pixmap.scaled(logo.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        rounded_pixmap = self.create_round_pixmap(scaled_pixmap, logo)
        logo.setPixmap(rounded_pixmap)
        logo.setMask(rounded_pixmap.mask())  # 마스크 설정으로 동그란 모양을 만듦

    def create_round_pixmap(self, pixmap, logo: QLabel):
        size = logo.size()
        rounded_pixmap = QPixmap(size)
        rounded_pixmap.fill(Qt.transparent)

        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)

        # 이미지가 QLabel의 중앙에 위치하도록 계산
        x_offset = (pixmap.width() - size.width()) // 2
        y_offset = (pixmap.height() - size.height()) // 2
        painter.drawPixmap(-x_offset, -y_offset, pixmap)
        painter.end()

        return rounded_pixmap


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
