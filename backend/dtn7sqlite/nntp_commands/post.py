from typing import TYPE_CHECKING

from backend.dtn7sqlite.nntp_commands import logger
from config import server_config
from status_codes import StatusCodes

if TYPE_CHECKING:
    from client_connection import ClientConnection


async def do_post(client_conn: "ClientConnection") -> str:
    """
    6.3.1.1.  Usage

    Indicating capability: POST

    This command MUST NOT be pipelined.

    Syntax
        POST

    Responses

    Initial responses
        340    Send article to be posted
        440    Posting not permitted

    Subsequent responses
        240    Article received OK
        441    Posting failed
    """

    if server_config["server_type"] != "read-write":
        return StatusCodes.STATUS_READONLYSERVER

    logger.debug("switching to post mode")
    client_conn.post_mode = True
    return StatusCodes.STATUS_SENDARTICLE
