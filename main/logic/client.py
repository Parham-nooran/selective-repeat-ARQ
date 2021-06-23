# import socket
# import time
#
# HOST = socket.gethostname()
# # '127.0.0.1'
# PORT = 1234
#
#
# def send():
#     client_socket = socket.socket()
#     client_socket.connect((HOST, PORT))
#     for i in range(10):
#         client_socket.send(str(i).encode())
#     client_socket.close()
#     print("end Client")
import socket
from threading import *
import struct

HOST = socket.gethostname()  # '127.0.0.1'  # The server's hostname or IP address
PORT = 1234  # The port used by the server


def client_program():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    client_socket.connect((HOST, PORT))
    # for i in range(4):
    #     client_socket.sendall(f'Frame{i}'.encode())
    #     data = client_socket.recv(1024)
    #
    #     print('Received ack', repr(data))
    #
    # for i in range(6):
    #     client_socket.sendall(bytes(32))
    #     # f'Frame{i}'.encode()
    #     data = client_socket.recv(1024)
    #
    #     print('Received ack', repr(data))




class Frame:
    def __init__(self, sequenceNumber, data):
        self.sequenceNumber = sequenceNumber
        self.data = data
        self.fcs = self.generateFCS()

    @staticmethod
    def generateFCS():
        #TODO
        return "10101"

    def pack(self):
        return struct.pack("=I", self.sequenceNumber) + struct.pack("=H", self.fcs) + self.data


class Window:
    def __init__(self, fieldLength, windowSize=None):
        self.nextFrame2send = 0
        self.expectedAck = 0
        self.sentPackets = 0
        self.fieldLength = fieldLength
        self.maxWindowSize = 2 ** (fieldLength - 1)
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)

    def send(self):
        self.nextFrame2send += 1
        self.nextFrame2send %= 2 ** self.fieldLength
        self.sentPackets += 1


class FrameManager(Thread):
    def __init__(self, file, packetSize, maxWindowSize):
        Thread.__init__(self)
        self.frames = []
        self.packetCount = 0
        self.file = file
        self.packetSize = packetSize
        self.maxWindowSize = maxWindowSize

    def makePackets(self):
        f = open(self.file, "r")
        while True:
            data = f.read(self.packetSize)
            if not data:
                break
            self.frames.append(Frame(self.packetCount % self.maxWindowSize, data))
            self.packetCount += 1

    def run(self):
        pass


class AckReceiver(Thread):
    def __init__(self):
        Thread.__init__(self)


if __name__ == '__main__':
    pass
    # message = "Hello, world"
    # file = "D:\\Users\\shahram\\test.txt"
    # f = open(file, "rb")
    # message = f.read(3)
    # print(data)
    # received = struct.pack("=I", 5) + struct.pack("=H", 4) + message
    # print(received)
    # seqNum = struct.unpack("=I", received[:4])
    # fcs = struct.unpack("=H", received[4:6])
    # data = received[6:]
    # print(seqNum[0], fcs[0], data.decode())


# client_program()
