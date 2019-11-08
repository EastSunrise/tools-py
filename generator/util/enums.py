#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 枚举模块
@Module enums

@Author Kingen
@Date 2019/8/29
@Version 1.0
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


class Module(Enum):
    """
    类型所属模块枚举
    """
    Root = 'service'
    Client = 'client'
    Common = 'common'
    Dmo = 'dmo'
    Service = 'service-service'
    War = 'war'
