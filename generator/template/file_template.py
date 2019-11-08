#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 文件模板
@Module file_template

@Author Kingen
@Date 2019/8/27
@Version 1.0
"""

import os
from abc import abstractmethod, ABC
from datetime import datetime

from generator.util.config import CONFIG, FILE_ENVIRONMENT
from generator.util.utils import create_file


class Template:
    """
    模板接口
    """

    @abstractmethod
    def format(self):
        """
        格式化模板
        :return: 格式化结果
        """
        pass


class FileTemplate(Template):
    """
    模板抽象类
    """

    def create_file(self) -> None:
        """
        根据模板生成并创建文件
        """
        create_file(self.format(), self.get_full_dir(), self.get_filename(), CONFIG.overwrite)

    @abstractmethod
    def _get_template(self) -> str:
        """
        :return: file目录下模板的相对路径，eg.'dao.jinja2'
        """
        pass

    @abstractmethod
    def get_filename(self) -> str:
        """
        :return: 要生成的文件名
        """
        pass

    @abstractmethod
    def get_full_dir(self) -> str:
        """
        :return: 文件生成的完整目录
        """
        pass

    @abstractmethod
    def _get_format_dict(self) -> dict:
        """
        :return: 模板格式化参数
        """
        pass

    def format(self) -> str:
        """
        模板格式化
        """
        return FILE_ENVIRONMENT.get_template(self._get_template()).render(**self._get_format_dict())


class JavaTemplate(FileTemplate):
    """
    Java模板类
    """

    _src_java_dir = 'src/main/java'

    def get_full_package(self) -> str:
        """
        :return: Java类所在包
        """
        pass

    def get_classname(self) -> str:
        """
        :return: 类名
        """
        pass

    def _get_version(self) -> str:
        """
        :return: 系统版本
        """
        pass

    def get_full_dir(self) -> str:
        return os.curdir

    def _get_template(self) -> str:
        return 'java.jinja2'

    def _get_format_dict(self) -> dict:
        return dict(
            package=self.get_full_package(),
            author=CONFIG.author,
            date=datetime.now().strftime('%Y-%m-%d'),
            version=self._get_version(),
            ClassName=self.get_classname()
        )

    def get_filename(self) -> str:
        """
        :return: 类名 + '.java'
        """
        return self.get_classname() + '.java'


class ResourceTemplate(FileTemplate, ABC):
    """
    资源文件模板抽象类
    """
    _src_resources_dir = 'src/main/resources'


class WebTemplate(FileTemplate, ABC):
    """
    web前台页面模板
    """
    _src_webapp_dir = 'src/main/webapp'
