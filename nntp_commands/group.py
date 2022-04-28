from typing import TYPE_CHECKING, Optional

from tortoise.functions import Count, Max, Min

from models import Message, Newsgroup
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

    server_state.selected_group = await Newsgroup.get_or_none(name=tokens[0])
    if server_state.selected_group is None:
        return StatusCodes.ERR_NOSUCHGROUP
    group_stats: Optional[dict] = (
        await Message.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .group_by("newsgroup__id")
        .filter(newsgroup=server_state.selected_group)
        .first()
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )

    if group_stats is None:
        # RFC 3977 Sec. 6.1.1.2.
        return StatusCodes.STATUS_GROUPSELECTED.substitute(
            count=0,
            first=0,
            last=0,
            name=server_state.selected_group.name,
        )

    return StatusCodes.STATUS_GROUPSELECTED.substitute(
        count=group_stats["count"],
        first=group_stats["min"],
        last=group_stats["max"],
        name=group_stats["name"],
    )
