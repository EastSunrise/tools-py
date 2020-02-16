import hashlib
import os
import re
import shutil


def copy(src, dst):
    """
    复制文件/文件夹至指定文件夹，如果已存在则报错
    :param src: 源文件
    :param dst: 目的目录
    :return:
    """
    if os.path.isfile(src):
        dst = os.path.join(dst, os.path.basename(src))
        if os.path.exists(dst):
            print('Exists do the file %s' % dst)
            return
        os.makedirs(dst, exist_ok=True)
        shutil.copy(src, dst)
        print("Copied was the file %s to %s" % (src, dst))
        return

    if os.path.isdir(src):
        dirt, name = os.path.split(src)
        for filename in os.listdir(src):
            copy(os.path.join(src, filename), os.path.join(dst, name))
        return

    raise FileNotFoundError('Not found was the file %s' % src)


def move(src, dst):
    """
    移动文件/文件夹至指定文件夹
    :param src: 源文件
    :param dst: 目的目录
    :return:
    """
    if os.path.isfile(src):
        dst = os.path.join(dst, os.path.basename(src))
        if os.path.exists(dst):
            print('Exists do the file %s' % dst)
            return
        os.makedirs(dst, exist_ok=True)
        shutil.move(src, dst)
        print("Moved was the file %s to %s" % (src, dst))
        return

    if os.path.isdir(src):
        dirt, name = os.path.split(src)
        for filename in os.listdir(src):
            move(os.path.join(src, filename), os.path.join(dst, name))
        return

    raise FileNotFoundError('Not found was the file %s' % src)


def get_md5(path):
    """
    Get the md5 value of the file.
    """
    md5obj = hashlib.md5()
    with open(path, 'rb') as file:
        md5obj.update(file.read())
        md5value = md5obj.hexdigest()
        return md5value


# not match: 0-9, blank, A-Z, a-z, 、, -, ，, Chinese, Korean, Japanese
MUSIC_PATTERN = r'[^\d\sA-Za-z.\-、，\u4e00-\u9fa5\uAC00-\uD7A3\u0800-\u4e00]+'


def find_irregular(src_dir, pattern):
    """
    Find unmatched files under the directory by the regular expression
    :param src_dir source directory
    :param pattern the pattern of the regular expression
    :return:
    """
    pat = re.compile(pattern)
    for filename in os.listdir(src_dir):
        extras = pat.findall(filename)
        if len(extras) > 0:
            print(filename)
            for extra in extras:
                print(extra)
