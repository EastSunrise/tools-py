import os
import shutil
from utils.global_log import LOGGER


def copy_file(src_path, dst_dir):
    if not os.path.isfile(src_path):
        LOGGER.warning("%s not exist!" % src_path)
        return -1
    src_dir, filename = os.path.split(src_path)  # 分离文件名和路径
    dst_path = os.path.join(dst_dir, filename)
    if os.path.exists(dst_path):
        LOGGER.info("File exists %s" % dst_path)
        return 0
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)  # 创建路径
    shutil.copy(src_path, os.path.join(dst_dir, filename))  # 复制文件
    LOGGER.info("Copied %s from %s to %s" % (filename, src_dir, dst_dir))
    return 1


def move_file(src_path, dst_dir):
    if not os.path.isfile(src_path):
        LOGGER.warning("%s not exist!" % src_path)
        return -1
    src_dir, filename = os.path.split(src_path)
    dst_path = os.path.join(dst_dir, filename)
    if os.path.exists(dst_path):
        LOGGER.info("File exists %s" % dst_path)
        return 0
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)  # 创建路径
    shutil.move(src_path, dst_path)  # 移动文件
    LOGGER.info("Moved %s from %s to %s" % (filename, src_dir, dst_dir))
    return -1


def create_file(path):
    if not os.path.exists(path):
        file = open(path, 'w')
        file.close()
        LOGGER.info("Created file %s" % path)
        return 1
    else:
        LOGGER.info("File exists %s" % path)
        return 0


if __name__ == '__main__':
    copy_file("E:\\Document\\My Kindle Content\\B00HJVC6KU_EBOK\\B00HJVC6KU_EBOK.azw", "E:\\Desktop")
