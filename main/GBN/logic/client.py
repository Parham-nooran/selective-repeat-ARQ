import socket
import time
import random
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
    print(f"Elapsed time to send the data : {(end - start) * 1000} ms")


class Window:
    def __init__(self, dataSize, windowSize=None):
        self.sentPackets = 0
        self.expectedAck = 0
        self.dataSize = dataSize
        self.maxWindowSize = (2 ** dataSize) - 1
        self.transmittedFrames = {}
        self.lastAcked = 0
        self.isTransmitting = True
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)

    def isNotEmpty(self):
        return len(self.transmittedFrames) > 0

    def saveNumber(self, seqNumber):
        self.transmittedFrames[seqNumber] = [None, False]
        self.expectedAck = seqNumber
        self.sentPackets += 1

    def markAcked(self, seqNumber):
        with LOCK:
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
        # print(temp)
        for key, value in temp.items():
            if value[1]:
                del self.transmittedFrames[key]
            else:
                break
        # print(self.transmittedFrames)


class Frame:
    def __init__(self, sequenceNumber, data=None, pBit=None):
        self.sequenceNumber = sequenceNumber
        self.data = data
        self.fcs = self.generateFCS()
        if pBit is not None:
            self.packet = struct.pack("=I", self.sequenceNumber) + struct.pack("=?", pBit)
        else:
            self.packet = struct.pack("=I", self.sequenceNumber) + struct.pack("=?", False) + \
                          self.data.encode(FORMAT) + struct.pack("=H", self.fcs)

    @staticmethod
    def generateFCS():
        # TODO
        return 4


class FrameManager(Thread):
    HEADER_SIZE = 6

    def __init__(self, client_socket, fileAddress, window, frameLostProb=-1):
        Thread.__init__(self)
        self.frames = []
        self.fileAddress = fileAddress
        self.nextFrame2Send = 0
        self.window = window
        self.packetCount = 0
        self.client_socket = client_socket
        self.frameLostProb = frameLostProb

    def makePackets(self):
        file = open(self.fileAddress, "r")
        while True:
            data = file.read(self.window.dataSize)
            if not data:
                break
            self.frames.append(Frame(len(self.frames) % 2 ** self.window.dataSize, data))

    def run(self):
        self.makePackets()
        self.packetCount = 0
        self.client_socket.sendall(struct.pack("=I", (len(self.frames) * self.window.dataSize)) +
                                   struct.pack("=H", self.window.dataSize))
        while self.packetCount < len(self.frames):
            # print(self.window.transmittedFrames, len(self.window.transmittedFrames), self.window.maxWindowSize)
            if len(self.window.transmittedFrames.keys()) < self.window.maxWindowSize:
                # print("[Sending] Client is sending a packet ...")
                with LOCK:
                    self.window.saveNumber(self.nextFrame2Send)
                    SingleFrame(self.client_socket, self.frames[self.packetCount], self.window, self).start()
                    time.sleep(0.0001)
                    self.nextFrame2Send += 1
                    self.nextFrame2Send %= 2 ** self.window.dataSize
                    self.packetCount += 1
        print(self.window.transmittedFrames)
        if len(self.window.transmittedFrames) != 0:
            time.sleep(2)
        self.window.isTransmitting = False
        print(self.window.transmittedFrames)
        print("End FrameManager")


class SingleFrame(Thread):
    def __init__(self, client_socket, frame, window, frameManager, timeOut=3):
        Thread.__init__(self)
        self.frame = frame
        self.window = window
        self.timeOut = timeOut
        self.client_socket = client_socket
        self.frameManager = frameManager

    def timeOutProtocol(self):
        while self.frame.sequenceNumber in self.window.transmittedFrames and\
                not self.window.transmittedFrames[self.frame.sequenceNumber][1] and self.window.isTransmitting:
            with LOCK:
                if self.frame.sequenceNumber in self.window.transmittedFrames and\
                        time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0] > self.timeOut:
                    # print("Elapsed : ", time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0])
                    self.client_socket.sendall(Frame(self.frame.sequenceNumber, pBit=True).packet)
        self.window.stop()

    def run(self):
        self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
        if random.random() > self.frameManager.frameLostProb:
            self.client_socket.sendall(self.frame.packet)
        self.timeOutProtocol()
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
                while seqNum - 1 in self.window.transmittedFrames.keys() and\
                        not self.window.transmittedFrames[(seqNum - 1) % (2 ** self.window.dataSize)][1]:
                    self.window.markAcked(seqNum)
                # self.window.stop()
            else:
                while self.frameManager.nextFrame2Send != seqNum:
                    with LOCK:
                        self.frameManager.nextFrame2Send = seqNum
                        self.frameManager.packetCount -= (self.frameManager.packetCount %
                                                          (2 ** self.window.dataSize) - seqNum) \
                            if self.frameManager.packetCount % \
                               (2 ** self.window.dataSize) > seqNum else (seqNum + 2 ** self.window.dataSize -
                                                                          self.frameManager.packetCount % (
                                                                                  2 ** self.window.dataSize))
            # except Exception as error:
            #     print("Could not receive the packet")
            #     print(error)
        print("End AckReceiver")
        self.client_socket.close()

    @staticmethod
    def parseAck(ack):
        return struct.unpack("=?", ack[:1])[0], struct.unpack("=I", ack[1:5])[0]


# for j in range(2, 12):
#     for i in range(4):
#         client_program(j)
        # time.sleep(1)
    # Graphiste(Client(20)).start()

client_program()
# client_program(1)
# time.sleep(1)
# client_program(1)
