"""
استفاده از کتابخانه ها ی مورد نیاز
"""
import random
import socket
import time
from threading import Thread, Lock
import struct
import tkinter as tk

"""
قرار دادن اطلاعات مربوط به اتصال و نحوه ی اتصال به صورت Global در ابتدای کد

"""
FORMAT = "utf-8"
LOCK = Lock()
HOST = socket.gethostbyname(socket.gethostname())
PORT = 5050
ADDRESS = (HOST, PORT)

"""

کلاس Client برای نگه داشتن اطلاعات مهم کلاینت و استفاده از آن برای نمایش گرافیکی اطلاعات پیام و نحوه ی ارسال آن تعریف 
شده است. تابع client_program برای اتصال به سرور با استفاده از اطلاعات اتصال تعریف شده در ابتدای کد به کار می رود در 
این کلاس دو رشته می سازیم تا بتوان وظیفه ی دریافت تاییدیه و ارسال بسته ها را به طور همزمان انجام داد زمان شروع تا 
اتمام کار این رشته ها ممکن است با زمان صرف شده برای ارسال بسته ها متفاوت باشد. در اینجا می توان احتمال ارسال بسته ها 
با گمشدگی را تنظیم کرد در صورت عدم نیاز به خطا می توان مقدار FrameLostProb را برابر منفی 1 قرار داد 

"""


class Client:
    def __init__(self, fieldLength=5, fileAddress="D:\\Users\\shahram\\test.txt", graphiste=None, frameLostProb=0.5):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.fileAddress = fileAddress
        self.fieldLength = fieldLength
        self.window = Window(fieldLength)
        self.graphiste = graphiste
        self.frameLostProb = frameLostProb
        # self.frameManager = FrameManager(self.client_socket, self.fileAddress, self.window)
        self.frameManager = FrameManager(self.client_socket, self.fileAddress, self.window, self.graphiste,
                                         frameLostProb=self.frameLostProb)
        self.ackReceiver = AckReceiver(self.window, self.frameManager, self.client_socket)

    def client_program(self):
        self.client_socket.connect((HOST, PORT))
        start = time.time()
        self.ackReceiver.start()
        self.frameManager.start()
        self.ackReceiver.join()
        self.frameManager.join()
        end = time.time()
        print("End all")
        print(f"Time to send all the data : {(end - start) * 1000} ms")


"""

در این کلاس اطلاعات یک بسته مثل شماره ی بسته و داده ی مورد نظر دریافت شده و بسته ی pack شده ی آماده ی ارسال به عنوان یکی 
از صفات نمونه قابل دسترسی خواهد بود.
در اینجا برای اطمینان از ارسال درست بسته 
"""


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


"""

در این کلاس توابع لازم مربوط به پروتکل پنجره ی لغزان تعریف می شود یک نمونه از این کلاس در تمام کلاس های کنترلی دیگر 
قرار می گیرد تا بر رعایت پروتکل های مربوطه نظارت کند. هر بسته ی ارسال شده تا قبل از دریافت تاییدیه در یک ساختار داده 
ئخیره می شود. این ساختار نمایشگر پنجره ی ارسال است و در صورتی که اندازه ی پنجره های تایید نشده از حد مجاز تعریف شده 
بیشتر شود ارسال بسته ها متوقف می شود در واقع در این ساختار اطلاعات پنجره ی شامل فریم های آماده ی ارسال نگه داری نمی شود
بلکه فریم های ارسال شده ی پنجره ثبت می شود که اندازه ی آن نمی تواند از اندازه ی پنجره تجاوز کند. 

"""


class Window:
    def __init__(self, dataSize, windowSize=None):
        self.dataSize = dataSize
        self.maxWindowSize = 2 ** (dataSize - 1)
        self.transmittedFrames = {}
        self.isTransmitting = True
        if windowSize is not None:
            self.maxWindowSize = min(self.maxWindowSize, windowSize)

    def isNotEmpty(self):
        return len(self.transmittedFrames) > 0

    def saveNumber(self, seqNumber):
        self.transmittedFrames[seqNumber] = [None, False]

    def markAcked(self, seqNumber):  # Marks the related frame as acknowledged
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
            # print(f"Marked {seqNumber}")

    def stop(self):  # Deletes the acknowledged frames from the dictionary
        with LOCK:
            temp = self.transmittedFrames.copy()
            for key, value in temp.items():
                if value[1]:
                    del self.transmittedFrames[key]
                    # print("Deleted ", key)
                else:
                    break


"""

برای مدیریت بسته ها به کار می رود.
در این کلاس توابع لازم برای ساخت و ارسال بسته ها تعریف می شود.
(توابع در کد کامنت شده اند.)

"""


class FrameManager(Thread):
    HEADER_SIZE = 6

    def __init__(self, client_socket, fileAddress, window, graphiste, frameLostProb):
        Thread.__init__(self)
        self.frames = []
        self.fileAddress = fileAddress
        self.window = window
        self.client_socket = client_socket
        self.graphiste = graphiste
        self.frameLostProb = frameLostProb

    def makePackets(self):  # Reads the information from the specified file and makes packets including parts of this
        # data that are as large as the specified fieldLength of the Window class, instance
        file = open(self.fileAddress, "r")
        while True:
            data = file.read(self.window.dataSize)
            if not data:
                break
            self.frames.append(Frame(len(self.frames) % 2 ** self.window.dataSize, data))

    def sendAgain(self, seqNum):  # Sends again a failed or lost packet
        self.window.transmittedFrames[seqNum][0] = time.time()
        if random.random() > self.frameLostProb:
            print(f"Sent again : {self.frames[seqNum].data}")
            self.client_socket.sendall(self.frames[seqNum].packet)

    def run(self):  # Sends all the made packets while considering the sliding window protocol
        if self.graphiste is None:
            self.makePackets()
        packetCount = 0
        self.client_socket.sendall(struct.pack("=I", (len(self.frames) * self.window.dataSize)) +
                                   struct.pack("=H", self.window.dataSize))
        while packetCount < len(self.frames):
            # print(self.window.transmittedFrames, len(self.window.transmittedFrames), self.window.maxWindowSize)
            if len(self.window.transmittedFrames.keys()) < self.window.maxWindowSize:
                print("[Sending] Client is sending a packet ...")
                self.window.saveNumber(packetCount % 2 ** self.window.dataSize)
                SingleFrame(self.client_socket, self.frames[packetCount], self.window, self.frameLostProb).start()
                if self.graphiste is not None:
                    self.graphiste.scrollable_frame.grid_slaves(row=packetCount + 2, column=3)[0]["text"] = "Sent\t"
                    self.graphiste.scrollable_frame.grid_slaves(row=packetCount + 2, column=3)[0]["bg"] = "Light Green"
                time.sleep(0.00000001 if self.graphiste is None else 1)
                packetCount += 1
        print(self.window.transmittedFrames)
        while len(self.window.transmittedFrames) != 0:
            continue
        self.window.isTransmitting = False
        # self.client_socket.close()
        print("End FrameManager")


"""

این کلاس برای پیاده سازی پروتکل Time out تعریف شده است. در این کلاس برای ارسال هر بسته یک رشته فعال می شود که تا 
دریافت تاییدیه ی مربوط به آن رشته در زمان های مشخصی بسته را مجدد ارسال می کند. 

"""


class SingleFrame(Thread):
    def __init__(self, client_socket, frame, window, frameLostPorb, timeOut=1):
        Thread.__init__(self)
        self.frame = frame
        self.window = window
        self.timeOut = timeOut
        self.client_socket = client_socket
        self.frameLostProb = frameLostPorb

    def timeOutProtocol(self):
        while self.frame.sequenceNumber in self.window.transmittedFrames.keys() and \
                not self.window.transmittedFrames[self.frame.sequenceNumber][1]:
            with LOCK:
                if self.frame.sequenceNumber in self.window.transmittedFrames.keys() and \
                        time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0] > self.timeOut:
                    # print("Elapsed : ", time.time() - self.window.transmittedFrames[self.frame.sequenceNumber][0])
                    self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
                    if random.random() > self.frameLostProb:
                        print(f"Sent : {self.frame.data}")
                        self.client_socket.sendall(self.frame.packet)
        self.window.stop()

    def run(self):
        self.window.transmittedFrames[self.frame.sequenceNumber][0] = time.time()
        if random.random() > self.frameLostProb:
            self.client_socket.sendall(self.frame.packet)
        # print(f"Sent {self.frame.packet}")
        self.timeOutProtocol()
        print(f"[Sent] Frame #{self.frame.sequenceNumber} (\"{self.frame.data}\"), sent successfully.\n")


"""

برای دریافت تاییده ی بسته ها به کار می رود.
در صورتی که کلاینت بسته ای دریافت کند در متد Parser مربوطه بسته تجزیه شده و متناسب با آن عملیات ارسال مجدد و یا تایید و 
حذف بسته از لیست ارسال شده(تایید نشده) ها انجام می شود.
نمونه ای ن کلاس تا زمان دریافت تاییدیه برای همه ی بسته های ارسال شده فعال خواهد ماند

"""


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
            print("Received acknowledgement : ", self.parseAck(ack), "\n")
            typeOfAck, seqNum = self.parseAck(ack)
            if typeOfAck:
                if (seqNum - 1) % 2 ** self.window.dataSize in self.window.transmittedFrames.keys():
                    while not self.window.transmittedFrames[(seqNum - 1) % 2 ** self.window.dataSize][1]:
                        self.window.markAcked(seqNum)
                    if self.frameManager.graphiste is not None:
                        self.frameManager.graphiste.scrollable_frame.grid_slaves(row=seqNum + 1, column=4)[0]["text"] =\
                            "Sure\t"
                        self.frameManager.graphiste.scrollable_frame.grid_slaves(row=seqNum + 1, column=4)[0]["bg"] = \
                            "Light Green"
                    # self.window.stop()
            else:
                self.frameManager.sendAgain(seqNum)
        print("End AckReceiver")
        self.client_socket.close()

    @staticmethod
    def parseAck(ack):
        return struct.unpack("=?", ack[:1])[0], struct.unpack("=I", ack[1:5])[0]


"""

برای ساخت رابط کاربری و نمایش روند ارسال و تایید بسته ها به کار می رود.

"""


class Graphiste:
    def __init__(self, client):
        self.client = client
        self.client.frameManager.graphiste = self
        self.fieldLength = self.client.fieldLength
        self.root = tk.Tk()
        self.root.geometry("400x300")
        self.client.frameManager.makePackets()
        self.frames = self.client.frameManager.frames
        self.mainFrame = tk.Frame()
        self.canvas = tk.Canvas(self.mainFrame)
        self.scrollbar = tk.Scrollbar(self.mainFrame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

    def startClient(self):
        clientThread = Thread(target=self.client.client_program)
        clientThread.start()

    def start(self):
        c = 1

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # canvas.pack(row=1, column=1)
        # scrollbar.grid(row=1, column=1)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.mainFrame.grid(row=1, column=1)

        frameData = tk.Label(self.scrollable_frame, text="Data")
        frameData.grid(row=1, column=2)
        status = tk.Label(self.scrollable_frame, text="Status")
        status.grid(columnspan=4, row=1, column=2)
        seqNumL = tk.Label(self.scrollable_frame, text="Sequence number")
        seqNumL.grid(row=1, column=1)
        for frame in self.frames:
            seqNumL = tk.Label(master=self.scrollable_frame, text=str((c - 1) % (2 ** self.client.fieldLength)))
            dataL = tk.Label(master=self.scrollable_frame, text=frame.data)
            statusL = tk.Label(master=self.scrollable_frame, text="Not sent", bg="Orange")
            ackL = tk.Label(master=self.scrollable_frame, text="Not sure", bg="Orange")
            c += 1
            seqNumL.grid(row=c, column=1)
            dataL.grid(row=c, column=2)
            statusL.grid(row=c, column=3)
            ackL.grid(row=c, column=4)

        start = tk.Button(bd=3, command=self.startClient, text="Start client")
        start.grid(row=c + 2, column=1)
        print()
        self.root.grid_slaves(row=2, column=3)
        tk.mainloop()


# if __name__ == '__main__':
# for j in range(1, 11):
#     for i in range(4):
#         Client(j).client_program()
#         time.sleep(1)


if __name__ == '__main__':
    # Client(5).client_program()
    Graphiste(Client(5)).start()
