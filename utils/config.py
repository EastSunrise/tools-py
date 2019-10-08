# config.py
import logging
import logging.config
import os


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
        logging.config.fileConfig(self.log_config)
        return logging.getLogger(name)


LOGGER = GlobalLog('../resources/config/logger_config.ini').get_logger('root')
