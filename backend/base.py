from abc import ABC, abstractmethod
from logging import Logger
from typing import TYPE_CHECKING

from logger import global_logger

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


class Backend(ABC):
    logger: Logger
    server: "AsyncNNTPServer"

    def __init__(self, server: "AsyncNNTPServer"):
        self.logger = global_logger()
        self.server = server

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def call_command(self, nntp_command):
        pass

    @abstractmethod
    def save_article(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @property
    @abstractmethod
    def available_commands(self):
        pass
