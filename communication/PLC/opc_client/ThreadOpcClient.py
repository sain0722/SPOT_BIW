
# from opcua import Client
import time
import threading
from communication.PLC.opc_client.DLLOPCClient import DLLOPCClient
import pythoncom


class ThreadOpcClientConnect(threading.Thread):
    # client_connect_opc = pyqtSignal(bool, Client) #20240527

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.cbClientConnectOpc = None

    def run(self):
        is_connect = False
        # client = Client(self.url)
        client = DLLOPCClient()

        try:
            # client.connect()
            # client.Init('Kepware.KEPServerEX.V6','localhost')
            client.Init('RSLinx Local OPC Server', 'localhost')
            is_connect = True
        except Exception as e:
            print(e)
            time.sleep(0.3)

        # self.client_connect_opc.emit(is_connect,client)# 20240527
        if self.cbClientConnectOpc != None:
            self.cbClientConnectOpc(is_connect,client)

    def stop(self):
        time.sleep(0.5)

    def setCallbackClientConnectOpc(self, cbConnect):
        self.cbClientConnectOpc = cbConnect


class ThreadOpcConnectAliveCheck(threading.Thread):
    # client_alive_check = pyqtSignal(bool)#20240527

    def __init__(self,client: DLLOPCClient,check_node):
        super().__init__()
        self.refClient = client
        self.check_node = check_node
        self.is_run = False
        self.cbClientAliveCheck = None

    def run(self):
        self.is_run = True

        while self.is_run:
            try:
                self.check_node.get_value()
            except:
                print("opc server alive check fail...")
                self.is_run = False

            #self.client_alive_check.emit(self.is_run)
            if self.cbClientAliveCheck != None:
                self.cbClientAliveCheck(self.is_run)

        time.sleep(0.5)

    def stop(self):
        self.is_run = False
        self.cbClientAliveCheck = None
        time.sleep(0.5)

    def setCallbackClientAliveCheck(self, cbCheck):
        self.cbClientAliveCheck = cbCheck


class ThreadOpcDataRead(threading.Thread):
    def __init__(self,client : DLLOPCClient , read_items : list):
        super().__init__()
        self.refClient = client
        self.read_items = read_items
        self.is_run = False
        self.cbClientItemsRead = None
        self.read_items_result = []
        self.mutex = threading.Lock()

        #self.refClient.readitems(self.read_items, self.read_items_result)


    def run(self):
        self.is_run = True
        result = []

        while self.is_run:
            try:
                #self.check_node.get_value()
                self.refClient.readitems(self.read_items, self.read_items_result)
            except:
                print("opc server alive check fail...")
                self.is_run = False

            ##self.client_alive_check.emit(self.is_run)
            if result != self.read_items_result:
                if self.cbClientItemsRead != None:
                    self.cbClientItemsRead(self.read_items_result)

                # self.read_items_result = result
                result = self.read_items_result
            #do 50ms..
            time.sleep(0.05)

        self.refClient.CoUnInitializeEx()
        time.sleep(0.5)


    def stop(self):
        self.is_run = False
        self.cbClientItemsRead = None
        time.sleep(0.5)

    def setCallbackOPCDataRead(self,cbItemsRead):
        self.cbClientItemsRead = cbItemsRead
