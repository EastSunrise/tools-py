# global_log.py
import logging
import logging.config
import os

log_config = '../resources/logger_config.ini'
logging.config.fileConfig(log_config)
LOGGER = logging.getLogger('root')


class GlobalLog(object):
    def __init__(self):
        self.log_config = '../resources/logger_config.ini'

    def get_logger(self):
        logging.config.fileConfig(self.log_config)
        return logging.getLogger('root')


if __name__ == '__main__':
    GlobalLog()
