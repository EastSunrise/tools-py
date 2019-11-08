#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description 网页解析器
@Module parser

@Author Kingen
@Date 2019/10/14
@Version 1.0
"""
from html.parser import HTMLParser


class HrefParser(HTMLParser):
    def error(self, message):
        pass
