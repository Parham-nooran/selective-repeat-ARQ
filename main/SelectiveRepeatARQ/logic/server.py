import socket
import struct
import time
from collections import OrderedDict

FORMAT = "utf-8"
HOST = socket.gethostbyname(socket.gethostname())
PORT = 5050
ADDRESS = (HOST, PORT)


def server_program():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(ADDRESS)
    server_socket.listen()
    runningTimes = OrderedDict()
    while len(runningTimes.keys()) < 10:
        print(f"[LISTENING] Server is listening on {HOST}")
        conn, addr = server_socket.accept()
        print('[CONNECTING] Connected by', addr)
        start = time.time()
        data = conn.recv(1024)
        dataSize = struct.unpack("=I", data[:4])[0]
        fieldLength = struct.unpack("=H", data[4:6])[0]
        # window = Window(dataSize)
        PacketManager(conn, addr, fieldLength, dataSize).start()
        end = time.time()
        print(f"Elapsed time : {(end - start) * 1000} ms")
        if fieldLength not in runningTimes.keys():
            runningTimes[fieldLength] = []
        runningTimes[fieldLength].append((end - start) * 1000)
        print(runningTimes)


class Window:
    def __init__(self, dataSize, windowSize=None):
        self.dataSize = dataSize
        self.maxWindowSize = 2 ** (dataSize - 1)
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)


class PacketManager:
    def __init__(self, conn, addr, fieldLength, dataSize=60):
        self.conn = conn
        self.buffer = {}
        self.addr = addr
        self.lastAck = None
        self.expectedFrame = 0
        self.received = 0
        self.result = ''
        self.maxWindowSize = 2 ** (fieldLength - 1)
        self.fieldLength = fieldLength
        self.dataSize = dataSize

    def sendAck(self, data):
        seqNum = struct.unpack("=I", data[:4])[0]

        if self.expectedFrame == seqNum:
            self.conn.sendall(struct.pack("=?", True) + struct.pack("=I", (seqNum + 1) % (2 ** self.fieldLength)))
            print(f"Send ack {seqNum}")
            self.result += data.decode(FORMAT)[6:]
            self.expectedFrame += 1
            if len(self.buffer) != 0 and seqNum in self.buffer:
                del self.buffer[seqNum]

        elif (len(self.buffer) == 0 and (self.expectedFrame < seqNum < 2 ** self.fieldLength
                                       or seqNum < (self.expectedFrame + self.maxWindowSize) % 2 ** self.fieldLength)) \
                or ((self.expectedFrame < seqNum < 2 ** self.fieldLength
                     or seqNum < (self.expectedFrame - self.maxWindowSize) % 2 ** self.fieldLength)
                    and 0 < len(self.buffer) < self.maxWindowSize):

            for i in range(self.expectedFrame, seqNum if seqNum > self.expectedFrame else 2 ** self.fieldLength +
                                                                                          seqNum):
                self.buffer[i % 2 ** self.fieldLength] = None
                self.conn.sendall(struct.pack("=?", False) + struct.pack("=I", i % (2 ** self.fieldLength)))

            self.buffer[seqNum] = data.decode(FORMAT)[6:]

        elif len(self.buffer) != 0 and seqNum in self.buffer.keys():
            self.buffer[seqNum] = data.decode(FORMAT)[6:]
        if len(self.buffer) != 0:
            temp = self.buffer.copy().keys()
            for k in temp:
                if self.buffer[k] is not None:
                    self.result += self.buffer[k]
                    del self.buffer[k]
                    self.expectedFrame += 1

        self.expectedFrame %= 2 ** self.fieldLength



    def start(self):
        while self.received < self.dataSize:
            # print("Memory : ", self.memory)
            data = self.conn.recv(1024)
            if not data:
                break
            seqNum = struct.unpack("=I", data[:4])[0]
            self.received += self.fieldLength
            print(f"[{self.addr}] Sequence number : {seqNum}, data :{data.decode(FORMAT)[6:]}")
            self.sendAck(data)

        self.conn.close()


if __name__ == '__main__':
    print(f"[STARTING] Server is starting ...")
    server_program()
