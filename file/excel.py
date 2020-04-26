#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Author Kingen
@Date 2020/4/13
"""
import xlwt


def hyperlink(link_location: str, friendly_name: str):
    return xlwt.Formula('HYPERLINK("%s","%s")' % (link_location, friendly_name))
