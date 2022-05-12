import asyncio
from asyncio import StreamReader, StreamWriter, Task
from logging import Logger
from socketserver import ForkingTCPServer
from typing import List, Optional, Union

import nntp_commands
from logger import global_logger
from models import Message, Newsgroup
from settings import settings
from status_codes import StatusCodes
from version import get_version


class NNTPServer(ForkingTCPServer):
    allow_reuse_address = 1
    if settings.MAX_CONNECTIONS:
        max_children = settings.MAX_CONNECTIONS


class AsyncTCPServer:
    def __init__(self, hostname: str, port: int) -> None:
        self.hostname: str = hostname
        self.port: int = port
        self.reader: StreamReader
        self.writer: StreamWriter
        self.clients: dict = {}
        self.logger: Logger = global_logger(__name__)
        self._terminated: bool = False
        self._empty_token_counter: int = 0
        self._cmd_args: Optional[list[str]] = None
        self._selected_group: Optional[Newsgroup] = None  # field to save a selected group
        self._selected_article: Optional[Message] = None  # field to save a selected group
        # self.sending_article: bool = False
        # self.auth_username

    def _send(self, writer: StreamWriter, send_obj: Union[List[str], str]) -> None:
        if type(send_obj) is str:
            self.logger.debug(f"server > {send_obj}")
            writer.write(f"{send_obj}\r\n".encode(encoding="utf-8"))
        else:
            send_obj.append(".")
            for line in send_obj:
                self.logger.debug(f"server > {line}")
                writer.write(f"{line}\r\n".encode(encoding="utf-8"))

    async def _accept_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        self.reader: StreamReader = reader
        self.writer: StreamWriter = writer

        task: Task = asyncio.create_task(self._handle_client(reader, writer))
        self.clients[task] = (reader, writer)

        def client_done(tsk: asyncio.Task):
            del self.clients[tsk]
            writer.close()
            self.logger.info("End Connection")

        task.add_done_callback(client_done)

        addr: str
        port: int
        addr, port = writer.get_extra_info(name="peername")
        self.logger.info(f"Connected to client at {addr}:{port}")

    async def _handle_client(self, reader, writer) -> None:
        if settings.SERVER_TYPE == "read-only":
            self._send(
                writer,
                StatusCodes.STATUS_READYNOPOST % (settings.NNTP_HOSTNAME, get_version()),
            )
        else:
            self._send(
                writer,
                StatusCodes.STATUS_READYOKPOST % (settings.NNTP_HOSTNAME, get_version()),
            )

        # main execution loop for handling a connection until it's closed
        while not self._terminated:
            try:
                # TODO: make timeout a setting
                incoming_data = await asyncio.wait_for(reader.readline(), timeout=43200.0)
            except TimeoutError as e:
                self.logger.error(f"ERROR: TimeoutError occurred. {e}")
                continue

            try:
                tokens: list[str] = (
                    incoming_data.decode(encoding="utf-8").strip().lower().split(" ")
                )
            except IOError:
                continue

            if all([t == "" for t in tokens]):
                self._empty_token_counter += 1
                if self._empty_token_counter >= settings.MAX_EMPTY_REQUESTS:
                    self.logger.warning(
                        "WARNING: Noping out because client is sending too many empty requests"
                    )
                    self._terminated = True
                continue
            else:
                self._empty_token_counter = 0

            self.logger.debug(f"{writer.get_extra_info(name='peername')} > {' | '.join(tokens)}")

            command: Optional[str] = tokens.pop(0) if len(tokens) > 0 else None
            self._cmd_args: Optional[list[str]] = tokens

            if command in nntp_commands.call_dict:
                self._send(writer, await nntp_commands.call_dict[command](self))

            if command == "quit":
                self._terminated = True

    async def start_serving(self):
        await asyncio.start_server(
            client_connected_cb=self._accept_client, host=self.hostname, port=self.port
        )

    @property
    def cmd_args(self) -> Optional[list[str]]:
        return self._cmd_args

    @property
    def terminated(self) -> bool:
        return self._terminated

    @property
    def selected_group(self) -> Optional[Newsgroup]:
        return self._selected_group

    @selected_group.setter
    def selected_group(self, val) -> None:
        self._selected_group = val

    @property
    def selected_article(self) -> Optional[Message]:
        return self._selected_article

    @selected_article.setter
    def selected_article(self, val) -> None:
        self._selected_article = val
