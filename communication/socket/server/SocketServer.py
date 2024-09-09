from dataclasses import dataclass
from communication.socket.server.ThreadServer import *
from enum import Enum

#@dataclass
#class SocketInfo:
#    conn =None
#    address=None

class EnumCommInfo(Enum):
    socket  = 0
    address = 1

class SocketServer:
    def __init__(self):

        self.info = None
        self.comm_info_list = []
        self.comm_Thread_list = []

        self.comm_thread_listen = None
        self.serverSocket = None

        self.is_run = False

        self.cbRecvdata =None

    def is_runnig(self):
        return self.is_run

    def ServerOpen(self,ip,port):
        address = (ip, port)
        if self.is_run == False:
            if self.comm_thread_listen is None:
                self.comm_thread_listen = ThreadSocketServerListen(address,self.callback_accept)
                self.comm_thread_listen.start()
                self.is_run =True
        else:
            print("server aleady run..")

    def server_close(self):
        if self.is_run == True:
            if self.comm_thread_listen.isRunning():
                self.comm_thread_listen.stop()
                self.comm_thread_listen.deleteLater()
                self.comm_thread_listen = None

            # 각 쓰레드 종료
            while len(self.comm_Thread_list) > 0:
                t = self.comm_Thread_list.pop()
                t.stop()
                t.deleteLater()
                t = None

            while len(self.comm_info_list) > 0:
                info = self.comm_info_list.pop()
                sock = info[EnumCommInfo.socket.value]
                close = False

                if sock is not None:
                    try:
                        sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    except:
                        pass
                    else:
                        sock.close()

            self.is_run=False

    def callback_accept(self, sock, address):
        sock.setblocking(False)
        info = (sock, address)

        thread = ThreadSocketServerComm(sock, address,self.cbRecvdata)
        thread.client_comm_close.connect()
        self.comm_info_list.append(info)
        self.comm_Thread_list.append(thread)

        thread.start()

    # callback func 등록시, accept 이전에 등록 필요.
    def Setrecvcallback(self,recv_callback):
        self.cbRecvdata = recv_callback

    # noinspection PyMethodMayBeStatic
    #def callback_recv(self, recv_data):
    #    print("recv_data:", recv_data)

    def callback_close(self,client_socket,address):
        if client_socket is not None and address is not None:
            index = -1

            for i in range(len(self.comm_info_list)):
                info = self.comm_info_list[i]
                if info[EnumCommInfo.socket.value] == client_socket:
                    index = i
                    break

            if index != -1:
                info = self.comm_info_list.pop(index)
                info[EnumCommInfo.socket.value].close()
                ip = info[EnumCommInfo.address.value][0]
                port = info[EnumCommInfo.address.value][1]
                print(f"connect client close...ip:{ip},port{port}")

    def sendmessage_(self, data: bytes):
        for th in self.comm_Thread_list:
            th.setsendmessage(data)

    def is_running(self):
        return self.is_run

    def is_connecting(self):
        connect = False
        if len(self.comm_Thread_list) > 0:
            connect = True
        return connect
