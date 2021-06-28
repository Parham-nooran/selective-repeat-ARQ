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
        self.nextFrame2send = 0
        self.sentPackets = 0
        self.expectedAck = 0
        self.dataSize = dataSize
        self.maxWindowSize = 2 ** (dataSize - 1)
        self.transmittedFrames = OrderedDict()
        self.start = 0
        self.end = 0
        self.lastAcked = 0
        self.isTransmitting = True
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)

    def isNotEmpty(self):
        return len(self.transmittedFrames) > 0

    def saveNumber(self, seqNumber):
        self.transmittedFrames[seqNumber] = [None, False]
        self.end = seqNumber
        self.expectedAck = seqNumber
        self.nextFrame2send += 1
        self.nextFrame2send %= 2 ** self.dataSize
        self.sentPackets += 1

    def markAcked(self, seqNumber):
        with LOCK:
            print(seqNumber)
            if seqNumber - 1 in self.transmittedFrames.keys():
                self.transmittedFrames[seqNumber - 1] = [None, True]
                # if self.start < self.end:
                #     for x in self.transmittedFrames.keys():
                #         if x < seqNumber:
                #             self.transmittedFrames[x] = [None, True]
                #         else:
                #             break
                # elif self.start > self.end:
                #     if seqNumber < self.start:
                #         for x in self.transmittedFrames.keys():
                #             if x > self.start:
                #                 self.transmittedFrames[x] = [None, True]
                #         for x in self.transmittedFrames.keys():
                #             if x < seqNumber:
                #                 self.transmittedFrames[x] = [None, True]
                #     else:
                #         for x in self.transmittedFrames.keys():
                #             if self.start <= x < seqNumber:
                #                 self.transmittedFrames[x] = [None, True]
                print(f"Marked {seqNumber}")
            self.stop(seqNumber)


    def stop(self, seqNumber):
        temp = self.transmittedFrames.copy()
        for sNum, value in temp.items():
            if sNum < seqNumber and value[1]:
                del self.transmittedFrames[sNum]
                self.start = sNum + 1
            else:
                break
        # if self.start < self.end:
        #     for sNum, value in temp.items():
        #         if sNum < seqNumber and value[1]:
        #             del self.transmittedFrames[sNum]
        #             self.start = sNum + 1
        #         else:
        #             break
        # elif self.start > self.end:
        #     for sNum, value in temp.items():
        #         if sNum >= self.start > seqNumber or (seqNumber > self.start and self.start <= sNum < seqNumber):
        #             if value[1]:
        #                 del self.transmittedFrames[sNum]
        #                 self.start = sNum + 1
        #     if seqNumber < self.start:
        #         for sNum, value in temp.items():
        #             if sNum < seqNumber:
        #                 if value[1]:
        #                     del self.transmittedFrames[sNum]
        #                     self.start = sNum + 1


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
                self.window.end = self.frames[packetCount].sequenceNumber
                SingleFrame(self.client_socket, self.frames[packetCount], self.window).start()
                time.sleep(0.00000001)
                packetCount += 1
        print(self.window.transmittedFrames)
        # while True:
        #     if len(self.window.transmittedFrames) == 0:
        #         self.window.isTransmitting = False
        #         break
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
        print(f"Sent {self.frame.packet}")
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


# client_program(9)
# if __name__ == '__main__':
#     for i in range(5):
#         client_program(i+2)
# def runAll():
#     # for i in range(5):
#     #     client_program(i+2)
#     #     time.sleep(3)
#     client_program(4)
#
#
# runAll()
client_program()
