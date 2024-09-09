from dataclasses import dataclass, field
# from communication.MES.MesData import *
from communication.Remote.RemoteData import *
# from communication.PLC.OpcClientData import *
# from communication.SPOT.SpotData import *

from typing import List

# joon 임시로.....
@dataclass
class SpotParameterSetting:
    body_speed:             float = 0.0
    body_angular:           float = 0.0
    arm_joint_rate:         float = 0.0
    arm_move_speed:         float = 0.0
    arm_angular:            float = 0.0
    joint_duration:         float = 0.0


@dataclass
class PositionSetting:
    waypoint:               str   = 0.0
    sh0:                    float = 0.0
    sh1:                    float = 0.0
    el0:                    float = 0.0
    el1:                    float = 0.0
    wr0:                    float = 0.0
    wr1:                    float = 0.0


@dataclass
class ImageSetting:
    path:               str = ""
    manual_path:        str = ""


@dataclass
class ArmCorrectionSetting:
    path:               str = ""
    point_cloud:        str = ""
    hand_color:         str = ""
    hand_depth:         str = ""
    depth_color:        str = ""
    arm_pose:           str = ""


@dataclass
class DepthSetting:
    is_accumulate:      bool    = False
    is_extract_range:   bool    = False
    is_gaussian:        bool    = False
    is_sor:             bool    = False
    acm_count:          int     = 0
    range_min:          int     = 0
    range_max:          int     = 0
    threshold:          float   = 0.0
    nb_neighbors:       int     = 0
    std_ratio:          float   = 0.0


@dataclass
class HoleInspectionSetting:
    path:               str   = ""
    region:             tuple = ()
    is_arm_correction:  bool  = False
    threshold:          float = 0.0


@dataclass
class DepthInspectionSetting:
    is_depth_inspection: bool  = False
    region:              tuple = ()


@dataclass
class CameraParameterSetting:
    resolution:         str = ""
    brightness:         int = 0
    contrast:           int = 0
    gain:               int = 0
    saturation:         int = 0
    focus_auto:         bool = False
    focus_absolute:     float = 0.0
    exposure_auto:      bool = False
    exposure_absolute:  int = 0
    hdr:                str = ""


@dataclass
class OperatorSettingData:
    # tRemoteServerSettingData:       RemoteSetting       = RemoteSetting()
    tRemoteClientSettingData: RemoteSetting = RemoteSetting()


