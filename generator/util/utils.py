import os


def convert_with_under2lower_camel(under_str, separator='_') -> str:
    """
    将下划线转换为驼峰字符串，开头小写
    """
    arr = filter(None, under_str.lower().split(separator))
    camel_result = ''
    j = 0
    for i in arr:
        if j == 0:
            camel_result = i
        else:
            camel_result = camel_result + i[0].upper() + i[1:]
        j += 1
    return camel_result


def convert_with_under2upper_camel(under_str, separator='_') -> str:
    """
    将下划线转换为驼峰字符串，开头大写
    """
    arr = filter(None, under_str.lower().split(separator))
    camel_result = ''
    for i in arr:
        camel_result = camel_result + i[0].upper() + i[1:]
    return camel_result


def convert_camel2lower_with_under(camel_word, separator='_') -> str:
    lower_with_under: str = ''
    for index, char in enumerate(camel_word):
        if index > 0 and char.isupper():
            lower_with_under = lower_with_under + separator
        lower_with_under = lower_with_under + char.lower()
    return lower_with_under


def convert_camel2upper_with_under(camel_word, separator='_') -> str:
    upper_with_under: str = ''
    for index, char in enumerate(camel_word):
        if index > 0 and char.isupper():
            upper_with_under = upper_with_under + separator
        upper_with_under = upper_with_under + char.upper()
    return upper_with_under


def lower_first(param) -> str:
    """
    小写首字母
    """
    if not param or len(param) == 0:
        return param
    if param[0].isalpha():
        return param[0].lower() + param[1:]


def upper_first(param) -> str:
    """
    大写首字母
    """
    if not param or len(param) == 0:
        return param
    if param[0].isalpha():
        return param[0].upper() + param[1:]


def search(root_dir, filename):
    """
    在指定目录下递归搜索文件
    :param root_dir: 搜索的目录
    :param filename: 文件全名
    :return: 文件所在目录，不存在返回False
    """
    for root, dirs, files in os.walk(root_dir):
        if filename in files:
            return os.path.join(root, filename)
    return False


def convert_column2field(column_name: str) -> str:
    """
    将数据库字段转换为POJO属性
    :param column_name:
    :return:
    """
    if column_name.startswith('IS'):
        column_name = column_name[2:]
    return convert_with_under2lower_camel(column_name)


def create_file(content, dst_dir, filename, overwrite=False, encoding='UTF-8'):
    """
    不存在则创建文件，存在则根据overwrite决定是否覆盖原文件
    :param encoding: 编码
    :param content: 生成内容
    :param overwrite: 是否覆盖原文件
    :param dst_dir: 目标目录
    :param filename: 生成的文件名
    :return:
    """
    print(content)
    exist_flag = os.path.exists(os.path.join(dst_dir, filename))
    from generator.util.config import LOGGER
    if not overwrite and exist_flag:
        LOGGER.info('Exists ' + filename + ' in ' + dst_dir)
        return

    with open(os.path.join(dst_dir, filename), 'w', encoding=encoding) as save_file:
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        save_file.write(content)
        save_file.close()
        LOGGER.info(('Create ' if not exist_flag else 'Overwrite ') + filename + ' in ' + dst_dir)
