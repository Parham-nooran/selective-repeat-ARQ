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
    ackReceiver.start()
    frameManager.start()
    ackReceiver.join()
    frameManager.join()
    end = time.time()
    print("End all")
    print(f"Time to send all the data : { (end - start) * 1000} ms")


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
        # self.nextFrame2send = 0
        # self.sentPackets = 0
        # self.expectedAck = 0
        self.dataSize = dataSize
        self.maxWindowSize = 2 ** (dataSize - 1)
        self.transmittedFrames = {}
        # self.lastAcked = 0
        self.isTransmitting = True
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)

    def isNotEmpty(self):
        return len(self.transmittedFrames) > 0

    def saveNumber(self, seqNumber):
        self.transmittedFrames[seqNumber] = [None, False]
        # self.expectedAck = seqNumber
        # self.nextFrame2send += 1
        # self.nextFrame2send %= 2 ** self.dataSize
        # self.sentPackets += 1

    def markAcked(self, seqNumber):
        with LOCK:
            print("Passed ack")
            if seqNumber > list(self.transmittedFrames.keys())[0]:
                for key in self.transmittedFrames.keys():
                    if key < seqNumber:
                        self.transmittedFrames[key][1] = True
                    else:
                        break
            elif seqNumber < list(self.transmittedFrames.keys())[0]:
                for key in self.transmittedFrames.keys():
                    if list(self.transmittedFrames.keys())[0] <= key < 2 ** self.dataSize or key < seqNumber:
                        self.transmittedFrames[key][1] = True
                    else:
                        break
            print(f"Marked {seqNumber}")


    def stop(self):
        temp = self.transmittedFrames.copy()
        for key, value in temp.items():
            if value[1]:
                del self.transmittedFrames[key]
            else:
                break


class FrameManager(Thread):
    HEADER_SIZE = 6

    def __init__(self, client_socket, fileAddress, window):
        Thread.__init__(self)
        self.frames = []
        self.fileAddress = fileAddress
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
            # print(self.window.transmittedFrames, len(self.window.transmittedFrames), self.window.maxWindowSize)
            if len(self.window.transmittedFrames.keys()) < self.window.maxWindowSize:
                # print("[Sending] Client is sending a packet ...")
                self.window.saveNumber(packetCount % 2 ** self.window.dataSize)
                SingleFrame(self.client_socket, self.frames[packetCount], self.window).start()
                time.sleep(0.00000001)
                packetCount += 1
        print(self.window.transmittedFrames)
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
                # print("Elapsed : ", time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0])
                self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
                self.client_socket.sendall(self.frame.packet)
        self.window.stop(self.frame.sequenceNumber)


    def run(self):
        self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
        self.client_socket.sendall(self.frame.packet)
        # print(f"Sent {self.frame.packet}")
        # self.timeOutProtocol()
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
            typeOfAck, seqNum = self.parseAck(ack)
            if typeOfAck:
                while not self.window.transmittedFrames[(seqNum - 1) % 2 ** self.window.dataSize][1]:
                    self.window.markAcked(seqNum)
                self.window.stop()
            else:
                self.frameManager.sendAgain(seqNum)
        print("End AckReceiver")
        self.client_socket.close()


    @staticmethod
    def parseAck(ack):
        return struct.unpack("=?", ack[:1])[0], struct.unpack("=I", ack[1:5])[0]


for j in range(1, 8):
    for i in range(2):
        client_program(j)
        time.sleep(1)
