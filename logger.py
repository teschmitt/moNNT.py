import logging

# global_logger = multiprocessing.log_to_stderr(logging.DEBUG)
from logging.config import fileConfig

fileConfig("logging_conf.ini")


def global_logger() -> logging.Logger:
    fileConfig("logging_conf.ini")
    return logging.getLogger()
