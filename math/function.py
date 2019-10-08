#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module function

@Author Kingen
@Date 2019/9/29
@Version 1.0
"""
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
    x = np.linspace(start, end)
    pyplot.grid()
    pyplot.plot(x, f(x, *args))
    pyplot.show()


pyplot.show()

if __name__ == '__main__':
    draw(rate, 0.01, 1, pag_rate)
