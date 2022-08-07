#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Operations for wallpaper files.

@Author Kingen
"""
import os


def repkg_we(executable: str, dir_path: str):
    """
    Extracts wallpaper files of Wallpaper Engine with repkg.exe
    """
    count = 0
    for dirname in os.listdir(dir_path):
        subdir = dirname + '\\' + dirname
        if not os.path.isdir(subdir):
            continue
        output = subdir + '\\output'
        if os.path.exists(output):
            continue
        for filename in os.listdir(subdir):
            path = subdir + '\\' + filename
            if os.path.isfile(path) and filename.lower().endswith('.pkg'):
                print('Extracting ' + path)
                count += 1
                print(os.popen(f'"{executable}" extract "{path}" -o "{output}"').read())
                break
    if count == 0:
        print('No file is extracted')
    else:
        print(f'Extracted {count} files')
