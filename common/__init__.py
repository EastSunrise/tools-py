#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Common functions.

@Author Kingen
"""
import logging
import os.path
import re
import sys
from datetime import date, datetime
from json import JSONEncoder
from typing import Iterable, Callable, Dict, Any, List

formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(threadName)s [%(filename)s:%(lineno)d]: %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)


def get_executable_folder(file=__file__):
    if getattr(sys, 'frozen', False):
        # Running in bundled mode (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Running in normal Python script mode
        return os.path.dirname(os.path.abspath(file))


def get_logger(level=logging.DEBUG, console=True, file_dir=None):
    logger = logging.getLogger()
    logger.setLevel(level)
    if console:
        logger.addHandler(console_handler)
    if file_dir is None:
        file_dir = os.path.join(get_executable_folder(), 'logs')
    if not os.path.isdir(file_dir):
        os.makedirs(file_dir, exist_ok=True)
    fh_debug = logging.FileHandler(os.path.join(file_dir, 'debug.log'), encoding='UTF-8')
    fh_debug.setFormatter(formatter)
    fh_debug.addFilter(lambda r: r.levelno == logging.DEBUG)
    logger.addHandler(fh_debug)

    fh_info = logging.FileHandler(os.path.join(file_dir, 'info.log'), encoding='UTF-8')
    fh_info.setFormatter(formatter)
    fh_info.addFilter(lambda r: r.levelno == logging.INFO)
    logger.addHandler(fh_info)

    fh_warn = logging.FileHandler(os.path.join(file_dir, 'warning.log'), encoding='UTF-8')
    fh_warn.setFormatter(formatter)
    fh_warn.setLevel(logging.WARNING)
    logger.addHandler(fh_warn)
    return logger


def group_by(it: Iterable, key_func: Callable, value_func=lambda x: x) -> Dict[Any, List[Any]]:
    res = {}
    for x in it:
        key = key_func(x)
        if key in res:
            res[key].append(value_func(x))
        else:
            res[key] = [value_func(x)]
    return res


class OptionalValue:
    def __init__(self, value):
        self.__value = value

    @property
    def value(self):
        return self.__value

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

    def get(self, default=None):
        return self.__value or default

    def not_value(self, value):
        return self.filter(lambda x: x != value)

    def not_blank(self):
        if isinstance(self.__value, list):
            return self.map(lambda xs: [x for x in xs if len(x.strip()) > 0])
        return self.filter(lambda x: len(x.strip()) > 0)

    def strip(self, chars=None):
        if isinstance(self.__value, list):
            return self.map(lambda xs: [x.strip(chars) for x in xs])
        return self.map(lambda x: x.strip(chars))

    def split(self, pattern):
        return self.map(lambda x: re.split(pattern, x))


class ComplexEncoder(JSONEncoder):
    def default(self, o: Any) -> str:
        if isinstance(o, date):
            return str(o)
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        return str(o)


class YearMonth:
    regexp = re.compile('(\\d{4,})-(\\d{2})')

    def __init__(self, year: int, month: int):
        self.__year = year
        if month < 1 or month > 12:
            raise ValueError('month must be between 1 and 12')
        self.__month = month

    __slots__ = '__year', '__month'

    @property
    def year(self):
        return self.__year

    @property
    def month(self):
        return self.__month

    @classmethod
    def now(cls):
        today = date.today()
        return YearMonth(today.year, today.month)

    def plus_months(self, months: int):
        if months == 0:
            return self
        months += self.__year * 12 + (self.__month - 1)
        return YearMonth(months // 12, months % 12 + 1)

    @staticmethod
    def parse(ym_str: str):
        match = YearMonth.regexp.fullmatch(ym_str)
        if match is None:
            raise ValueError('cannot parse the string: ' + ym_str)
        return YearMonth(int(match.group(1)), int(match.group(2)))

    def __eq__(self, other):
        return self.__cmp(other) == 0

    def __le__(self, other):
        return self.__cmp(other) <= 0

    def __lt__(self, other):
        return self.__cmp(other) < 0

    def __ge__(self, other):
        return self.__cmp(other) >= 0

    def __gt__(self, other):
        return self.__cmp(other) > 0

    def __cmp(self, other):
        assert isinstance(other, YearMonth)
        cmp = self.__year - other.__year
        return cmp if cmp != 0 else self.__month - other.__month

    def __hash__(self) -> int:
        return self.__year ^ (self.__month << 27)

    def __str__(self) -> str:
        return '%04d-%02d' % (self.__year, self.__month)
