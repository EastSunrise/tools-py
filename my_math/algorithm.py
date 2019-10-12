#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module algorithm

@Author Kingen
@Date 2019/10/12
@Version 1.0
"""
import random


class RSA:
    """
    RSA加密算法
    """

    def __init__(self) -> None:
        p, q = get_prime(), get_prime()
        while p == q:
            q = get_prime()
        n = p * q
        euler = (p - 1) * (q - 1)
        e = 65537
        d, y, gcd = ext_euclidean(e, euler)
        self.public_key = (n, e)
        self.__private_key = (n, d)

    def encrypt(self, plaintext):
        return exp_mode(plaintext, self.public_key[1], self.public_key[0])

    def decrypt(self, ciphertext):
        return exp_mode(ciphertext, self.__private_key[1], self.__private_key[0])


def miller_rabin(num):
    """
    判断大整数是否为质数
    :param num: 大整数
    :return:
    """
    s = num - 1
    t = 0
    while s % 2 == 0:
        s = s // 2
        t += 1

    for trials in range(5):
        a = random.randrange(2, num - 1)
        v = pow(a, s, num)
        if v != 1:
            i = 0
            while v != (num - 1):
                if i == t - 1:
                    return False
                else:
                    i = i + 1
                    v = (v ** 2) % num
    return True


def is_prime(num):
    """
    判断是否是质数
    :param num:
    :return:
    """
    # 排除0,1和负数
    if num < 2:
        return False

    # 创建小素数的列表,可以大幅加快速度
    # 如果是小素数,那么直接返回true
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101,
                    103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199,
                    211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
                    331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419, 421, 431, 433, 439, 443,
                    449, 457, 461, 463, 467, 479, 487, 491, 499, 503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577,
                    587, 593, 599, 601, 607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691, 701,
                    709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809, 811, 821, 823, 827, 829, 839,
                    853, 857, 859, 863, 877, 881, 883, 887, 907, 911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983,
                    991, 997]
    if num in small_primes:
        return True

    # 如果大数是这些小素数的倍数,那么就是合数,返回false
    for prime in small_primes:
        if num % prime == 0:
            return False

    # 如果这样没有分辨出来,就一定是大整数,那么就调用rabin算法
    return miller_rabin(num)


# 得到大整数,默认位数为1024
def get_prime(key_size=1024):
    while True:
        num = random.randrange(2 ** (key_size - 1), 2 ** key_size)
        if is_prime(num):
            return num


def ext_euclidean(a, b):
    """
    扩展欧几里得算法，a和b互质
    ax+by=gcd
    :return 一组解x, y和gcd
    """
    if b == 0:
        return 1, 0, a
    else:
        x, y, q = ext_euclidean(b, a % b)  # q = gcd(a, b) = gcd(b, a%b)
        x, y = y, (x - (a // b) * y)
        return x, y, q


def exp_mode(base, exponent, r):
    """
    大整数幂取模
    :param base: 底数
    :param exponent: 指数
    :param n: 模
    :return: 结果
    """
    if exponent == 0:
        return 1 % r
    if exponent == 1:
        return base % r
    temp = exp_mode(base, (exponent / 2), r)
    temp = temp * temp % r
    if exponent & 1 == 1:
        temp = temp * base % r
    return temp


if __name__ == '__main__':
    src = 89
    rsa = RSA()
    mi = rsa.encrypt(src)
    print(mi)
    jie = rsa.decrypt(mi)
    print(jie)
