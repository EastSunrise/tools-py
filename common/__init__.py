#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Common functions.

@Author Kingen
"""
import logging
from typing import Iterable, Callable, Dict, Any, List


def group_by(it: Iterable, key_func: Callable) -> Dict[Any, List[Any]]:
    res = {}
    for x in it:
        key = key_func(x)
        if key in res:
            res[key].append(x)
        else:
            res[key] = [x]
    return res


def create_logger(name: str, level=logging.INFO, console=True, file_path=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(fmt='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d]: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    fmt = logging.Formatter(fmt='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    if file_path:
        fh = logging.FileHandler(file_path, encoding='UTF-8')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


CHINESE_NUMERALS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']


def num2chinese(num: int) -> str:
    """
    Transfers Arabic numerals to Chinese numerals.
    """
    if num <= 0 or num > 20:
        raise ValueError
    if num <= 10:
        return CHINESE_NUMERALS[num]
    if num == 20:
        return '二十'
    return '十' + CHINESE_NUMERALS[num - 10]


class OptionalValue:
    def __init__(self, value):
        self.__value = value

    def map(self, mapper: Callable[[Any], Any]):
        if self.__value is None:
            return OptionalValue(None)
        return OptionalValue(mapper(self.__value))

    def filter(self, predicate: Callable[[Any], bool]):
        if self.__value is None or not predicate(self.__value):
            return OptionalValue(None)
        return OptionalValue(self.__value)

    @property
    def value(self):
        return self.__value
