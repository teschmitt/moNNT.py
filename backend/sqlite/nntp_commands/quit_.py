from typing import TYPE_CHECKING

from backend.sqlite.nntp_commands import logger
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


async def do_quit(server_state: "AsyncNNTPServer") -> str:
    """
    Syntax:
        QUIT
    Responses:
        205 closing connection - goodbye!
    """
    if len(server_state.cmd_args) > 0:
        return StatusCodes.ERR_CMDSYNTAXERROR

    logger.debug("Quitting")
    return StatusCodes.STATUS_CLOSING
