# -*- coding: utf-8
import logging
import re
from os import environ
from logging.handlers import RotatingFileHandler


def _get_file_handler(log_name):
    # create time rotating file handler
    fh = logging.FileHandler(LOG_PATH + '/%s' % log_name)
    formatter = logging.Formatter(
        '%(asctime)s - p%(process)s - %(pathname)s:%(lineno)d - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    return fh


LOG_PATH = environ.get("CONSOLE_LOG_PATH", "/lain/logs/")
LOG_LEVEL = environ.get("CONSOLE_LOG_LEVEL", "INFO")


logger = logging.getLogger('console_log')
op_logger = logging.getLogger('console_op')


if LOG_LEVEL == "DEBUG":
    logger.setLevel(logging.DEBUG)
    op_logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
    op_logger.setLevel(logging.INFO)


op_logger.addHandler(_get_file_handler("console_op"))
logger.addHandler(_get_file_handler("console_log"))
