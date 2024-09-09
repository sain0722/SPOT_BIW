import time

from communication.PLC.opc_client.ThreadOpcClient import *
from communication.PLC.OpcClientData import *

from communication.PLC.opc_client.DLLOPCClient import VARIANT
import pythoncom

# from Functions.utils.utils import g_TEST_LOG


class OpcClient:
    def __init__(self):
        super().__init__()
        self.url = ""
        #self.client: Client = None #joon_20240614
        self.client: DLLOPCClient = None
        self.is_connect = False

        # connect thread
        self.thread_conn = None
        self.alive_check_node = None
        self.thread_alive_check = None

        # send,recv thread
        self.thread_comm = None

        # recv callback func.
        self.cbRecvdata = None

        # current read data
        self.opc_client_data = OpcClientReadData()
        self.list_read_node = []
        self.read_subscribe_handler = None

        # joon
        # 추후 필요정도를 확인하여 외부설정을 할수있도록 접근함수 구상요망
        self.auto_reconnect = True

    def connect(self, url: str):
        """
        opc 서버 연결
        param
        url: str
        """
        if self.is_connect == False:
            if self.thread_conn is None:
                self.url = url
                self.thread_conn = ThreadOpcClientConnect(self.url)
                # self.thread_conn.client_connect_opc.connect(self.on_connected)
                self.thread_conn.setCallbackClientConnectOpc(self.on_connected)
                self.thread_conn.start()

    def SetReadDataCallback(self, callback):
        """
        opc서버에서 값을 read시, 호출할 callback함수등록 함수.
        callback함수타입 -> callback(OpcClientReadData)
        """
        self.cbRecvdata = callback

    def disconnect(self):
        """
        opc서버 연결 해제 함수
        """
        if self.is_connect is True:
            if self.read_subscribe_handler:
                try:
                    self.read_subscribe_handler.delete()
                except:
                    print(f"{self.disconnect.__name__}() error! subscribe delete fail, but ignore..")
                    # g_TEST_LOG.set_message(f"{self.disconnect.__name__}() error! subscribe delete fail, but ignore..")
                    # print(f"{self.disconnect.__name__}() error! subscribe delete fail, but ignore..")

                self.read_subscribe_handler = None

            if self.thread_alive_check:
                self.thread_alive_check.stop()
                self.thread_alive_check = None

            if self.client:
                try:
                    self.client.disconnect()
                except:
                    print(f"{self.disconnect.__name__}() error! opc client delete fail,but ignore..")
                    # g_TEST_LOG.set_message(f"{self.disconnect.__name__}() error! opc client delete fail,but ignore..")
                    # print(f"{self.disconnect.__name__}() error! opc client delete fail,but ignore..")
                self.client = None

            self.list_read_node.clear()
            self.thread_alive_check = None

            self.is_connect = False

    #def on_connected(self, is_connect: bool, client_: Client):#joon_20240614
    def on_connected(self, is_connect: bool, client_: DLLOPCClient):
        """
        ThreadOpcClient 쓰레드에서 opc서버 연결 시도후 호출 함수
        opc서버 연결시 subscribe 등록할 노드 정의 및 subscribe설정을 진행.
        :param
            is_connect: True or False connect result.
            client_: opcClient object
        """
        if self.thread_conn:
            self.thread_conn.stop()
            self.thread_conn = None

        if self.read_subscribe_handler:
            try:
                self.read_subscribe_handler.delete()
            except:
                print(f"{self.on_connected.__name__}() error! opc client delete fail,but ignore..")
                # g_TEST_LOG.set_message(f"{self.on_connected.__name__}() error! opc client delete fail,but ignore..")
                # print(f"{self.on_connected.__name__}() error! opc client delete fail,but ignore..")
            self.read_subscribe_handler = None

        if self.thread_alive_check:
            self.thread_alive_check.stop()
            self.thread_alive_check = None

        if self.client:
            try:
                #self.client.disconnect() #joon_20240614
                self.client.__del__()
            except:
                print(f"{self.on_connected.__name__}() error! opc client delete fail,but ignore..")
            self.client = None

        self.is_connect = is_connect

        if self.is_connect:
            # joon_20240614
            self.client = client_

            self.client.additem("[OPC]Program:MainProgram.M1")
            self.client.additem("[OPC]Program:MainProgram.M2")
            #self.client.additem("Simulation Examples.Functions.server_alive")
            #self.client.additem("Simulation Examples.Functions.plc_agv_no")
            #self.client.additem("Simulation Examples.Functions.plc_agv_mov_no")
            #self.client.additem("Simulation Examples.Functions.plc_vic_no")
            #self.client.additem("Simulation Examples.Functions.plc_interlock")
            #self.client.additem("Simulation Examples.Functions.plc_inspection_start")

            read_list = []
            read_list.append("[OPC]Program:MainProgram.M1")
            read_list.append("[OPC]Program:MainProgram.M2")
            #read_list.append("Simulation Examples.Functions.server_alive")
            #read_list.append("Simulation Examples.Functions.plc_agv_no")
            #read_list.append("Simulation Examples.Functions.plc_agv_mov_no")
            #read_list.append("Simulation Examples.Functions.plc_vic_no")
            #read_list.append("Simulation Examples.Functions.plc_interlock")
            #read_list.append("Simulation Examples.Functions.plc_inspection_start")

            #20240704
            var = VARIANT()
            var.tag.tagVARIANT.vt = pythoncom.VT_I2
            var.tag.tagVARIANT.union.iVal = 1

            #20240618
            self.thread_opc_data_read = ThreadOpcDataRead(self.client, read_list)
            self.thread_opc_data_read.setCallbackOPCDataRead(self.opc_read_update)
            self.thread_opc_data_read.start()

            time.sleep(10000)
            """
            # joon
            # 통신할 노드 태그 협의시 수정요망
            self.client = client_
            # 연결 확인용 값확인 node
            self.alive_check_node = self.client.get_node("ns=2;s=Simulation Examples.Functions.server_alive")

            self.thread_alive_check = ThreadOpcConnectAliveCheck(self.client, self.alive_check_node)
            # self.thread_alive_check.client_alive_check.connect(self.check_alive)
            self.thread_alive_check.setCallbackClientAliveCheck(self.check_alive)
            self.thread_alive_check.start()

            self.addchecknode_("ns=2; s=Simulation Examples.Functions.plc_agv_no")
            self.addchecknode_("ns=2; s=Simulation Examples.Functions.plc_agv_mov_no")
            self.addchecknode_("ns=2;s=Simulation Examples.Functions.plc_vic_no")
            self.addchecknode_("ns=2;s=Simulation Examples.Functions.plc_interlock")
            self.addchecknode_("ns=2;s=Simulation Examples.Functions.plc_inspection_start")

            self.read_subscribe_handler = self.client.create_subscription(100, self)
            self.read_subscribe_handler.subscribe_data_change(self.list_read_node)
            """
        else:
            if self.auto_reconnect:
                self.reconnect()

    def is_connecting(self):
        return self.is_connect

    def check_alive(self, connect_alive: bool):
        if connect_alive == False:
            self.disconnect()
            self.reconnect()

    def reconnect(self):
        # print("try reconnect!")
        self.connect(self.url)

    def addchecknode_(self, node_id: str):
        """
        opc server와 통신할 node객체 생성
        param
            node_id: str -> ex) "ns=2; s=Simulation Examples.Functions.plc_agv_no"
                                "ns=namesapce s=node name"
        """
        if self.client:
            is_exist = any(str(node) == node_id for node in self.list_read_node)

            if is_exist is False:
                new_node = self.client.get_node(node_id)
                self.list_read_node.append(new_node)
            else:
                print(f"already exist node..id[{node_id}]")

    def datachange_notification(self, node, val, data):
        """
        subscribe_handler 를 생성할 때 등록 함수

        :param
            node: Node object
            val:  Node value
            data: Node detail data.
        """
        is_exist = any(str(node_) == str(node) for node_ in self.list_read_node)

        if is_exist:
            index = 0
            for node_ in self.list_read_node:
                if node == node_:
                    break
                index += 1

            if index == OpcClientReadDataIndex.opc_avg_no.value:
                self.opc_client_data.opc_avg_no = val

            if index == OpcClientReadDataIndex.opc_avg_mov_no.value:
                self.opc_client_data.opc_avg_mov_no = val

            if index == OpcClientReadDataIndex.opc_vic_no.value:
                self.opc_client_data.opc_vic_no = val

            if index == OpcClientReadDataIndex.opc_interlock.value:
                self.opc_client_data.opc_interlock = val

            if index == OpcClientReadDataIndex.opc_inspection_start.value:
                self.opc_client_data.opc_inspection_start = val

            if self.cbRecvdata:
                self.cbRecvdata(self.opc_client_data)
        else:
            print(f"unexpected node value recv.[{str(node)}]")

    def opc_read_update(self, result : list):

        for i in range(len(result)):
            item:VARIANT = result[i]

            #dictionary가 괜찮을거 같긴한데...
            val = self.get_value_from_variant(item)

            if i == 0:
                self.opc_client_data.opc_avg_no = val
            elif i == 1:
                self.opc_client_data.opc_avg_mov_no = val
            elif i == 2:
                self.opc_client_data.opc_vic_no = val
            elif i == 3:
                self.opc_client_data.opc_interlock = val
            elif i == 4:
                self.opc_client_data.opc_inspection_start = val

        if self.cbRecvdata:
            self.cbRecvdata(self.opc_client_data)

    def get_value_from_variant(self,item:VARIANT):
        if item.tag.tagVARIANT.vt == pythoncom.VT_NULL:
            val = None
        elif item.tag.tagVARIANT.vt == pythoncom.VT_I2:
            val = item.tag.tagVARIANT.union.iVal
        elif item.tag.tagVARIANT.vt == pythoncom.VT_I4:
            val = item.tag.tagVARIANT.union.lVal
        elif item.tag.tagVARIANT.vt == pythoncom.VT_R4:
            val = item.tag.tagVARIANT.union.fltVal
        elif item.tag.tagVARIANT.vt == pythoncom.VT_R8:
            val = item.tag.tagVARIANT.union.dblVal
        elif item.tag.tagVARIANT.vt == pythoncom.VT_BSTR:
            val = item.tag.tagVARIANT.union.bstrVal
        elif item.tag.tagVARIANT.vt == pythoncom.VT_BOOL:
            val = item.tag.tagVARIANT.union.boolVal
        elif item.tag.tagVARIANT.vt ==pythoncom.VT_DATE:
            val = item.tag.tagVARIANT.union.date
        else:
            val = None

        # print(val)

        return val