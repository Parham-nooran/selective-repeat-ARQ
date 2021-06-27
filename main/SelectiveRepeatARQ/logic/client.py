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
import time
from threading import Thread, Lock
import struct
from collections import OrderedDict

FORMAT = "utf-8"
LOCK = Lock()
HOST = socket.gethostbyname(socket.gethostname())
PORT = 5050
ADDRESS = (HOST, PORT)


def client_program(fieldLength=5):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    address = "D:\\Users\\shahram\\test.txt"
    window = Window(fieldLength)
    frameManager = FrameManager(client_socket, address, window)
    ackReceiver = AckReceiver(window, frameManager, client_socket)
    start = time.time()
    frameManager.start()
    ackReceiver.start()
    frameManager.join()
    ackReceiver.join()
    end = time.time()
    print("End all")
    print(f"Time to send all the data : { (end - start) * 1000} ms")
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
        self.packet = struct.pack("=I", self.sequenceNumber) + struct.pack("=H", self.fcs) + self.data.encode(FORMAT)

    @staticmethod
    def generateFCS():
        # TODO
        return 4


class Window:
    def __init__(self, dataSize, windowSize=None):
        self.nextFrame2send = 0
        self.sentPackets = 0
        self.expectedAck = 0
        self.dataSize = dataSize
        self.maxWindowSize = 2 ** (dataSize - 1)
        self.transmittedFrames = OrderedDict()
        self.isTransmitting = True
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)

    def isNotEmpty(self):
        return len(self.transmittedFrames) > 0

    def saveNumber(self, seqNumber):
        self.transmittedFrames[seqNumber] = [None, False]
        self.nextFrame2send += 1
        self.nextFrame2send %= 2 ** self.dataSize
        self.sentPackets += 1

    def markAcked(self, seqNumber):
        with LOCK:
            print("Passed lock")
            if seqNumber in self.transmittedFrames.keys():
                self.transmittedFrames[seqNumber][1] = True
                print(f"Marked{seqNumber}")


    def stop(self, seqNumber):
        with LOCK:
            # print(self.transmittedFrames)
            if seqNumber == self.expectedAck:
                temp = self.transmittedFrames.copy()
                for sNum, value in temp.items():
                    # print(sNum, value)
                    if value[1]:
                        del self.transmittedFrames[sNum]
                    else:
                        break
                self.expectedAck = self.nextFrame2send if len(self.transmittedFrames) == 0\
                    else list(self.transmittedFrames.keys())[0]
                # print(self.expectedAck)
            # print(self.transmittedFrames)


class FrameManager(Thread):
    HEADER_SIZE = 6

    def __init__(self, client_socket, fileAddress, window):
        Thread.__init__(self)
        self.frames = []
        self.fileAddress = fileAddress
        # self.packetSize = window.dataSize + FrameManager.HEADER_SIZE
        self.window = window
        self.client_socket = client_socket

    def makePackets(self):
        file = open(self.fileAddress, "r")
        while True:
            data = file.read(self.window.dataSize)
            if not data:
                break
            self.frames.append(Frame(len(self.frames) % 2 ** self.window.dataSize, data))

    def sendAgain(self, seqNum):
        self.window.transmittedFrames[seqNum][0] = time.time()
        self.client_socket.sendall(self.frames[seqNum].packet)

    def run(self):
        self.makePackets()
        packetCount = 0
        self.client_socket.sendall(struct.pack("=I", (len(self.frames)*self.window.dataSize)) +
                                   struct.pack("=H", self.window.dataSize))
        while packetCount < len(self.frames):
            if len(self.window.transmittedFrames.keys()) < self.window.maxWindowSize:
                # print("Transmitted frames size : ", len(self.window.transmittedFrames.keys()))
                self.window.saveNumber(packetCount % 2 ** self.window.dataSize)
                SingleFrame(self.client_socket, self.frames[packetCount], self.window).start()
                packetCount += 1
        while True:
            if len(self.window.transmittedFrames) == 0:
                self.window.isTransmitting = False
                break
        # self.client_socket.close()
        print("End FrameManager")


class SingleFrame(Thread):
    def __init__(self, client_socket, frame, window, timeOut=3):
        Thread.__init__(self)
        self.frame = frame
        self.window = window
        self.timeOut = timeOut
        self.client_socket = client_socket

    def timeOutProtocol(self):
        while not self.window.transmittedFrames[self.frame.sequenceNumber][1]:
            if time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0] > self.timeOut:
                # print(self.window.transmittedFrames)
                # print("Elapsed : ", time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0])
                self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
                self.client_socket.sendall(self.frame.packet)


    def run(self):
        self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
        self.client_socket.sendall(self.frame.packet)
        # self.timeOutProtocol()
        self.window.stop(self.frame.sequenceNumber)
        # print("End SingleFrame")


class AckReceiver(Thread):
    def __init__(self, window, frameManager, client_socket):
        Thread.__init__(self)
        self.window = window
        self.client_socket = client_socket
        self.frameManager = frameManager

    def run(self):
        while self.window.isTransmitting:
            ack = self.client_socket.recv(1024)
            if not ack:
                break
            print("Received ack", self.parseAck(ack))
            # print(self.window.transmittedFrames[self.parseAck(ack)[1]])
            typeOfAck, seqNum = self.parseAck(ack)
            if typeOfAck:
                self.window.markAcked(seqNum)
            else:
                self.frameManager.sendAgain(seqNum)
            # except Exception as error:
            #     print("Could not receive the packet")
            #     print(error)
        print("End AckReceiver")
        self.client_socket.close()


    @staticmethod
    def parseAck(ack):
        return struct.unpack("=?", ack[:1])[0], struct.unpack("=I", ack[1:5])[0]


# if __name__ == '__main__':
#     for i in range(5):
#         client_program(i+2)
# client_program(9)
# if __name__ == '__main__':
#
#     # temp = Window(3)
#     # n = 10
#     # for i in range(n)[::2]:
#     #     temp.saveNumber(i)
#     #     temp.saveNumber(i+1)
#     # temp.stop(2)
#     # message = "Hello, world"
#     file = "D:\\Users\\shahram\\test.txt"
#     f = open(file, "rb")
#     message = f.read(3)
#     frame = Frame(1, message)
#     print(frame.packet)
    # print(data)
    # received = struct.pack("=I", 5) + struct.pack("=H", 4) + message
    # print(received)
    # seqNum = struct.unpack("=I", received[:4])
    # fcs = struct.unpack("=H", received[4:6])
    # data = received[6:]
    # print(seqNum[0], fcs[0], data.decode())

# if __name__ == '__main__':