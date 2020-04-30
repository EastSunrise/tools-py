import hashlib
import os
import shutil


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


def copy(src, dst_dir):
    """
    Copy a file or directory to target directory. Print a message if target file exists.
    :param src: source file or directory
    :param dst_dir: target directory
    :return:
    """
    if os.path.isfile(src):
        dst_path = os.path.join(dst_dir, os.path.basename(src))
        if os.path.exists(dst_path):
            print('Exist does the file %s' % dst_path)
            return
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy(src, dst_path)
        print("Copied was the file from %s to %s" % (src, dst_dir))
        return

    if os.path.isdir(src):
        dirt, name = os.path.split(src)
        for filename in os.listdir(src):
            copy(os.path.join(src, filename), os.path.join(dst_dir, name))
        return

    raise FileNotFoundError('Not found was the file %s' % src)


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
            print('Exist does the file %s' % dst_path)
            return
        os.makedirs(dst_dir, exist_ok=True)
        shutil.move(src, dst_path)
        print("Moved was the file %s to %s" % (src, dst_path))
        return

    if os.path.isdir(src):
        dirt, name = os.path.split(src)
        for filename in os.listdir(src):
            move(os.path.join(src, filename), os.path.join(dst_dir, name))
        return

    raise FileNotFoundError('Not found was the file %s' % src)


def get_md5(path):
    """
    Get the md5 value of the file.
    """
    md5obj = hashlib.md5()
    with open(path, 'rb') as fp:
        md5obj.update(fp.read())
        md5value = md5obj.hexdigest()
        return md5value
