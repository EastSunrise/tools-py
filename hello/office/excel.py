#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description todo
@Module excel

@Author Kingen
@Date 2019/9/30
@Version 1.0
"""

from time import sleep
from tkinter import Tk

import win32com.client as win32

RANGE = range(3, 8)


def excel():
    app = 'Excel'
    xl = win32.gencache.EnsureDispatch('%s.Application' % app)
    ss = xl.Workbooks.Add()
    sh = ss.ActiveSheet
    xl.Visible = True
    sleep(1)
    sh.Cells(1, 1).Value = 'Python-to-%s Demo' % app
    sleep(1)
    for i in range(1, 15):
        sh.Cells(i, 1).Value = 'Line %d' % i
        sleep(1)
    sh.Cells(i + 2, 1).Value = "Th-th-th-that's all folks!"

    # ss.Close(False)
    # xl.Application.Quit()


if __name__ == '__main__':
    Tk().withdraw()
    excel()
