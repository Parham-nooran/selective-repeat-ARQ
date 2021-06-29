import threading
import time
from collections import OrderedDict
# from main.SelectiveRepeatARQ.logic import client
#
#
# def calculateAll():
#     client.client_program()
#     # times = []
#     # for i in range(5):
#     #     times.append(1000*client.client_program(i + 5))
#     #     time.sleep(1)
#     # print(times)
#
#

#
# def delay():
#     d = 1
#     for i in range(1000):
#         d *= 2
#

# if __name__ == '__main__':
    # start = time.time()
    # delay()
    # end = time.time()
    # print(end - start)
    # test = OrderedDict()
    # for i in range(10):
    #     test[i] = [i+5, True]
    # print(test[1:5])
    # test[:5] = [0, False] * 5
    # print(test)
if __name__ == '__main__':
    for i in range(5):
        print(i)
        time.sleep(2)
    # test = {}
    #
    # for i in range(10)[5:]:
    #     test[i] = [i + 5, False]
    # for i in range(1, 10)[:5]:
    #     test[i] = [i + 5, True]
    # print(test)
    # print(list(test.keys())[0])
    # print(-1 % 5)

