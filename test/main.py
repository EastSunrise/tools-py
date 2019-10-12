#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module main

@Author Kingen
@Date 2019/10/12
@Version 1.0
"""
import random


def draw_lots():
    groups = ['A', 'B', 'C', 'D']
    ones = random.shuffle(groups)
    shuffle_twos = random.shuffle(groups)
    left_twos = []
    right_twos = []
    for i in range(4):
        if shuffle_twos[i] in ones[0:2]:
            right_twos.append(shuffle_twos[i])
        else:
            left_twos.append(shuffle_twos[i])
    twos = left_twos + right_twos
    return [(ones[i] + str(1), twos[i] + str(2)) for i in range(len(groups))]


def earning(probabilities, odds, values, length):
    result = 0.0
    for i in range(length):
        result += (1 - probabilities[i]) * values[i] - probabilities[i] * values[i] * odds[i]
    return result


if __name__ == '__main__':
    print(earning([0.88, 0.72, 0.39, 0.01], [1.11, 1.18, 2.60, 50.00], [10000, 10000, 10000, 100], 4))
