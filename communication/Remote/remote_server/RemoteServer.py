from communication.socket.server.SocketServer import *
from communication.Remote.RemoteData import *
# from communication.remote_server.ThreadServer import *
# from communication.socket.SocketServer import *
# from communication.remote_client.RemoteData import *

class RemoteServer(SocketServer):
    def __init__(self):
        super().__init__()
        self.Setrecvcallback(self.recvdata)
        self.remain_data = b''
        self.cbRecvDataProcess = None

    def senddata(self, data: RemoteCommMessageData):
        """
        RemoteCommMessageData -> data(bytes)
        """
        byte_data = b''

        if len(data.body_data) > 0:
            byte_data = SOH+data.type + data.id+STX

            for b in data.body_data:
                body: RemoteCommBodyData = b
                byte_data += body.data_type + US + body.data + GS

            byte_data += ETX

            super().sendmessage_(byte_data)

    def recvdata(self, data: bytes):
        """
        data(bytes) ->  RemoteCommMessageData
        """
        self.remain_data += data

        start_index = self.remain_data.find(SOH)
        end_index = -1

        if start_index != -1:
            end_index = self.remain_data.find(ETX,start_index)

        # 온전한 정보가 다들어 왔을 경우
        if start_index != -1 and end_index != -1:
            req_data = self.remain_data[start_index:end_index+1]
            self.remain_data = self.remain_data[end_index+1:-1]

            recv_data = RemoteCommMessageData(RemoteCommCommandType.Req.value, b'', [])

            if req_data[0] is SOH[0]:
                index = req_data.find(STX)

                if index != -1:
                    recv_data.type = req_data[1:4]
                    recv_data.id = req_data[4:index]

                    start_index = index+1
                    index = req_data.find(GS, start_index)

                    while index != -1:
                        body = RemoteCommBodyData()
                        body.data_type = req_data[start_index:index]
                        body.data = b''
                        start_index = index+1
                        recv_data.body_data.append(body)
                        index = req_data.find(GS, start_index)

            # 파싱한 데이터를 토대로 데이터 취득 시작.
            # do processing callback 등록
            # print("server remain:", self.remain_data)
            if self.cbRecvDataProcess is not None:
                self.cbRecvDataProcess(recv_data)

    def setcallbackrecvdataprocess(self,callback_func):
        self.cbRecvDataProcess = callback_func

"""
class RemoteServer:
    def __init__(self):
        super().__init__()

        self.info = None
        self.comm_info_list = []
        self.comm_Thread_list = []
        
        self.comm_thread_listen = None
        self.serverSocket = None

        #self.mutex = QMutex()

        self.is_run = False

        self.recv_remain_data = ""

    def ServerOpen(self,ip,port):
        self.info=(ip,port)

        if self.comm_thread_listen is None:
            self.comm_thread_listen = ThreadWorkRemoteCommServerListen(self)
            self.comm_thread_listen.accept_func = self.callback_accept
            self.comm_thread_listen.start()


    def callback_accept(self,sock,address):
        sock.setblocking(False)
        info =(sock,address)

        self.comm_info_list.append(info)

        thread = ThreadWorkRemoteServerComm(sock,address)

        self.comm_Thread_list.append(thread)
        thread.callback = self.callback_recv

        thread.start()

    def client_close(self, conn, address):
        if conn is not None and address is not None:
            index = -1

            for i in range(len(self.comm_info_list)):
                info = self.comm_info_list[i]

                if info.conn == conn:
                    index = i
                    break

            if index != -1:
                info = self.comm_info_list.pop(index)
                info.conn.close()
"""