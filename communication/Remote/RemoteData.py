from dataclasses import dataclass
from enum import Enum
###########################################
# global...
SOH = chr(1).encode()   # message start
STX = chr(2).encode()   # data start
ETX = chr(3).encode()   # data end
GS  = chr(29).encode()  # 그룹 구분자
US  = chr(31).encode()  # 단위 구분자

# 내부통신... 내부정의format...
# 필요포맷
# 1 message에 최대 8요청 가능하도록..
# 데이터 요청,응답....(REQ,RES)
# SOH + 'REQ'+'controller_id' + STX +'요청1'+GS+'요청2'+GS+'요청3'... + ETX
# SOH + 'RES'+'controller_id' + STX +'요청1' '응답1'+GS+'요청2' '응답2'+GS+'요청3' '응답3'... + ETX

#요청 타입
#'spotstat'     #spot connect
#'messtat'      #mes connect
#'plcstat'      #plc connect

# 응답 타입
# 'OK' or 'NG'         #spot connect
# 'OK' or 'NG'         #spot connect
# 'OK' or 'NG'         #spot connect

# 단일 메세지에 대한 구조체로 관리
##################################################################
class RemoteCommCommandType(Enum):
    Req = b"REQ"
    Res = b"RES"

class RemoteCommControllerType(Enum):
    controller_left = b"spot_controler_1"
    controller_right = b"spot_controler_2"

class RemoteCommResVal(Enum):
    spot_connected = b"TRUE"
    spot_disconnected = b"FALSE"

    mes_connected = b"TRUE"
    mes_disconnected = b"FALSE"

    plc_connected = b"TRUE"
    plc_disconnected = b"FALSE"

    pos1_inspection_result_ready_OK = b"TRUE"
    pos1_inspection_result_ready_NG = b"FALSE"

    pos2_inspection_result_ready_OK = b"TRUE"
    pos2_inspection_result_ready_NG = b"FALSE"

    pos3_inspection_result_ready_OK = b"TRUE"
    pos3_inspection_result_ready_NG = b"FALSE"

class RemoteCommReqType(Enum):
    spot_connected = b"spot_conn"
    spot_serial_no = b"spot_serial"
    spot_power = b"spot_power"
    spot_battery = b"spot_battery"
    spot_position = b"spot_position"

    mes_connected = b"mes_conn"
    mes_flag = b"mes_flag"
    mes_device_id = b"mes_device_id"
    mes_data_type = b"mes_data_type"
    mes_spool_point = b"mes_spool_point"
    mes_prod_date = b"mes_prod_date"
    mes_station_code = b"mes_station_code"
    mes_seq = b"mes_seq"
    mes_body_no = b"mes_body_no"
    mes_vic_no = b"mes_vic_no"
    mes_fsc = b"mes_fsc"

    plc_connected = b"plc_conn"
    plc_agv_no = b"plc_agv_no"
    plc_agv_mov_no = b"plc_agv_mov_no"
    plc_vic_no = b"plc_vic_no"
    plc_interlock = b"plc_interlock"

    position1_inspection_result_ready = b'pos1_result_ready'
    position2_inspection_result_ready = b'pos2_result_ready'
    position3_inspection_result_ready = b'pos3_result_ready'

    position1_inspection_result = b'pos1_result'
    position2_inspection_result = b'pos2_result'
    position3_inspection_result = b'pos3_result'

@dataclass
class RemoteCommBodyData:
    data_type: RemoteCommReqType = RemoteCommReqType.spot_connected.value
    data: bytes = b''


@dataclass
class RemoteCommMessageData:
    type: RemoteCommCommandType      # 'REQ' OR 'RES'
    id: bytes                        # 'controller 고유 id'
    body_data: list

@dataclass
class DeviceStatusData:
    spot_connected = False
    spot_serial_no = ""
    spot_power = ""
    spot_battery = ""
    spot_position = ""

    mes_connected = False
    mes_flag = ""
    mes_device_id = ""
    mes_data_type = ""
    mes_spool_point = ""
    mes_prod_date = ""
    mes_station_code = ""
    mes_seq = ""
    mes_body_no = ""
    mes_vic_no = ""
    mes_fsc = ""

    plc_connected = False
    plc_agv_no = ""
    plc_agv_mov_no = ""
    plc_vic_no = ""
    plc_interlock = ""

    plc_inspection_start = 0

"""
@dataclass
class RemoteCommData:
    spot_connected = False
    spot_serial_no = ""
    spot_power = ""
    spot_battery = ""
    spot_position = ""

    mes_connected = False
    mes_flag = ""
    mes_device_id = ""
    mes_data_type = ""
    mes_spool_point = ""
    mes_prod_date = ""
    mes_station_code = ""
    mes_seq = ""
    mes_body_no = ""
    mes_vic_no = ""
    mes_fsc = ""

    plc_connected = False
    plc_agv_no = ""
    plc_agv_mov_no = ""
    plc_vic_no = ""
    plc_interlock = ""
"""

@dataclass
class RemoteSetting:
    strIp: str = ""
    nPort: int = 0



#g_remote_comm_client_data_left = RemoteCommData()
#g_remote_comm_client_data_right = RemoteCommData()
#g_remote_comm_server_data = RemoteCommData()



