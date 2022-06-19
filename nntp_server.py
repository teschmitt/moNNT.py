import asyncio
from asyncio import StreamReader, StreamWriter, Task
from logging import Logger
from socketserver import ForkingTCPServer
from typing import List, Optional, Union

from py_dtn7 import DTNRESTClient, DTNWSClient

from backend.dtn7sqlite import nntp_commands
from backend.dtn7sqlite.save import save_article
from logger import global_logger
from models import Message, Newsgroup
from settings import settings
from status_codes import StatusCodes
from utils import get_version


class NNTPServer(ForkingTCPServer):
    allow_reuse_address = 1
    if settings.MAX_CONNECTIONS:
        max_children = settings.MAX_CONNECTIONS


class AsyncTCPServer:
    def __init__(self, hostname: str, port: int, backend: Optional[DTNWSClient]) -> None:
        self.hostname: str = hostname
        self.port: int = port
        self.reader: StreamReader
        self.writer: StreamWriter
        self.clients: dict = {}
        self.logger: Logger = global_logger()
        self._terminated: bool = False
        self._empty_token_counter: int = 0
        self._cmd_args: Optional[list[str]] = None
        self._selected_group: Optional[Newsgroup] = None  # field to save a selected group
        self._selected_article: Optional[Message] = None  # field to save a selected group
        self._post_mode: bool = False
        self._article_buffer: list[str] = []
        self._command: Optional[str]
        self._dtn_rest_client: DTNRESTClient = DTNRESTClient()
        self._backend: Optional[DTNWSClient] = backend
        # self.auth_username

    def _send(self, send_obj: Union[List[str], str]) -> None:
        if type(send_obj) is str:
            self.logger.debug(f"server > {send_obj}")
            self.writer.write(f"{send_obj}\r\n".encode(encoding="utf-8"))
        else:
            send_obj.append(".")
            for line in send_obj:
                self.logger.debug(f"server > {line}")
                self.writer.write(f"{line}\r\n".encode(encoding="utf-8"))

    async def _accept_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        self.reader: StreamReader = reader
        self.writer: StreamWriter = writer

        task: Task = asyncio.create_task(self._handle_client(reader, writer))
        self.clients[task] = (reader, writer)

        def client_done(tsk: asyncio.Task):
            del self.clients[tsk]
            writer.close()
            self._empty_token_counter = 0
            self._cmd_args = None
            self._selected_group = None
            self._selected_article = None
            self._post_mode = False
            self._article_buffer = []
            self._command = None
            self.logger.info("End Connection")

        task.add_done_callback(client_done)

        addr: str
        port: int
        addr, port = writer.get_extra_info(name="peername")
        self.logger.info(f"Connected to client at {addr}:{port}")

    async def _handle_client(self, reader, writer) -> None:
        self._terminated = False
        self._empty_token_counter = 0

        if settings.SERVER_TYPE == "read-only":
            self._send(
                StatusCodes.STATUS_READYNOPOST % (settings.NNTP_HOSTNAME, get_version()),
            )
        else:
            self._send(
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

            self.logger.debug(
                f"{writer.get_extra_info(name='peername')} >"
                f" {incoming_data.decode(encoding='utf-8').strip()}"
            )

            if self._post_mode:
                # only rstrip in order to preserve indentation in body
                data_decode = incoming_data.decode(encoding="utf-8").rstrip()
                if data_decode == ".":
                    try:
                        await save_article(self)
                        self._send(StatusCodes.STATUS_POSTSUCCESSFUL)
                    except Exception as e:  # noqa E722
                        self.logger.error(e)
                        self._send(StatusCodes.ERR_NOTPERFORMED)
                    self.post_mode = False
                    self._article_buffer = []
                else:
                    self._article_buffer.append(data_decode)
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

            self._command = tokens.pop(0) if len(tokens) > 0 else None
            self._cmd_args: Optional[list[str]] = tokens

            if self._command in nntp_commands.call_dict:
                try:
                    self._send(await nntp_commands.call_dict[self._command](self))
                except Exception as e:
                    self.logger.exception(e)
                    self._terminated = True
            else:
                # command is not in list of implemented capabilities
                self._send(StatusCodes.ERR_CMDSYNTAXERROR)

            if self._command == "quit":
                self._terminated = True

    async def start_serving(self):
        await asyncio.start_server(
            client_connected_cb=self._accept_client, host=self.hostname, port=self.port
        )

    @property
    def article_buffer(self):
        return self._article_buffer

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, new_backend: DTNWSClient):
        self._backend = new_backend

    @property
    def cmd_args(self) -> Optional[list[str]]:
        return self._cmd_args

    @property
    def command(self) -> Optional[str]:
        return self._command

    @property
    def dtn_rest_client(self):
        return self._dtn_rest_client

    @property
    def dtn_ws_client(self):
        return self._backend

    @property
    def post_mode(self) -> bool:
        return self._post_mode

    @post_mode.setter
    def post_mode(self, val) -> None:
        self._post_mode = val

    @property
    def selected_article(self) -> Optional[Message]:
        return self._selected_article

    @selected_article.setter
    def selected_article(self, val) -> None:
        self._selected_article = val

    @property
    def selected_group(self) -> Optional[Newsgroup]:
        return self._selected_group

    @selected_group.setter
    def selected_group(self, val) -> None:
        self._selected_group = val

    @property
    def terminated(self) -> bool:
        return self._terminated
