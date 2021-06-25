# import socket
# import time
#
# HOST = socket.gethostname()
# # '127.0.0.1'
# PORT = 1234
#
#
# def receive():
#     server_socket = socket.socket()
#     server_socket.bind((HOST, PORT))
#     server_socket.listen()
#     conn, address = server_socket.accept()
#     print("server")
#     while True:
#         print('Connected by', address)
#         data = conn.recv(32)
#         if not data:
#             break
#         print(data)

import socket
import struct
import time

FORMAT = "utf-8"
HOST = socket.gethostbyname(socket.gethostname())
PORT = 5050
ADDRESS = (HOST, PORT)


def server_program():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(ADDRESS)
    server_socket.listen()
    while True:
        print(f"[LISTENING] Server is listening on {HOST}")
        conn, addr = server_socket.accept()
        print('[CONNECTING] Connected by', addr)
        start = time.time()
        data = conn.recv(1024)
        dataSize = struct.unpack("=I", data[:4])
        fieldLength = struct.unpack("=H", data[4:6])
        PacketManager(conn, addr, fieldLength[0], dataSize[0]).start()
        end = time.time()
        print(f"Time to receive the information : {(end - start)* 1000} ms")



class PacketManager:
    def __init__(self, conn, addr, fieldLength, dataSize=60):
        self.conn = conn
        self.memory = []
        self.expectedFrame = 0
        self.addr = addr
        self.maxWindowSize = 2**(fieldLength - 1)
        self.fieldLength = fieldLength
        self.dataSize = dataSize

    def sendAck(self, seqNum, data, temp):
        if seqNum == self.expectedFrame:
            self.conn.sendall(struct.pack("=?", True) + data[:4])
            print(f"send ack {seqNum}")
            temp.append(data.decode(FORMAT)[6:])
            self.expectedFrame += 1
        elif seqNum < self.expectedFrame:
            self.conn.sendall(struct.pack("=?", True) + data[:4])
            temp[seqNum] = data.decode(FORMAT)[6:]
        else:
            self.conn.sendall(struct.pack("=?", False) + data[:4])
            temp.append(None)
            self.expectedFrame += 1
        self.expectedFrame %= 2 ** self.fieldLength

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
            self.sendAck(seqNum, data, temp)

            if len(temp) == 2 ** self.fieldLength and None not in temp[:2 ** self.fieldLength]:
                self.memory += temp[:(2 ** self.fieldLength)]
                temp = temp[2 ** self.fieldLength:]

        self.memory += temp
        self.printResult()
        self.conn.close()


if __name__ == '__main__':
    print(f"[STARTING] Server is starting ...")
    server_program()
