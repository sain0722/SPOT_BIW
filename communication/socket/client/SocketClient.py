from communication.socket.client.ThreadClient import *

class SocketClient:
    def __init__(self):
        self.sock = None
        self.server_address = None
        self.is_connect = False

        # connect thread
        self.thread_conn = None
        # send,recv thread
        self.thread_comm = None
        # recv callback func.
        self.cbRecvdata = None

        self.auto_reconnect =True
    def __del__(self):
        if self.sock is not None:
            self.sock.close()

        if self.thread_conn is not None:
            self.thread_conn.stop()

        if self.thread_comm is not None:
            self.thread_comm.stop()

    def connect(self, server_address):
        if self.is_connect == False:
            if self.thread_conn is None:
                self.server_address = server_address
                self.thread_conn = ThreadSocketClientConnect(server_address)
                self.thread_conn.client_connect.connect()
                self.thread_conn.start()
            else:
                print("please wait connecting...")
        else:
            print("aleady connected...")

    # callback func 등록시, connect 이전에 등록 필요.
    def Setrecvcallback(self,recv_callback):
        self.cbRecvdata = recv_callback

    def on_connected(self, is_connect: bool, sock: socket.socket):
        # 이전 연결이 살아있다면 close
        if self.sock is not None:
            self.sock.close()
            self.sock = None

        self.is_connect = is_connect
        self.sock = sock

        print(f"socket connect:[{self.is_connect}]")

        # send,recv thread create and running..
        if self.is_connect is True:
            if self.thread_comm is None:
                self.thread_comm = ThreadSocketClientComm()

            self.thread_comm.SetInfo(self.sock, self.cbRecvdata)
            self.thread_comm.client_comm_close.connect()
            self.thread_comm.start()
        else:
            self.reconnect()

    def reconnect(self):
        # 쓰레드 종료
        if self.thread_conn != None:
            if self.thread_conn.isRunning() is True:
                self.thread_conn.stop()
            self.thread_conn = None

        if self.sock != None:
            self.sock.close()
            self.sock = None

        self.connect(self.server_address)

    def SetAutoReconnect(self, reconnect: bool):
        self.auto_reconnect = reconnect

    def commclose(self, str=""):
        if self.thread_conn is not None:
            if self.thread_conn.isRunning() is True:
                self.thread_conn.stop()
        self.thread_conn = None

        if self.thread_comm is not None:
            if self.thread_comm.isRunning() is True:
                self.thread_comm.stop()
        self.thread_comm = None

        if self.sock is not None:
            self.sock.close()
            self.sock = None

        self.is_connect=False

        # log...
        print(str)

        # re connect.
        if self.auto_reconnect is True:
            self.reconnect()

    def senddata(self, data: bytes):
        """
        data: type byte string. byte[]
        """
        if self.thread_comm is not None:
            self.thread_comm.setsendmessage(data)

    # def recvdata(self, data):
        # print("recv data:", data)

    def is_connecting(self):
        return self.is_connect
