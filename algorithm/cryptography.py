import random


class RSA:
    """
    RSA
    """

    def __init__(self):
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
    If a big number is prime.
    :param num
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
    If a number is prime
    :param num:
    :return:
    """
    # exclude 0, 1 and negative numbers
    if num < 2:
        return False

    # Efficiency will increase with a list of small prime numbers
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

    for prime in small_primes:
        if num % prime == 0:
            return False

    return miller_rabin(num)


def get_prime(length=1024):
    """
    Get a big prime number, defaults to 1024 digits.
    :param length:
    :return:
    """
    while True:
        num = random.randrange(2 ** (length - 1), 2 ** length)
        if is_prime(num):
            return num


def ext_euclidean(a, b):
    """
    Extended Euclidean Algorithm.
    Solve the equation 'ax+by=gcd', a is prime to b.
    :return one solution: x, y and gcd
    """
    if b == 0:
        return 1, 0, a
    else:
        x, y, q = ext_euclidean(b, a % b)  # q = gcd(a, b) = gcd(b, a%b)
        x, y = y, (x - (a // b) * y)
        return x, y, q


def exp_mode(base, exponent, modulo):
    """
    Modulo for big integers
    :param base
    :param exponent
    :param modulo
    :return:
    """
    if exponent == 0:
        return 1 % modulo
    if exponent == 1:
        return base % modulo
    temp = exp_mode(base, (exponent / 2), modulo)
    temp = temp * temp % modulo
    if exponent & 1 == 1:
        temp = temp * base % modulo
    return temp
