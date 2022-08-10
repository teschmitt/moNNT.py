from typing import TYPE_CHECKING, List

from backend.dtn7sqlite.nntp_commands import logger
from config import server_config
from status_codes import StatusCodes

if TYPE_CHECKING:
    from client_connection import ClientConnection


async def do_mode(client_conn: "ClientConnection") -> str:
    """
    Syntax:
        MODE READER|STREAM
    Responses:
        200 Hello, you can post
        201 Hello, you can't post
        203 Streaming is OK
        500 Command not understood
    """
    tokens: List[str] = client_conn.cmd_args
    logger.debug(f"in do_mode with {tokens}")
    if tokens[0] == "reader":
        if server_config["server_type"] == "read-only":
            return StatusCodes.STATUS_NOPOSTMODE
        else:
            return StatusCodes.STATUS_POSTALLOWED
    elif tokens[0] == "stream":
        return StatusCodes.ERR_NOSTREAM
