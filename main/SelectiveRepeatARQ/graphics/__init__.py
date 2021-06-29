import tkinter
import matplotlib.pyplot as mp


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
