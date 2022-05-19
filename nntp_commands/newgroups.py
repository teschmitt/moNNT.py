from typing import TYPE_CHECKING, Union

from tortoise.functions import Max, Min

from models import Newsgroup
from status_codes import StatusCodes
from utils import get_datetime

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


async def do_newgroups(server_state: "AsyncTCPServer") -> Union[list[str], str]:
    """
    7.3.1.  Usage

        Indicating capability: READER

        Syntax
            NEWGROUPS date time [GMT]

        Responses
            231    List of new newsgroups follows (multi-line)

        Parameters
            date    Date in yymmdd or yyyymmdd format
            time    Time in hhmmss format
    """
    tokens: list[str] = server_state.cmd_args
    if len(tokens) > 3 or tokens[2] != "GMT":
        # invalid command, return an error-code
        return StatusCodes.ERR_CMDSYNTAXERROR
    try:
        gte_date = get_datetime(tokens)
    except (IndexError, ValueError):
        return StatusCodes.ERR_CMDSYNTAXERROR
    # tz_: Optional[str] = tokens[2] if len(tokens) == 3 else None

    group_stats = (
        await Newsgroup.filter(created_at__gte=gte_date)
        .annotate(high=Max("messages__id"), low=Min("messages__id"))
        .order_by("name")
        .values("high", "low", "name", "status")
    )

    result_stats = [StatusCodes.STATUS_NEWGROUPS]
    result_stats.extend(
        [
            f"{g['name']} {g['high'] if g['high'] is not None else '0'} "
            f"{g['low'] if g['low'] is not None else '0'} {g['status']}"
            for g in group_stats
        ]
    )

    return result_stats
