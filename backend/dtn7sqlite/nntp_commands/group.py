from typing import TYPE_CHECKING, List, Optional

from tortoise.functions import Count, Max, Min

from models import Article, Newsgroup
from status_codes import StatusCodes

if TYPE_CHECKING:
    from client_connection import ClientConnection


async def do_group(client_conn: "ClientConnection") -> str:
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

    tokens: List[str] = client_conn.cmd_args

    if len(tokens) != 1:
        return StatusCodes.ERR_CMDSYNTAXERROR

    new_group: Optional[Newsgroup] = await Newsgroup.get_or_none(name=tokens[0])
    if new_group is None:
        return StatusCodes.ERR_NOSUCHGROUP
    client_conn.selected_group = new_group
    # if the selected group is empty, filter.first() will return None so this is RFC-compliant:
    client_conn.selected_article = (
        await Article.filter(newsgroup=client_conn.selected_group).order_by("id").first()
    )
    group_stats: Optional[dict] = (
        await Article.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .group_by("newsgroup__id")
        .filter(newsgroup=client_conn.selected_group)
        .first()
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )

    if group_stats is None:
        # RFC 3977 Sec. 6.1.1.2.
        return StatusCodes.STATUS_GROUPSELECTED.substitute(
            count=0,
            first=0,
            last=0,
            name=client_conn.selected_group.name,
        )

    return StatusCodes.STATUS_GROUPSELECTED.substitute(
        count=group_stats["count"],
        first=group_stats["min"],
        last=group_stats["max"],
        name=group_stats["name"],
    )
