#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description common methods
@Author Kingen
@Date 2020/4/12
"""

CHINESE_NUMERALS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']


def merge_dict(dict1: dict, dict2: dict):
    """
    Merge dict2 into dict1 recursively
    """
    for key, value in dict2.values():
        if key in dict1 and isinstance(value, dict) and isinstance(dict1[key], dict):
            merge_dict(dict1[key], value)
        else:
            dict1[key] = value


def num2chinese(num: int) -> str:
    """
    transfer Arabic numerals to Chinese numerals
    """
    if num <= 0 or num > 20:
        raise ValueError
    if num <= 10:
        return CHINESE_NUMERALS[num]
    if num == 20:
        return '二十'
    return '十' + CHINESE_NUMERALS[num - 10]
