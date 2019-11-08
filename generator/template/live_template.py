#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 动态模板
@Module live_template

@Author Kingen
@Date 2019/8/27
@Version 1.0
"""

from abc import abstractmethod

from generator.template.file_template import Template
from generator.util.config import LIVE_ENVIRONMENT


class LiveTemplate(Template):
    """
    动态模板
    """

    def format(self, **kwargs) -> str:
        """
        :return: 格式化动态模板
        """
        return LIVE_ENVIRONMENT.get_template(self._get_template()).render(**kwargs)

    @abstractmethod
    def _get_template(self):
        """
        :return: 对应动态模板在live目录下的相对路径
        """
        pass


class QueryColumns(LiveTemplate):
    """
    查询给定表的所有字段sql语句模板
    """

    def format(self, table_name) -> str:
        return super().format(
            TABLE_NAME=table_name
        )

    def _get_template(self):
        return 'query_columns.sql'
