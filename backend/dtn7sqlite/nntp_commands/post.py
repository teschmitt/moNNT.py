from typing import TYPE_CHECKING

from backend.dtn7sqlite.nntp_commands import logger
from settings import settings
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


async def do_post(server_state: "AsyncNNTPServer") -> str:
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

    if settings.SERVER_TYPE != "read-write":
        return StatusCodes.STATUS_READONLYSERVER

    logger.debug("switching to post mode")
    server_state.post_mode = True
    return StatusCodes.STATUS_SENDARTICLE
