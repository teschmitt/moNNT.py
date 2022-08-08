from typing import TYPE_CHECKING

from backend.dtn7sqlite.nntp_commands import logger
from status_codes import StatusCodes

if TYPE_CHECKING:
    from client_connection import ClientConnection


async def do_quit(client_conn: "ClientConnection") -> str:
    """
    Syntax:
        QUIT
    Responses:
        205 closing connection - goodbye!
    """
    if len(client_conn.cmd_args) > 0:
        return StatusCodes.ERR_CMDSYNTAXERROR

    logger.debug("Quitting")
    return StatusCodes.STATUS_CLOSING
