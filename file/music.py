#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Operations for music files.

@Author Kingen
"""
import os.path
import re

__regex_title = re.compile(r'([^、()]+)(( ?\([^()]+\))*)')


def get_info(filename: str) -> dict:
    """
    Extracts info of a song from its filename.
    @param filename:
    @return:
    """
    basename, ext = os.path.splitext(filename)
    parts = basename.split(' - ')
    if len(parts) != 2:
        raise ValueError(filename)
    singers = [x.strip() for x in parts[0].split('、')]
    matcher = __regex_title.fullmatch(parts[1])
    if not matcher:
        raise ValueError(filename)
    name = matcher.group(1).strip()
    info = {
        'singers': sorted(singers),
        'name': name,
        'quality': ext
    }
    note = matcher.group(2)
    if note:
        info['notes'] = [x.strip() for x in note.strip('()').split(')(')]
    return info
