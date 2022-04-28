from nntp_commands import logger
from settings import settings
from status_codes import StatusCodes


async def do_mode(server_state) -> str:
    """
    Syntax:
        MODE READER|STREAM
    Responses:
        200 Hello, you can post
        201 Hello, you can't post
        203 Streaming is OK
        500 Command not understood
    """
    tokens: list[str] = server_state.cmd_args
    logger.debug(f"in do_mode with {tokens}")
    if tokens[0] == "reader":
        if settings.SERVER_TYPE == "read-only":
            return StatusCodes.STATUS_NOPOSTMODE
        else:
            return StatusCodes.STATUS_POSTMODE
    elif tokens[0] == "stream":
        return StatusCodes.ERR_NOSTREAM
