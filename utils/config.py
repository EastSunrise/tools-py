import logging
import logging.config
import os

import yaml

if not os.path.exists('logs'):
    os.mkdir('logs')
with open(os.path.join(os.path.dirname(__file__), 'logging.yml'), 'r') as file:
    config = yaml.load(file.read(), Loader=yaml.Loader)
logging.config.dictConfig(config)


def get_logger(name='default'):
    """
    Get a common logger named by the module name.
    :param name: module name
    :return:
    """
    return logging.getLogger(name)
