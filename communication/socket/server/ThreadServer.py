import socket
import time
from PyQt5.QtCore import QThread,pyqtSignal,QMutex

class ThreadSocketServerListen(QThread):
    def __init__(self,server_address:tuple,callback):
        super().__init__()
        self.socket = None
        self.is_open =False
        self.server_address = server_address
        self.cbAccept = callback

    def run(self):
        self.is_open = True

        if self.socket is not None:
            self.socket.close()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.socket.bind((self.server_address[0], self.server_address[1]))
        self.socket.listen()

        while self.is_open:
            try:
                client_socket, address = self.socket.accept()
            except BlockingIOError:
                pass
            except Exception as e:
                print(e)
            else:
                if self.cbAccept is not None:
                    self.cbAccept(client_socket, address)

            time.sleep(0.1)

    def stop(self):
        if self.is_open is True:
            self.is_open = False

        if self.socket is not None:
            self.socket.close()
            self.socket = None

        self.quit()
        self.wait(10)


class ThreadSocketServerComm(QThread):
    client_comm_close = pyqtSignal(str)

    def __init__(self,socket,address,callback_recv):
        super().__init__()
        self.is_run=False

        self.socket = socket
        self.address = address
        #self.callback= callback
        self.cbRecv = callback_recv

        self.mutex= QMutex()

        self.Buffer=[]
        self.currentMessage=None

    def run(self):
        self.is_run=True

        error =''

        while self.is_run==True:
            ##send...
            self.mutex.lock()

            if len(self.Buffer)>0 and self.currentMessage==None:
                self.currentMessage = self.Buffer.pop(0)

            if self.currentMessage!=None:
                try:
                    self.socket.send(self.currentMessage)
                    self.currentMessage = None
                except BlockingIOError:
                    pass
                except ConnectionError as e:
                    error =str(e)
                    break
                except Exception as e:
                    error = str(e)
                    break

            self.mutex.unlock()

            ##recv
            try:
                data = self.socket.recv(4096)

                if len(data) == 0:
                    break

                if self.cbRecv is not None:
                    self.cbRecv(data)
            except BlockingIOError:
                continue
            except ConnectionError as e:
                error = str(e)
                break
            except Exception as e:
                error = str(e)
                break

            time.sleep(0.1)

        # recv동안 소켓에러 발생시 소켓해제를 위하여.
        # socket close..
        # self.commMes.client_close(self.conn, self.address)
        # self.cbClose(self.socket, self.address)
        self.client_comm_close.emit(error)

    def stop(self):
        self.is_run=False
        self.quit()
        self.wait(10)

    def setsendmessage(self,message):
        self.mutex.lock()

        if len(message)>0:
            self.Buffer.append(message)

        self.mutex.unlock()

