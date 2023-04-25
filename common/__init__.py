#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Common functions.

@Author Kingen
"""
import logging
from datetime import date, datetime
from json import JSONEncoder
from typing import Iterable, Callable, Dict, Any, List


def group_by(it: Iterable, key_func: Callable, value_func=lambda x: x) -> Dict[Any, List[Any]]:
    res = {}
    for x in it:
        key = key_func(x)
        if key in res:
            res[key].append(value_func(x))
        else:
            res[key] = [value_func(x)]
    return res


def create_logger(name: str, level=logging.INFO, console=True, file_path=None):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    fmt = logging.Formatter(fmt='%(asctime)s %(levelname)s %(threadName)s [%(filename)s:%(lineno)d]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    if file_path:
        fh = logging.FileHandler(file_path, encoding='UTF-8')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


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

    def not_empty(self):
        return self.filter(lambda x: len(x) > 0)

    @property
    def value(self):
        return self.__value


class ComplexEncoder(JSONEncoder):
    def default(self, o: Any) -> str:
        if isinstance(o, date):
            return str(o)
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        return str(o)
