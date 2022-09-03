#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
Operations for video files.

@Author Kingen
"""
import functools
import math
import os

from pymediainfo import MediaInfo

from file import cmp_filename


class Ffmpeg:
    def __init__(self, executable: str):
        self.__executable = executable

    def convert_format(self, dir_path: str, src_fmt: str, dest_fmt: str):
        """
        All files of the source format in the directory will be converted to target format with ffmpeg.
        @param dir_path: directory where files will be converted
        @param src_fmt: source format of files to be converted
        @param dest_fmt: target format files converted to
        @return:
        """
        src_ext = '.' + src_fmt.upper()
        for filename in os.listdir(dir_path):
            basename, ext = os.path.splitext(filename)
            if ext.upper() != src_ext:
                continue
            filepath = os.path.join(dir_path, filename)
            dest_path = os.path.join(dir_path, f"{basename}.{dest_fmt}")
            print(os.popen(f'"{self.__executable}" -i "{filepath}" -c copy "{dest_path}"').read())


def rename_season_episodes(season_dir: str, header='Ep'):
    """
    Formats filenames of episodes in order.
    """
    files = os.listdir(season_dir)
    files.sort(key=functools.cmp_to_key(cmp_filename))
    pat = f"{header}%0{int(math.log10(len(files))) + 1}d"
    pairs = []
    for i, filename in enumerate(files):
        src = os.path.join(season_dir, filename)
        if os.path.isdir(src):
            raise FileExistsError("Unexpected directory")
        suffix = os.path.splitext(filename)[-1]
        dest = os.path.join(season_dir, (pat % (i + 1)) + suffix)
        pairs.append([src, dest])
    for pair in pairs:
        print(f'Renaming "{pair[0]}" to "{pair[1]}"')
    print("Press enter or input 'Y/y' to execute, otherwise quit:")
    yes = input()
    if "Y" == yes or "y" == yes or "" == yes:
        for pair in pairs:
            os.rename(pair[0], pair[1])
        print(f"{len(pairs)} files are renamed")
    else:
        print("No file is renamed")


def rename_series_episodes(series_dir: str, header='Ep'):
    """
    Formats filenames of episodes within seasons.
    """
    for dirname in os.listdir(series_dir):
        dir_path = os.path.join(series_dir, dirname)
        if os.path.isdir(dir_path):
            rename_season_episodes(dir_path, header)
            print("Press any key to continue:")
            input()


def separate_srt(filepath: str):
    """
    Separates the .srt file with two languages to separated files.
    @param filepath: the path of the source file. Every 4 lines form a segment and segments are split by a space line.
    """
    if os.path.isfile(filepath) and filepath.lower().endswith('.srt'):
        root, ext = os.path.splitext(filepath)
        with open(filepath, mode='r', encoding='utf-8') as fp:
            with open(root + '_1' + ext, 'w', encoding='utf-8') as f1:
                with open(root + '_2' + ext, 'w', encoding='utf-8') as f2:
                    segment = []
                    for line in fp.readlines():
                        if line != '\n':
                            segment.append(line)
                        else:
                            if len(segment) != 4:
                                print(f'Special lines in No. {segment[0]}')
                            f1.writelines([
                                segment[0], segment[1], segment[2], '\n'
                            ])
                            f2.writelines([
                                segment[0], segment[1], segment[3], '\n'
                            ])
                            segment = []


def get_duration(filepath):
    media_info = MediaInfo.parse(filepath)
    tracks = dict([(x.track_type, x) for x in media_info.tracks])
    d = tracks['General'].duration
    if isinstance(d, int):
        return d
    if 'Video' in tracks:
        d = tracks['Video'].duration
        if isinstance(d, int):
            return d
    raise IOError('Duration Not Found')


def print_size(size: int):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return '%.2f %s' % (size, unit)
        size /= 1024
    return '%.2f %s' % (size, 'PB')
