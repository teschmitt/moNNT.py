from typing import TYPE_CHECKING, Optional

from tortoise.functions import Count, Max, Min

from models import Message
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


async def do_group(server_state: "AsyncTCPServer") -> str:
    """
    Syntax:
        GROUP ggg
    Responses:
        211 n f l s group selected
           (n = estimated number of articles in group,
            f = first article number in the group,
            l = last article number in the group,
            s = name of the group.)
        411 no such news group
    """

    tokens: list[str] = server_state.cmd_args

    if len(tokens) != 1:
        return StatusCodes.ERR_CMDSYNTAXERROR

    server_state.selected_group = tokens[0]

    group_stats: Optional[dict] = (
        await Message.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .group_by("newsgroup__id")
        .filter(newsgroup__name=tokens[0])
        .first()
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )

    if group_stats is None:
        return StatusCodes.ERR_NOSUCHGROUP

    return StatusCodes.STATUS_GROUPSELECTED.substitute(
        count=group_stats["count"],
        first=group_stats["min"],
        last=group_stats["max"],
        name=group_stats["name"],
    )
