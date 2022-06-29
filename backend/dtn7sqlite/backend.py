from abc import ABC, abstractmethod


class Backend(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def call_command(self):
        pass

    @abstractmethod
    def save_article(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class DTN7Backend(Backend):
    def call_command(self):
        pass

    def stop(self):
        pass

    def start(self):
        pass

    def save_article(self):
        pass
