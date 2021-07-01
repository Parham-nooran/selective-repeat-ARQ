import tkinter as tk
import matplotlib.pyplot as mp

from main.SelectiveRepeatARQ.logic.client import Client


class Plotter:
    def __init__(self, data):
        self.data = data
        self.frameLengths = self.data.keys()
        self.times = {}
        for key in self.frameLengths:
            self.times[key] = sum(self.data[key])/ len(data[key])

    def plot(self):
        mp.plot(self.times.keys(), self.times.values())
        mp.show()


class Graphiste:
    def __init__(self, fieldLength, server):
        self.fieldLength = fieldLength
        self.client = Client(self.fieldLength)
        self.clientRoot = tk.Tk()
        self.serverRoot = tk.Tk()
        self.frames = []
        self.server = server

    def startClient(self):
        self.client.frameManager.makePackets()
        self.frames = self.client.frameManager.frames
        c = 0
        for frame in self.frames:
            label = tk.Label(master=self.clientRoot, text=frame.data)
            c += 1
            label.grid(row=c, column=1)
        tk.mainloop()

    def receive(self, data):
        label = tk.Label(master=self.serverRoot, text=data)
        label.pack()




# if __name__ == '__main__':
#     Graphiste(5).startClient()
    # Client().client_program()
