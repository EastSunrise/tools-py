#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module main

@Author Kingen
@Date 2019/10/31
@Version 1.0
"""
from datetime import datetime

if __name__ == '__main__':
    start = datetime(2020, 2, 9)
    end = datetime(2020, 7, 1)
    print((end - start).days)
