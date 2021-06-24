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

HOST = socket.gethostname() # '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 1234        # Port to listen on (non-privileged ports are > 1023)


def server_program():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    conn, addr = server_socket.accept()

    print('Connected by', addr)
    frame_num = 0
    while True:
        data = conn.recv(1024)
        # time.sleep(0.100)
        # data2 = conn.recv(1024)
        print(f"Me, server, received : {data.decode()[6:]}")
        if not data:
            break
        print(struct.unpack("=I", data[:4]))
        conn.sendall(data[:4])
    conn.close()


server_program()
