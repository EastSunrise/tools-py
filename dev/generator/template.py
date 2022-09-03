#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Generates codes with templates.

@Author Kingen
"""
from abc import abstractmethod

from jinja2 import Environment, FileSystemLoader

FILE_ENVIRONMENT = Environment(loader=FileSystemLoader('templates'))
FILE_ENVIRONMENT.trim_blocks = True
FILE_ENVIRONMENT.lstrip_blocks = True


class Template:
    """
    Interface of templates.
    """

    @abstractmethod
    def format(self) -> str:
        """
        Returns formatted result.
        """
        pass


class FileTemplate(Template):
    """
    Abstract class of file templates.
    """

    def __init__(self, template_filename: str, **kwargs):
        """

        @param template_filename: the filename of the template under FILE_ENVIRONMENT, eg.'foo.jinja2'
        @param kwargs: arguments to format the template
        """
        self.__template = template_filename
        self.__kwargs = kwargs

    def format(self) -> str:
        """
        Formats the template with Jinja2 engine.
        """
        return FILE_ENVIRONMENT.get_template(self.__template).render(**self.__kwargs)


class JavaTemplate(FileTemplate):

    def __init__(self, template_filename: str, author: str, version: str, package: str, classname: str):
        """
        @param author:
        @param version:
        @param package: full path of the package to which the class belongs
        @param classname: in camel case
        """
        super().__init__(template_filename, package=package, author=author, version=version, ClassName=classname)


class QueryColumns(FileTemplate):
    """
    SQL to query for all columns of a specified table.
    """

    def __init__(self, table_name: str):
        super().__init__('query_columns.jinja2', TABLE_NAME=table_name)
