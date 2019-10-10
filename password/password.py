#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 密码生成器
@Module password

@Author Kingen
@Date 2019/10/10
@Version 1.0
"""
import hashlib
import math
from datetime import datetime

COMPLEX_DICT = ['!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4',
                '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I',
                'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']',
                '^', '_', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
                't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~']

SIMPLE_DICT = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
               'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f',
               'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

NUMBER_DICT = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']


def generate(domain, user=None, key=None, account=None, service=None, length=16, ascii_dict=None) -> str:
    """
    生成md5加密的密码
    :param domain: 域名，标志网站的域名，如126.com，seu.edu.cn
    :param user: 用户关键词
    :param key: 指定关键词
    :param account: 多账户时，账户关键词
    :param service: 多服务时，相关服务关键词，默认为空
    :param length: 所需密码长度
    :param ascii_dict: 密码字典
    :return: 密码
    """
    if ascii_dict is None:
        ascii_dict = COMPLEX_DICT

    # 原始字符串
    if ascii_dict is None:
        ascii_dict = COMPLEX_DICT
    domain = domain.lower()
    parts = domain.split('.')
    top = ''
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] != '':
            top = parts[i]
            break
    src_str = ''
    src_str += top + '.' + domain[0:2]
    src_str += '$' + 'wsg' if isBlank(user) else user
    src_str += '#' + '787' if isBlank(key) else key + '#'
    if not isBlank(account):
        src_str += '@' + account
    if not isBlank(service):
        src_str += '-' + service
    src_str += '%' + str(len(domain))

    # 多重md5加密
    times = math.ceil(2 * length / 32)
    md5 = hashlib.md5()
    str_md5 = ''
    for i in range(times):
        md5.update(src_str.encode(encoding='UTF-8'))
        src_str = md5.hexdigest()
        str_md5 += src_str

    # 最终的密码
    password = ''
    ascii_length = len(ascii_dict)
    for i in range(0, 2 * length, 2):
        index = int(str_md5[i:i + 2], 16)
        password += ascii_dict[index % ascii_length]
    return password


def start():
    global service
    print('©Gen Kings')
    while True:
        print('Please enter the password:')
        str_input = input()
        now_time = datetime.now()
        str_time = datetime.strftime(now_time, '%y%m%d%H%M%S')
        password = str_time[7:8] + str_time[9:10] + str_time[1:2] + str_time[3:4] + str_time[5:6]
        if str_input == password:
            break

    while True:
        print('Please enter the domain(-1 to exit):')
        domain = input()
        if domain == '-1':
            break
        if domain != '':
            print('Extra args?')
            flag = input()
            user = key = account = service = None
            if flag != '':
                print('Please enter the user:')
                user = input()
                print('Please enter the key:')
                key = input()
                print('Please enter the account:')
                account = input()
                print('Please enter the service:')
                service = input()
            print(generate(domain, user, key, account, service, 12, COMPLEX_DICT))
            print(generate(domain, user, key, account, service, 16, SIMPLE_DICT))
            print(generate(domain, user, key, account, service, 6, NUMBER_DICT))


def isBlank(string):
    return string is None or string.strip() == ''


if __name__ == '__main__':
    start()
