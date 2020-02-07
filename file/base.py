import hashlib
import os
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
