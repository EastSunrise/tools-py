import configparser
import logging
import logging.config
import os

from jinja2 import Environment, FileSystemLoader

from generator.util import utils


class Config(object):
    """
    读取配置参数
    """

    def __init__(self):
        self.parser = configparser.ConfigParser()
        self.parser.read('D:/Docs/PyCharm Projects/tools-py/generator/resources/config/config.ini', encoding='UTF-8')

        self.doc_dir = self.parser['dir']['doc_dir']
        self.db_dir = self.parser['dir']['sql_dir']

        self.service = self.parser['system_service']
        self.service_dir = self.service['root_dir']
        self.service_version = self.service['version']

        self.admin = self.parser['system_admin']
        self.admin_dir = self.admin['root_dir']
        self.admin_version = self.admin['version']

        custom = self.parser['custom']
        self.author = custom['author']
        self.overwrite = True if custom['overwrite'] == 'Y' else False


CONFIG = Config()


class GlobalLog(object):
    """
    日志全局配置
    """

    def __init__(self, config_file):
        """
        :param config_file: 配置文件
        """
        self.log_config = config_file

    def get_logger(self, name=None):
        if not os.path.exists('../logs'):
            os.mkdir('../logs')
        # todo 按日期生成日志
        return logging.getLogger(name)


LOGGER = GlobalLog('D:/Docs/PyCharm Projects/Tools/generator/resources/config/logger_config.ini').get_logger('root')

Environment.trim_blocks = True
Environment.lstrip_blocks = True

FILE_ENVIRONMENT = Environment(
    loader=FileSystemLoader('D:/Docs/PyCharm Projects/Tools/generator/templates/file'))
FILE_ENVIRONMENT.filters['convert_with_under2lower_camel'] = utils.convert_with_under2lower_camel
FILE_ENVIRONMENT.filters['convert_with_under2upper_camel'] = utils.convert_with_under2upper_camel
FILE_ENVIRONMENT.filters['convert_camel2lower_with_under'] = utils.convert_camel2lower_with_under
FILE_ENVIRONMENT.filters['convert_camel2upper_with_under'] = utils.convert_camel2upper_with_under
FILE_ENVIRONMENT.filters['lower_first'] = utils.lower_first
FILE_ENVIRONMENT.filters['upper_first'] = utils.upper_first
FILE_ENVIRONMENT.trim_blocks = True
FILE_ENVIRONMENT.lstrip_blocks = True

LIVE_ENVIRONMENT = Environment(
    loader=FileSystemLoader('D:/Docs/PyCharm Projects/Tools/generator/templates/live'))
