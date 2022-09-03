#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Generates codes.

@Author Kingen
"""
from enum import Enum


class FormType(Enum):
    """
    搜索表单的输入类型
    """
    InputText = 0
    InputTextDate = 1
    InputTextDateTime = 2
    Select = 10
    SelectBean = 11


class ResultCellType(Enum):
    """
    列表查询结果字段展示类型
    """
    RString = 0
    RDate = 10
    RDateTime = 11
    REnum = 20


class JavaType(Enum):
    """
    常用Java类型枚举
    """
    Object = 0
    Integer = 10
    Long = 11
    Float = 12
    Double = 13
    BigDecimal = 14
    Date = 20
    String = 30
    IBaseEnum = 40
    Page = 50

    def get_dependency(self) -> str:
        """
        获取类型依赖
        :return: String等基础类型返回''
        """
        if self == JavaType.BigDecimal:
            return 'java.math.BigDecimal'
        if self == JavaType.Date:
            return 'java.util.Date'
        if self == JavaType.IBaseEnum:
            return 'sg.campaign.common.enums.IBaseEnum'
        if self == JavaType.Page:
            return 'com.kxd.framework.page.Page'
        return ''

    def get_form_type(self) -> FormType:
        """
        :return: 对应表单类型
        """
        if self == JavaType.IBaseEnum:
            return FormType.Select
        if self == JavaType.Date:
            return FormType.InputTextDateTime
        return FormType.InputText

    def get_result_type(self) -> ResultCellType:
        """
        :return: 对应结果展示类型
        """
        if self == JavaType.Date:
            return ResultCellType.RDate
        if self == JavaType.IBaseEnum:
            return ResultCellType.REnum
        return ResultCellType.RString


def convert_underline_to_upper_camel(under_str: str, separator='_') -> str:
    """
    Converts a string from under_score_case to CamelCase.
    """
    arr = under_str.lower().split(separator)
    return ''.join([x[0].upper() + x[1:] for x in arr])


def convert_camel_to_lower_underline(camel_str: str, separator='_') -> str:
    """
    Converts a string from CamelCase to under_score_case.
    """
    underline = ''
    for index, char in enumerate(camel_str):
        if index > 0 and char.isupper():
            underline += separator
        underline += char.lower()
    return underline


def convert_camel_to_upper_underline(camel_str: str, separator='_') -> str:
    """
    Converts a string from CamelCase to UNDER_SCORE_CASE.
    """
    underline = ''
    for index, char in enumerate(camel_str):
        if index > 0 and char.isupper():
            underline += separator
        underline += char.upper()
    return underline


def lower_first(text: str) -> str:
    """
    Lowers the first letter.
    """
    if not text or len(text) == 0:
        return text
    if text[0].isalpha():
        return text[0].lower() + text[1:]


def upper_first(text: str) -> str:
    """
    Uppers the first letter.
    """
    if not text or len(text) == 0:
        return text
    if text[0].isalpha():
        return text[0].upper() + text[1:]
