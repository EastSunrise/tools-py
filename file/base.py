import hashlib
import os
import shutil

from win32comext.shell import shell
from win32comext.shell.shellcon import FO_DELETE, FOF_ALLOWUNDO, FO_COPY

from utils import config

logger = config.get_logger(__name__)

st_blksize = 1048576  # 1MB


def find_duplicate(dst_dir, get_key, recursive=False):
    """
    Find duplicate files.
    :param dst_dir: directory to filter
    :param recursive: if search the sub folders recursively.
    :param get_key: function to get the unique key of the file
    """
    files = []
    if recursive:
        for root, dirnames, filenames in os.walk(dst_dir):
            for filename in filenames:
                files.append(os.path.join(root, filename))
    else:
        for filename in os.listdir(dst_dir):
            files.append(os.path.join(dst_dir, filename))
    file_set = {}
    for filepath in files:
        file_key = get_key(filepath)
        if file_key in file_set:
            file_set[file_key].append(filepath)
        else:
            file_set[file_key] = [filepath]
    for same_files in file_set.values():
        if len(same_files) > 1:
            print(same_files)


def copy(src, dst):
    """
    Copy a big file
    :return:
    """
    if os.path.isfile(dst):
        logger.warning('File exists: %s', dst)
        return 1
    src_md5 = get_md5(src)
    logger.info('Copy file from %s to %s', src, dst)
    code, msg = shell_file_operation(0, FO_COPY, src, dst, FOF_ALLOWUNDO)[0]
    if code != 0:
        logger.error('Failed to copy file: %s', msg)
        return code
    if get_md5(dst) != src_md5:
        logger.error('File corrupted while copying')
        return 2
    return 0


def move(src, dst_dir):
    """
    Move a file or directory to target directory. Print a message if target file exists.
    :param src: source file or directory
    :param dst_dir: target directory
    :return:
    """
    if os.path.isfile(src):
        dst_path = os.path.join(dst_dir, os.path.basename(src))
        if os.path.exists(dst_path):
            logger.info('Exist does the file %s', dst_path)
            return
        os.makedirs(dst_dir, exist_ok=True)
        shutil.move(src, dst_path)
        logger.info('Moved was the file %s to %s', (src, dst_path))
        return

    if os.path.isdir(src):
        dirt, name = os.path.split(src)
        for filename in os.listdir(src):
            move(os.path.join(src, filename), os.path.join(dst_dir, name))
        return

    raise FileNotFoundError('Not found was the file %s' % src)


def get_md5(path, block_size=st_blksize):
    """
    Get the md5 value of the file.
    """
    md5obj = hashlib.md5()
    with open(path, 'rb') as fp:
        read_size = 0
        size = os.path.getsize(path)
        while True:
            block = fp.read(block_size)
            read_size += block_size
            print('\rComputing md5: %.2f%%' % (read_size * 100 / size), end='', flush=True)
            if block is None or len(block) == 0:
                print()
                break
            md5obj.update(block)
        md5value = md5obj.hexdigest()
        return md5value


def del_to_recycle(filepath):
    logger.info('Delete to recycle bin: %s', filepath)
    return shell_file_operation(0, FO_DELETE, filepath, None, FOF_ALLOWUNDO)


def shell_file_operation(file_handle, func, p_from, p_to, flags, name_dict=None, progress_title=None):
    """

    :param file_handle:
    :param func: FO_COPY/FO_RENAME/FO_MOVE/FO_DELETE
    :param p_from:
    :param p_to:
    :param flags: FOF_FILESONLY | FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_NOERRORUI
                    | FOF_RENAMEONCOLLISION | FOF_SILENT | FOF_WANTMAPPINGHANDLE
    :param name_dict: new_filepath-old_filepath dict
    :param progress_title: title of progress dialog
    :return:
    """
    code = shell.SHFileOperation((file_handle, func, p_from, p_to, flags, name_dict, progress_title))[0]
    if code == 0:
        return 0, 'OK'
    if code == 2:
        return 2, 'File Not Found'
    return code, 'Unknown Error'
