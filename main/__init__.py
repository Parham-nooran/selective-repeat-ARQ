import threading
import time
from main.logic import client

# if __name__ == '__main__':
    # clientThread = threading.Thread(target=client.startClient())
    # # serverThread.start()
    # clientThread.start()
    # second = threading.Thread(target=server_program())
    # time.sleep(5)
    # first = threading.Thread(target=client_program())
# serverThread = threading.Thread(target=server.startServer())

for i in range(10):
    client.client_program(i)



