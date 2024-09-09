from dataclasses import dataclass
from enum import Enum


class OpcClientReadKey(Enum):
    opc_avg_no = "opc_avg_no"
    opc_avg_mov_no = "opc_avg_mov_no"
    opc_vic_no = "opc_vic_no"
    opc_interlock = "opc_interlock"

class OpcClientWriteKey(Enum):
    opc_avg_no = "opc_avg_no"
    opc_avg_mov_no = "opc_avg_mov_no"
    opc_vic_no = "opc_vic_no"
    opc_interlock = "opc_interlock"

class OpcClientReadDataIndex(Enum):
    opc_avg_no = 0
    opc_avg_mov_no = 1
    opc_vic_no = 2
    opc_interlock = 3

    opc_inspection_start = 4


@dataclass
class OpcClientReadData:
    opc_avg_no = ""
    opc_avg_mov_no = ""
    opc_vic_no = ""
    opc_interlock = ""

    opc_inspection_start = 0

@dataclass
class OpcSetting:
    strServerUrl: str = ""


