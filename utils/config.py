import logging
import logging.config
import os

import yaml


def get_logger(name):
    """
    Get a common logger named by the module name.
    :param name: module name
    :return:
    """
    if not os.path.exists('../logs'):
        os.mkdir('../logs')
    with open('logging.yml', 'r') as file:
        config = yaml.load(file.read(), Loader=yaml.Loader)
    logging.config.dictConfig(config)
    return logging.getLogger(name)


if __name__ == '__main__':
    logger = get_logger(__name__)
    logger.info('main')
