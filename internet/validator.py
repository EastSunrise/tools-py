#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Validators for data.

@Author Kingen
"""
from re import Pattern
from urllib.parse import urlparse

from common import create_logger

log = create_logger(__name__)


def validate_not_blank(idx, field: str, value):
    if value is None:
        log.error('no value of field [%s], index=[%s]', field, idx)
        return False
    if not isinstance(value, str):
        log.error('not str value [%s] of field [%s], index=[%s]', type(value), field, idx)
        return False
    if value.strip() == '':
        log.error('blank str of field [%s], index=[%s]', field, idx)
        return False
    return True


def validate_pattern(obj: dict, field: str, key: str, regexp: Pattern):
    value = obj.get(field)
    if value is None:
        return True
    if not isinstance(value, str):
        log.error('not str value [%s] of field [%s], key=[%s]', type(value), field, obj[key])
        return False
    if regexp.fullmatch(value) is None:
        log.error('mismatched str [%s] of field [%s], key=[%s]', type(value), field, obj[key])
        return False
    return True


def validate_url(obj: dict, field: str, key: str):
    value = obj.get(field)
    if value is None:
        return True
    if not isinstance(value, str):
        log.error('not str value [%s] of field [%s], key=[%s]', type(value), field, obj[key])
        return False
    result = urlparse(value)
    if not all([result.scheme, result.netloc, result.path]):
        log.error('illegal url [%s] of field [%s], key=[%s]', type(value), field, obj[key])
        return False
    return True


def validate_range(obj: dict, field: str, key: str, minimum: int = 0, maximum: int = 0x7fffffffffffffff):
    value = obj.get(field)
    if value is None:
        return True
    if not isinstance(value, int):
        log.error('not int value [%s] of field [%s], key=[%s]', type(value), field, obj[key])
        return False
    if value < minimum or value > maximum:
        log.error('out of range int [%s] of field [%s], key=[%s]', type(value), field, obj[key])
        return False
    return True


def validate_list(idx, field, value, func, **kwargs):
    if value is None:
        return True
    if not isinstance(value, list):
        log.error('not list value [%s] of field [%s], index=[%s]', type(value), field, idx)
        return False
    all_valid = True
    for v in value:
        all_valid &= func(idx, field, v, kwargs)
    return all_valid
