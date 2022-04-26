import asyncio
from asyncio import StreamWriter, StreamReader, Task
from logging import Logger
from socketserver import ForkingTCPServer
from typing import Union, List, Tuple

from logger import global_logger
from nntp_commands import call_dict
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

    def _send_array(
        self, writer: StreamWriter, send_obj: Union[List[str], str]
    ) -> None:
        if type(send_obj) is str:
            # there has been an error and we're only returning the error code
            self._send_str(writer, send_obj)
        else:
            send_obj.append(".")
            for line in send_obj:
                self.logger.debug(f"server > {line}")
                writer.write(f"{line}\r\n".encode(encoding="utf-8"))

    def _send_str(self, writer: StreamWriter, send_str: str) -> None:
        self.logger.debug(f"server > {send_str}")
        writer.write(f"{send_str}\r\n".encode(encoding="utf-8"))

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
        terminated: bool = False
        empty_token_counter: int = 0
        selected_group: str = ""  # variable to save a selected group for later
        selected_article: str = ""  # variable to save a selected group for later
        # sending_article: bool = False
        # auth_username

        if settings.SERVER_TYPE == "read-only":
            self._send_str(
                writer,
                StatusCodes.STATUS_READYNOPOST
                % (settings.NNTP_HOSTNAME, get_version()),
            )
        else:
            self._send_str(
                writer,
                StatusCodes.STATUS_READYOKPOST
                % (settings.NNTP_HOSTNAME, get_version()),
            )

        # main execution loop for handling a connection until it's closed
        while not terminated:
            try:
                # TODO: make timeout a setting
                incoming_data = await asyncio.wait_for(
                    reader.readline(), timeout=43200.0
                )
            except TimeoutError as e:
                self.logger.error(f"ERROR: TimeoutError occurred. {e}")
                continue

            try:
                tokens = (
                    incoming_data.decode(encoding="utf-8").strip().lower().split(" ")
                )
            except IOError:
                continue

            if all([t == "" for t in tokens]):
                empty_token_counter += 1
                # TODO: make empty_token_counter a setting
                if empty_token_counter == 10:
                    self.logger.warning(
                        f"WARNING: Noping out because client is sending too many empty requests"
                    )
                    terminated = True
                continue
            else:
                empty_token_counter = 0

            self.logger.debug(
                f"{writer.get_extra_info(name='peername')} > {' | '.join(tokens)}"
            )

            command = tokens.pop(0)

            # special case: loading messages first sets a group and then specifies which
            # headers or article to load, so we save the group for the next call
            if command == "group":
                # Todo: Error handling in here if tokens[0] does not exist
                selected_group = tokens[0]
            elif command == "article":
                # Todo: Error handling in here if tokens[0] does not exist
                selected_article = tokens[0]
                tokens = [selected_group] + [selected_article] + tokens
            elif command in ["over", "xover"]:
                tokens = [selected_group] + tokens

            if command in ["mode", "group", "capabilities", "over", "xover"]:
                self._send_str(writer, await call_dict[command](tokens))
            elif command in ["article", "list"]:
                self._send_array(writer, await call_dict[command](tokens))

    async def start_serving(self):
        await asyncio.start_server(
            client_connected_cb=self._accept_client, host=self.hostname, port=self.port
        )
