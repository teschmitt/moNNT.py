from asyncio import StreamReader, StreamWriter, wait_for
from logging import Logger
from typing import TYPE_CHECKING, List, Optional

from config import server_config
from logger import global_logger
from models import Message, Newsgroup
from status_codes import StatusCodes
from utils import get_version

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


class ClientConnection:
    """
    Holds all state of a client connection to the server.
    """

    def __init__(
        self, server: "AsyncNNTPServer", reader: StreamReader, writer: StreamWriter
    ) -> None:
        self._server: "AsyncNNTPServer" = server
        self._reader: StreamReader = reader
        self._writer: StreamWriter = writer
        self.logger: Logger = global_logger()
        self._terminated: bool = False
        self._empty_token_counter: int = 0
        self._cmd_args: Optional[List[str]] = None
        self._selected_group: Optional[Newsgroup] = None
        self._selected_article: Optional[Message] = None
        self._post_mode: bool = False
        self._article_buffer: List[str] = []
        self._command: str = ""

    async def handle_client(self) -> None:
        self._terminated = False
        self._empty_token_counter = 0

        if server_config["server_type"] == "read-only":
            self._server.send(
                writer=self._writer,
                send_obj=StatusCodes.STATUS_READYNOPOST
                % (server_config["nntp_hostname"], get_version()),
            )
        else:
            self._server.send(
                writer=self._writer,
                send_obj=StatusCodes.STATUS_READYOKPOST
                % (server_config["nntp_hostname"], get_version()),
            )

        # main execution loop for handling a connection until it's closed
        while not self._terminated:
            try:
                # TODO: make timeout a setting
                incoming_data = await wait_for(self._reader.readline(), timeout=43200.0)
            except TimeoutError as e:
                self.logger.error(f"ERROR: TimeoutError occurred. {e}")
                continue

            self.logger.debug(
                f"{self._writer.get_extra_info(name='peername')} >"
                f" {incoming_data.decode(encoding='utf-8').strip()}"
            )

            if self._post_mode:
                # only rstrip in order to preserve indentation in body
                data_decode = incoming_data.decode(encoding="utf-8").rstrip()
                if data_decode == ".":
                    try:
                        self._server.backend.save_article(article_buffer=self._article_buffer)
                        self._server.send(
                            writer=self._writer, send_obj=StatusCodes.STATUS_POSTSUCCESSFUL
                        )
                    except Exception as e:  # noqa E722
                        self.logger.error(e)
                        self._server.send(
                            writer=self._writer, send_obj=StatusCodes.ERR_NOTPERFORMED
                        )
                    self._post_mode = False
                    self._article_buffer = []
                else:
                    self._article_buffer.append(data_decode)
                continue

            try:
                tokens: List[str] = (
                    incoming_data.decode(encoding="utf-8").strip().lower().split(" ")
                )
            except IOError:
                continue

            if all([t == "" for t in tokens]):
                self._empty_token_counter += 1
                if self._empty_token_counter >= server_config["max_empty_requests"]:
                    self.logger.warning(
                        "WARNING: Noping out because client is sending too many empty requests"
                    )
                    self._terminated = True
                continue
            else:
                self._empty_token_counter = 0

            self._command = tokens.pop(0) if len(tokens) > 0 else None
            self._cmd_args: Optional[List[str]] = tokens

            if self._command in self._server.backend.available_commands:
                try:
                    self._server.send(
                        writer=self._writer,
                        send_obj=await self._server.backend.call_dict[self._command](self),
                    )
                except Exception as e:
                    self.logger.exception(e)
                    self._terminated = True
            else:
                # command is not in list of implemented capabilities
                self._server.send(writer=self._writer, send_obj=StatusCodes.ERR_CMDSYNTAXERROR)

            if self._command == "quit":
                self._terminated = True

    def stop(self):
        self._writer.close()

    @property
    def article_buffer(self):
        return self._article_buffer

    @property
    def cmd_args(self) -> Optional[List[str]]:
        return self._cmd_args

    @property
    def command(self) -> Optional[str]:
        return self._command

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
