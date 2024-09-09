from communication.socket.client.SocketClient import *
from communication.Remote.RemoteData import *


class RemoteClient(SocketClient):
    def __init__(self):
        super().__init__()
        self.Setrecvcallback(self.recvdata)
        self.remain_data = b''
        self.cbRecvDataProcess = None

        self.remoteRecvData = None

    def recvdata(self, data: bytes):
        """
        data(bytes) ->  RemoteCommMessageData
        """
        self.remain_data += data

        # test
        # print("client recv res_data",self.remain_data)

        start_index = self.remain_data.find(SOH)
        end_index = -1

        if start_index != -1:
            end_index = self.remain_data.find(ETX, start_index)

        # 온전한 정보가 다들어 왔을 경우
        if start_index != -1 and end_index != -1:
            req_data = self.remain_data[start_index:end_index + 1]
            self.remain_data = self.remain_data[end_index + 1:-1]

            recv_data = RemoteCommMessageData(RemoteCommCommandType.Req.value, b'', [])

            if req_data[0] is SOH[0]:
                index = req_data.find(STX)

                if index != -1:
                    recv_data.type = req_data[1:4]
                    recv_data.id = req_data[4:index]

                    start_index = index + 1
                    index = req_data.find(GS, start_index)

                    while index != -1:
                        body = RemoteCommBodyData()
                        data_index = req_data[start_index:index].find(US)

                        if data_index != -1:
                            body.data_type = req_data[start_index:start_index+data_index]
                            body.data = req_data[start_index+data_index+1:index]
                        else:
                            body.data_type = req_data[start_index:index]

                        start_index = index + 1
                        recv_data.body_data.append(body)
                        index = req_data.find(GS, start_index)

            # 파싱한 데이터를 토대로 데이터 취득 시작.
            # do processing callback 등록
            # print("client remain:", self.remain_data)
            if self.cbRecvDataProcess is not None:
                self.cbRecvDataProcess(recv_data)

    def setcallbackrecvdataprocess(self,call_back_func):
        self.cbRecvDataProcess = call_back_func

    def reqdata(self,data:RemoteCommMessageData):
        # joon_20240313 gma.... djEjgrp gkfRk...
        # parsing and set...
        if len(data.body_data)>0:
            byte_data = SOH+data.type + data.id+STX

            for b in data.body_data:
                body: RemoteCommBodyData = b
                byte_data += body.data_type + GS

            byte_data += ETX

            self.senddata(byte_data)
        else:
            print("wrong data_type...")

    def ReqPlcRemoteStatus(self):
        """
        make req data for plc_status.
        """
        if self.is_connect:
            req = RemoteCommMessageData(RemoteCommCommandType.Req.value, b'', [])
            req.type = RemoteCommCommandType.Req.value
            req.id = RemoteCommControllerType.controller_left.value

            # plc connect check.
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_connected.value
            req.body_data.append(body)

            # plc agv_no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_agv_no.value
            req.body_data.append(body)

            # plc agv_mov_no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_agv_mov_no.value
            req.body_data.append(body)

            # plc vic_no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_vic_no.value
            req.body_data.append(body)

            # plc interlock
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_interlock.value
            req.body_data.append(body)

            self.reqdata(req)
        else:
            print(f"{self.ReqPlcRemoteStatus.__name__}() error! not connected...")

    def ReqMesRemoteStatus(self):
        """
        make req data for mes_status.
        """
        if self.is_connect:
            req = RemoteCommMessageData(RemoteCommCommandType.Req.value, b'', [])
            req.type = RemoteCommCommandType.Req.value
            req.id = RemoteCommControllerType.controller_left.value

            # mes check.
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_connected.value
            req.body_data.append(body)

            # mes flag
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_flag.value
            req.body_data.append(body)

            # mes device_id
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_device_id.value
            req.body_data.append(body)

            # mes type
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_data_type.value
            req.body_data.append(body)

            # mes spool point
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_spool_point.value
            req.body_data.append(body)

            # mes prod date
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_prod_date.value
            req.body_data.append(body)

            # mes station code
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_station_code.value
            req.body_data.append(body)

            # mes seq
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_seq.value
            req.body_data.append(body)

            # mes body no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_body_no.value
            req.body_data.append(body)

            # mes vic no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_vic_no.value
            req.body_data.append(body)

            # mes fsc
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_fsc.value
            req.body_data.append(body)
        else:
            print(f"{self.ReqMesRemoteStatus.__name__}() error! not connected...")

    def ReqSpotRemoteStatus(self):
        """
        make req data for spot_status.
        """
        if self.is_connect:
            req = RemoteCommMessageData(RemoteCommCommandType.Req.value, b'', [])
            req.type = RemoteCommCommandType.Req.value
            req.id = RemoteCommControllerType.controller_left.value

            # spot check.
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_connected.value
            req.body_data.append(body)

            # spot serial
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_serial_no.value
            req.body_data.append(body)

            # spot power
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_power.value
            req.body_data.append(body)

            # spot battery
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_battery.value
            req.body_data.append(body)

            # spot position
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_position.value
            req.body_data.append(body)
        else:
            print(f"{self.ReqSpotRemoteStatus.__name__}() error! not connected...")


    def ReqRemoteStatus(self):
        """
        make req data for all device_status.
        send to remote server..
        """
        if self.is_connect:
            req = RemoteCommMessageData(RemoteCommCommandType.Req.value, b'', [])
            req.type = RemoteCommCommandType.Req.value
            req.id = RemoteCommControllerType.controller_left.value

            # plc check.
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_connected.value
            req.body_data.append(body)

            # plc agv_no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_agv_no.value
            req.body_data.append(body)

            # plc agv_mov_no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_agv_mov_no.value
            req.body_data.append(body)

            # plc vic_no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_vic_no.value
            req.body_data.append(body)

            # plc interlock
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.plc_interlock.value
            req.body_data.append(body)

            ############################################################

            # mes check.
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_connected.value
            req.body_data.append(body)

            # mes flag
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_flag.value
            req.body_data.append(body)

            # mes device_id
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_device_id.value
            req.body_data.append(body)

            # mes type
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_data_type.value
            req.body_data.append(body)

            # mes spool point
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_spool_point.value
            req.body_data.append(body)

            # mes prod date
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_prod_date.value
            req.body_data.append(body)

            # mes station code
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_station_code.value
            req.body_data.append(body)

            # mes seq
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_seq.value
            req.body_data.append(body)

            # mes body no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_body_no.value
            req.body_data.append(body)

            # mes vic no
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_vic_no.value
            req.body_data.append(body)

            # mes fsc
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.mes_fsc.value
            req.body_data.append(body)

            #####################################################

            # spot check.
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_connected.value
            req.body_data.append(body)

            # spot serial
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_serial_no.value
            req.body_data.append(body)

            # spot power
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_power.value
            req.body_data.append(body)

            # spot battery
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_battery.value
            req.body_data.append(body)

            # spot position
            body = RemoteCommBodyData()
            body.data_type = RemoteCommReqType.spot_position.value
            req.body_data.append(body)

            self.reqdata(req)

