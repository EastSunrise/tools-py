#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Basic operations for files.

@Author Kingen
"""
import hashlib
import os
import shutil
from typing import List

from pypinyin.constants import Style
from pypinyin.core import pinyin

import common


def flat_dir(root: str):
    for dirname in os.listdir(root):
        dirpath = os.path.join(root, dirname)
        if os.path.isdir(dirpath):
            for filename in os.listdir(dirpath):
                filepath = os.path.join(dirpath, filename)
                dst = shutil.move(filepath, root)
                print(f'{filepath} is moved to {dst}')
            os.rmdir(dirpath)


def find_duplicate(dst_dirs) -> List[List[str]]:
    """
    @param dst_dirs: a directory or directories to filter, any one should not be subdirectory of another one
    """
    all_files = []
    if isinstance(dst_dirs, str):
        dst_dirs = [dst_dirs]
    for dst_dir in dst_dirs:
        for dirpath, dirnames, filenames in os.walk(dst_dir):
            for filename in filenames:
                all_files.append(os.path.join(dirpath, filename))

    same_files = []
    by_size = common.group_by(all_files, lambda x: os.path.getsize(x))
    for size_files in by_size.values():
        if len(size_files) <= 1:
            continue
        by_md5 = common.group_by(size_files, get_md5)
        for md5_files in by_md5.values():
            if len(md5_files) <= 1:
                continue
            arrays = []
            for file in md5_files:
                unique = True
                for arr in arrays:
                    if is_same_file(file, arr[0]):
                        arr.append(file)
                        unique = False
                        break
                if unique:
                    arrays.append([file])
            for arr in arrays:
                if len(arr) > 1:
                    arr.sort(key=lambda x: [pinyin(i, style=Style.TONE3) for i in x])
                    same_files.append(arr)
    return same_files


def cmp_filename(filename1: str, filename2: str) -> int:
    """
    Compares filenames treating digits as number.
    """
    i1 = i2 = 0
    len1 = len(filename1)
    len2 = len(filename2)
    while i1 < len1 and i2 < len2:
        c1 = filename1[i1]
        c2 = filename2[i2]
        if c1.isdigit() and c2.isdigit():
            j1 = i1 + 1
            j2 = i2 + 1
            while j1 < len1 and filename1[j1].isdigit():
                j1 += 1
            while j2 < len2 and filename2[j2].isdigit():
                j2 += 1
            num1 = int(filename1[i1:j1])
            num2 = int(filename2[i2:j2])
            if num1 < num2:
                return -1
            if num1 > num2:
                return 1
            i1 = j1
            i2 = j2
        else:
            if c1 < c2:
                return -1
            if c1 > c2:
                return 1
            i1 += 1
            i2 += 1


st_blksize = 1048576  # 1MB


def get_md5(path, block_size=st_blksize) -> str:
    """
    Gets the md5 value of the file.
    """
    md5obj = hashlib.md5()
    with open(path, 'rb') as fp:
        read_size = 0
        size = os.path.getsize(path)
        while True:
            block = fp.read(block_size)
            if block is None or len(block) == 0:
                if read_size > 0:
                    print()
                break
            read_size += len(block)
            print(f"\rComputing md5 of '{path}': %.2f%%" % (read_size * 100 / size), end='', flush=True)
            md5obj.update(block)
        return md5obj.hexdigest()


def is_same_file(file1, file2, block_size=st_blksize):
    size = os.path.getsize(file1)
    if size != os.path.getsize(file2):
        return False
    with open(file1, 'rb') as fp1:
        with open(file2, 'rb') as fp2:
            read_size = 0
            while True:
                block1 = fp1.read(block_size)
                block2 = fp2.read(block_size)
                if block1 != block2:
                    if read_size > 0:
                        print()
                    return False
                if not block1 or len(block1) == 0:
                    if read_size > 0:
                        print()
                    return True
                read_size += len(block1)
                print(f"\rComparing '{file1}' and '{file2}': %.2f%%" % (read_size * 100 / size), end='', flush=True)
