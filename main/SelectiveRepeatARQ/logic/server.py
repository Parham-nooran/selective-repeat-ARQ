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
    while len(runningTimes.keys()) < 20:
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
        self.start = 0
        self.end = 0
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)


class PacketManager:
    def __init__(self, conn, addr, fieldLength, dataSize=60):
        self.conn = conn
        self.buffer = []
        self.addr = addr
        self.lastAck = None
        self.expectedFrame = 0
        self.maxWindowSize = 2 ** (fieldLength - 1)
        self.fieldLength = fieldLength
        self.dataSize = dataSize

    def sendAck(self, data, temp):
        seqNum = struct.unpack("=I", data[:4])[0]

        # if seqNum > self.expectedFrame:
        #     if seqNum < self.expectedFrame + self.maxWindowSize and seqNum in temp and temp[seqNum] is not None:
        #         count = self.expectedFrame
        #         while count < seqNum:
        #             temp.append(None)
        #             self.conn.sendall(struct.pack("=?", False) + struct.pack("=I", count))
        #             count += 1
        #         temp.append(data.decode(FORMAT)[6:])
        #     else:
        #         temp[seqNum] = data.decode(FORMAT)[6:]
        #
        # elif seqNum == self.expectedFrame:
        #     temp.append(data.decode(FORMAT)[6:])
        #     self.conn.sendall(struct.pack("=?", True) + struct.pack("=I", (seqNum + 1) % 2 ** self.fieldLength))
        #     self.expectedFrame += 1
        # elif seqNum < self.expectedFrame:
        #     if seqNum < self.expectedFrame - self.maxWindowSize:
        #         count = self.expectedFrame
        #         while count < seqNum:
        #             temp.append(None)
        #             self.conn.sendall(struct.pack("=?", False) + struct.pack("=I", count))
        #             count += 1
        #         temp.append(data.decode(FORMAT)[6:])
        #     else:
        #         temp[seqNum] = data.decode(FORMAT)[6:]
        #
        # if (seqNum > self.expectedFrame and seqNum >= self.expectedFrame + self.maxWindowSize) or \
        #         (self.expectedFrame > seqNum >= self.expectedFrame - self.maxWindowSize):
        #     index = 0
        #     while index < len(temp) and temp[index] is not None:
        #         index += 1
        #     if self.lastAck is None or self.lastAck < index:
        #         self.lastAck = index
        #         self.conn.sendall(struct.pack("=?", True) + struct.pack("=I", index + 1))
        # self.expectedFrame %= 2 ** self.fieldLength
        # print(f"Send ack {seqNum}")

        # if seqNum == self.expectedFrame:
        #     self.conn.sendall(struct.pack("=?", True) + struct.pack("=H", struct.unpack("=I", data[:4])[0] + 1))
        #     print(f"Send ack {seqNum}")
        #     temp.append(data.decode(FORMAT)[6:])
        #     self.expectedFrame += 1

        # if seqNum == self.expectedFrame:
        #     self.conn.sendall(struct.pack("=?", True) + data[:4])
        #     print(f"Send ack {seqNum}")
        #     temp.append(data.decode(FORMAT)[6:])
        #     self.expectedFrame += 1
        # elif seqNum < self.expectedFrame:
        #     self.conn.sendall(struct.pack("=?", True) + data[:4])
        #     temp[seqNum] = data.decode(FORMAT)[6:]
        # else:
        #     self.conn.sendall(struct.pack("=?", False) + data[:4])
        #     temp.append(None)
        #     self.expectedFrame += 1
        # self.expectedFrame %= 2 ** self.fieldLength

    def printResult(self):
        print(self.memory[:self.dataSize])
        temp = ''
        for x in self.memory:
            temp += x
        print(temp)

    def start(self):
        temp = []
        while len(list(set(self.memory + temp) - {None})) * self.fieldLength < self.dataSize:
            # print("Memory : ", self.memory)
            data = self.conn.recv(1024)
            if not data:
                break
            seqNum = struct.unpack("=I", data[:4])[0]
            print(f"[{self.addr}] Sequence number : {seqNum}, data :{data.decode(FORMAT)[6:]}")
            self.sendAck(data, temp)

            if len(temp) >= 2 ** self.fieldLength and None not in temp[:2 ** self.fieldLength]:
                self.memory += temp[:(2 ** self.fieldLength)]
                temp = temp[2 ** self.fieldLength:]

        self.memory += temp
        self.printResult()
        self.conn.close()


if __name__ == '__main__':
    print(f"[STARTING] Server is starting ...")
    server_program()
