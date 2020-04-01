from abc import abstractmethod

import numpy as np
from matplotlib import pyplot

pag_rate = 0.04
gem_rate = 0.3
hex_rate = 0.0006


def rate(x, r):
    return 1 - (1 - r) ** x


class F:
    @abstractmethod
    def y(self, x):
        pass


def draw(f, start=0.0, end=100, *args):
    """
    绘制函数图像
    :param f: 函数方法，第一个参数为x
    :param start: 横坐标起点
    :param end: 横坐标终点
    :param args: 函数方法除x外参数
    :return:
    """
    x = np.linspace(start, end)
    pyplot.grid()
    pyplot.plot(x, f(x, *args))
    pyplot.show()


def develop(x, a, r):
    return a * (1 + r) ** x


def draw_dev(a, r, s, l):
    x = np.linspace(s, s + l)
    pyplot.grid()
    pyplot.plot(x, a * (1 + r) ** x)
    pyplot.show()


pyplot.show()

if __name__ == '__main__':
    draw_dev(1, 1, 1, 100)
