import socket
import time
from PyQt5.QtCore import QThread, pyqtSignal, QMutex


class ThreadSocketClientConnect(QThread):
    client_connect = pyqtSignal(bool, socket.socket)

    def __init__(self,server_addr):
        super().__init__()
        self.server_addr = server_addr

    def run(self):
        # server_addr = (self.data[0],self.data[1])
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        is_connect = False

        try:
            sock.connect(self.server_addr)
            sock.setblocking(False)
            is_connect =True
        except ConnectionRefusedError as refuse_e:
            print(refuse_e)
            print(f"connect error!ip:[{self.server_addr[0]}],port[{self.server_addr[1]}]")
        except Exception as e:
            print(e)
            print(f"connect error!ip:[{self.server_addr[0]}],port[{self.server_addr[1]}]")
        finally:
            self.client_connect.emit(is_connect, sock)

    def stop(self):
        self.quit()
        self.wait(10)


class ThreadSocketClientComm(QThread):
    client_comm_close = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.data = None
        self.sock = None
        self.cbRecv = None

        self.is_run = False
        self.mutex = QMutex()

        self.Buffer=[]
        self.currentMessage = None

    def SetInfo(self, client_sock, callback):
        self.mutex.lock()

        self.sock = client_sock
        self.cbRecv = callback

        self.mutex.unlock()

    def run(self):
        self.is_run = True
        error = ''

        while self.is_run == True:
            # send
            self.mutex.lock()
            if len(self.Buffer)>0 and self.currentMessage==None:
                self.currentMessage=self.Buffer.pop(0)

            if self.currentMessage!=None:
                try:
                    self.sock.send(self.currentMessage)
                    self.currentMessage = None
                except BlockingIOError:
                    pass
                except ConnectionError as e:
                    print(e)
                    break
            self.mutex.unlock()

            # recv
            self.mutex.lock()
            data = None
            try:
                data = self.sock.recv(4096)

                if len(data) == 0:
                    error = "서버연결종료."
                    break

                # callback..
                if self.cbRecv is not None:
                    self.cbRecv(data)
                    self.currentMessage = None
            except BlockingIOError:
                pass
            except ConnectionError as conn_e:
                error = str(conn_e)
                break
            except Exception as e:
                error = str(e)
                break

            self.mutex.unlock()

            time.sleep(0.1)

        # print("end...")
        self.client_comm_close.emit(error)

    def stop(self):
        self.quit()
        self.wait(10)

    def setsendmessage(self,message):
        self.mutex.lock()
        if len(message)>0:
            self.Buffer.append(message)
        self.mutex.unlock()
