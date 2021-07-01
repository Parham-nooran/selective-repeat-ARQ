import tkinter as tk
import matplotlib.pyplot as mp

# from main.SelectiveRepeatARQ.logic.client import Client

"""

داده ها مشخص شده در data را پردازش و رسم می کند. برای این کار از داده های مربوط به هر کلید میانگین می گیرد و میانگین 
را به آن کلید ربط می دهد. کلید ها نشان دهنده ی اندازه داده ی موجود در هر قاب و مقادیر ربط داده شده به کلید نشان دهنده 
ی زمان دریافت (یا ارسال) با این اندازه ی داده است. 

"""


class Plotter:
    def __init__(self, data):
        self.data = data
        self.frameLengths = self.data.keys()
        self.times = {}
        for key in self.frameLengths:
            self.times[key] = sum(self.data[key]) / len(data[key])

    def plot(self):
        mp.plot(self.times.keys(), self.times.values())
        mp.xlabel("Data size (Byte(Latin-1 encoding))")
        mp.ylabel("Time (ms)")
        mp.show()


# class Graphiste:
#     def __init__(self, fieldLength, server):
#         self.fieldLength = fieldLength
#         self.client = Client(self.fieldLength)
#         self.clientRoot = tk.Tk()
#         self.serverRoot = tk.Tk()
#         self.frames = []
#         self.server = server
#
#     def startClient(self):
#         self.client.frameManager.makePackets()
#         self.frames = self.client.frameManager.frames
#         c = 0
#         for frame in self.frames:
#             label = tk.Label(master=self.clientRoot, text=frame.data)
#             c += 1
#             label.grid(row=c, column=1)
#         tk.mainloop()
#
#     def receive(self, data):
#         label = tk.Label(master=self.serverRoot, text=data)
#         label.pack()

# if __name__ == '__main__':
#     Graphiste(5).startClient()
# Client().client_program()
