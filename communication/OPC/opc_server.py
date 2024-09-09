import threading

from opcua import Server
from opcua import ua
import time

class OPC_TAG:
    S600_RB1_I                      = 'S600_RB1_I'                      #
    S600_SPOT_RB1_I_HOME_POSI       = 'S600_SPOT_RB1_I_HOME_POSI'       # '도크에 앉아있는 상태'
    S600_SPOT_RB1_I_LAST_WORK_COMP  = 'S600_SPOT_RB1_I_LAST_WORK_COMP'  # '최종 작업완료'
    S600_SPOT_RB1_I_1ST_WORK_COMP   = 'S600_SPOT_RB1_I_1ST_WORK_COMP'   # 'Fender QR코드 촬영'
    S600_SPOT_RB1_I_2ND_WORK_COMP   = 'S600_SPOT_RB1_I_2ND_WORK_COMP'   # 'RR DR Hole 촬영(2군데)'
    S600_SPOT_RB1_I_3RD_WORK_COMP   = 'S600_SPOT_RB1_I_3RD_WORK_COMP'   # 'Side OTR QR코드 촬영''
    S600_SPOT_RB1_I_AUTORUNNING     = 'S600_SPOT_RB1_I_AUTORUNNING'     # 'SPOT POWER+MOTER ON
    S600_SPOT_RB1_I_BATTERY_LOW     = 'S600_SPOT_RB1_I_BATTERY_LOW'     # 'WARNING',
    S600_SPOT_RB1_I_TOTAL_ERR       = 'S600_SPOT_RB1_I_TOTAL_ERR'       # '종합 이상'
    S600_SPOT_RB1_I_EM_STOP         = 'S600_SPOT_RB1_I_EM_STOP'         # '비상정지',
    S600_SPOT_RB1_I_NON_INT         = 'S600_SPOT_RB1_I_NON_INT'         # 'AGV 간섭무'
    S600_SPOT_RB1_I_HEART_BIT       = 'S600_SPOT_RB1_I_HEART_BIT'       # HEARTBEAT


class OPCUAServer:
    def __init__(self, endpoint):
        self.server = Server()
        self.server.set_endpoint(endpoint)
        self.uri = "http://example.com/BIW"
        self.idx = self.server.register_namespace(self.uri)
        self.objects = self.server.get_objects_node()
        self.setup_tags()

    def setup_tags(self):
        self.tags = {
            OPC_TAG.S600_RB1_I: self.objects.add_variable(self.idx, OPC_TAG.S600_RB1_I, 0),
            OPC_TAG.S600_SPOT_RB1_I_HOME_POSI: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_HOME_POSI, 0),
            OPC_TAG.S600_SPOT_RB1_I_LAST_WORK_COMP: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_LAST_WORK_COMP, 0),
            OPC_TAG.S600_SPOT_RB1_I_1ST_WORK_COMP: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_1ST_WORK_COMP, 0),
            OPC_TAG.S600_SPOT_RB1_I_2ND_WORK_COMP: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_2ND_WORK_COMP, 0),
            OPC_TAG.S600_SPOT_RB1_I_3RD_WORK_COMP: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_3RD_WORK_COMP, 0),
            OPC_TAG.S600_SPOT_RB1_I_AUTORUNNING: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_AUTORUNNING, 0),
            OPC_TAG.S600_SPOT_RB1_I_BATTERY_LOW: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_BATTERY_LOW, 0),
            OPC_TAG.S600_SPOT_RB1_I_TOTAL_ERR: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_TOTAL_ERR, 0),
            OPC_TAG.S600_SPOT_RB1_I_EM_STOP: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_EM_STOP, 0),
            OPC_TAG.S600_SPOT_RB1_I_NON_INT: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_NON_INT, 0),
            OPC_TAG.S600_SPOT_RB1_I_HEART_BIT: self.objects.add_variable(self.idx, OPC_TAG.S600_SPOT_RB1_I_HEART_BIT, 0)
        }

        # 태그를 writable로 설정
        for tag in self.tags.values():
            tag.set_writable()

        # HEART_BIT를 1로 설정
        self.tags[OPC_TAG.S600_SPOT_RB1_I_HEART_BIT].set_value(ua.Variant(1, ua.VariantType.Int32))

    def start(self):
        self.server.start()
        print("OPC UA 서버가 시작되었습니다.")

        threading.Thread(target=self.change_tag_value).start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.server.stop()
            print("OPC UA 서버가 종료되었습니다.")

    def change_tag_value(self):
        while True:
            user_input = input("변경할 태그 이름과 값을 입력하세요 (예: S600_RB1_I 1): ")
            try:
                tag_name, value = user_input.split()
                value = int(value)
                if tag_name in self.tags:
                    self.tags[tag_name].set_value(ua.Variant(value, ua.VariantType.Int32))
                    print(f"{tag_name} set to {value}")
                else:
                    print(f"태그 이름 {tag_name}을(를) 찾을 수 없습니다.")
            except Exception as e:
                print(f"입력 오류: {e}")


if __name__ == "__main__":
    server = OPCUAServer("opc.tcp://localhost:4840")
    server.start()
