import asyncio
from asyncio import StreamReader, StreamWriter, Task
from logging import Logger
from typing import List, Optional, Union

from backend.base import Backend
from client_connection import ClientConnection
from logger import global_logger
from models import Message, Newsgroup


class AsyncNNTPServer:
    def __init__(self, hostname: str, port: int) -> None:
        self.hostname: str = hostname
        self.port: int = port
        self.clients: dict = {}
        self.logger: Logger = global_logger()
        self._terminated: bool = False
        self._empty_token_counter: int = 0
        self._cmd_args: Optional[List[str]] = None
        self._selected_group: Optional[Newsgroup] = None  # field to save a selected group
        self._selected_article: Optional[Message] = None  # field to save a selected group
        self._post_mode: bool = False
        self._article_buffer: List[str] = []
        self._command: Optional[str]
        self._backend: Optional[Backend] = None
        # self.auth_username

    def send(self, writer: StreamWriter, send_obj: Union[List[str], str]) -> None:
        if type(send_obj) is str:
            self.logger.debug(f"server > {send_obj}")
            writer.write(f"{send_obj}\r\n".encode(encoding="utf-8"))
        else:
            send_obj.append(".")
            for line in send_obj:
                self.logger.debug(f"server > {line}")
                writer.write(f"{line}\r\n".encode(encoding="utf-8"))

    async def _accept_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        """
        Accepts a new client and transfers control of the reader and writer to it
        """
        client_conn: ClientConnection = ClientConnection(server=self, reader=reader, writer=writer)
        task: Task = asyncio.create_task(client_conn.handle_client())
        self.clients[task] = (reader, writer)

        def client_done(tsk: asyncio.Task):
            self.clients[tsk].stop()
            del self.clients[tsk]
            self.logger.info("End Connection")

        task.add_done_callback(client_done)

        addr: str
        port: int
        addr, port = writer.get_extra_info(name="peername")
        self.logger.info(f"Connected to client at {addr}:{port}")

    async def start_serving(self):
        await asyncio.start_server(
            client_connected_cb=self._accept_client, host=self.hostname, port=self.port
        )
        if self.backend is not None:
            await self.backend.start()

    def stop_serving(self) -> None:
        self._terminated = True
        if self.backend is not None:
            self.backend.stop()

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, new_backend: Backend):
        self._backend = new_backend

    @property
    def terminated(self) -> bool:
        return self._terminated
