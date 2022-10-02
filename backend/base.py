from abc import ABC, abstractmethod
from logging import Logger
from typing import TYPE_CHECKING, List

from logger import global_logger

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


class Backend(ABC):
    logger: Logger
    server: "AsyncNNTPServer"

    def __init__(self, server: "AsyncNNTPServer"):  # , loop: AbstractEventLoop):
        self.logger = global_logger()
        self.server = server

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    async def save_article(self, article_buffer: List[str]):
        pass

    @abstractmethod
    def stop(self):
        pass

    @property
    @abstractmethod
    def available_commands(self):
        pass
