#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Edits the Windows registry to support custom protocol.

@author: Kingen
"""
import os
import re
import subprocess
import sys
import winreg
from tkinter import messagebox

CMD_DELEGATE_KEY = 'DelegateExecute'


def register_protocol(protocol: str, delegate: str):
    if not protocol or protocol.strip() == '':
        messagebox.showwarning('Warning', 'Protocol is empty')
        return
    protocol = protocol.strip()
    if not re.match(r'^[a-z]+$', protocol):
        messagebox.showwarning('Warning', f'Protocol only accepts lowercase letters: [{protocol}]')
        return
    delegate = os.path.abspath(delegate)
    if not os.path.exists(delegate):
        messagebox.showwarning('Warning', f'Delegate executable does not exist: [{delegate}]')
        return
    transfer = os.path.abspath(sys.argv[0])

    protocol_key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, protocol)
    winreg.SetValueEx(protocol_key, None, 0, winreg.REG_SZ, f'URL:{protocol}')
    winreg.SetValueEx(protocol_key, 'URL Protocol', 0, winreg.REG_SZ, '')

    shell_key = winreg.CreateKey(protocol_key, "shell")
    open_key = winreg.CreateKey(shell_key, "open")
    command_key = winreg.CreateKey(open_key, "command")
    winreg.SetValueEx(command_key, None, 0, winreg.REG_SZ, f'"{transfer}" open {protocol} "%1"')
    winreg.SetValueEx(command_key, CMD_DELEGATE_KEY, 0, winreg.REG_SZ, f'{delegate}')
    messagebox.showinfo('Success', f'Protocol [{protocol}] was registered with delegate executable [{delegate}]')


def open_url(protocol: str, url: str):
    if not protocol or protocol.strip() == '':
        messagebox.showwarning('Warning', 'Protocol is empty')
    protocol = protocol.strip()
    if not url or url.strip() == '':
        messagebox.showwarning('Warning', 'The URL is empty')
    url = url.strip()
    if not url.startswith(protocol + '://'):
        messagebox.showwarning('Warning', f'The URL [{url}] does not match the protocol [{protocol}]')
    url = url[len(protocol) + 3:]

    protocol_key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, protocol)
    shell_key = winreg.OpenKey(protocol_key, "shell")
    open_key = winreg.OpenKey(shell_key, "open")
    command_key = winreg.OpenKey(open_key, "command")
    delegate = winreg.QueryValueEx(command_key, CMD_DELEGATE_KEY)[0]
    if delegate == '':
        messagebox.showwarning('Warning', 'Cannot find an executable to open the url')
        return
    subprocess.Popen([delegate, url])


# pyinstaller -n registry -w -F registry.py
if __name__ == '__main__':
    if len(sys.argv) < 3:
        messagebox.showwarning('Warning', 'At least 2 arguments are required')
    elif len(sys.argv) == 3:
        register_protocol(sys.argv[1], sys.argv[2])
    else:
        cmd = sys.argv[1]
        if cmd == 'reg' or cmd == 'register':
            register_protocol(sys.argv[2], sys.argv[3])
        elif cmd == 'open':
            open_url(sys.argv[2], sys.argv[3])
        else:
            messagebox.showwarning('Warning', f'Unknown command: [{cmd}]', )
