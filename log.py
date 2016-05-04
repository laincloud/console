# -*- coding: utf-8
import logging
import re
from os import environ
from logging.handlers import TimedRotatingFileHandler


def _get_file_handler(log_name):
    # create time rotating file handler
    fh = TimedRotatingFileHandler(LOG_PATH + '/%s' % log_name, 'W0',
                                  interval=2, backupCount=12
                                  )
    fh.suffix = "%Y-%m-%d.log"
    fh.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}.log$")

    formatter = logging.Formatter(
        '%(asctime)s - p%(process)s - %(pathname)s:%(lineno)d - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)
    return fh


LOG_PATH = environ.get("CONSOLE_LOG_PATH", "./logs/")
LOG_LEVEL = environ.get("CONSOLE_LOG_LEVEL", "DEBUG")

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
