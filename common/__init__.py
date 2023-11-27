#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Common functions.

@Author Kingen
"""
import logging
import re
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
