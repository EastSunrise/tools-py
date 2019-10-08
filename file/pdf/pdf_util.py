#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module pdf_util

@Author Kingen
@Date 2019/8/28
@Version 1.0
"""
import generator
import pdfkit
from generator import util
from generator.factory import Business

pdfkit.from_url('http://docs.jinkan.org/docs/jinja2/index.html', 'index.pdf')

if __name__ == '__main__':
    print(util)

