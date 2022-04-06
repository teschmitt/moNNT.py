from typing import List

from tortoise.functions import Count, Max, Min

from models import Message
from settings import settings
from status_codes import StatusCodes


async def do_group(tokens: List[str]) -> str:
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
    if len(tokens) != 1:
        return StatusCodes.ERR_CMDSYNTAXERROR

    group_stats = (
        await Message.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .group_by("newsgroup__id")
        .filter(newsgroup__name=tokens[0])
        .first()
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )
    return StatusCodes.STATUS_GROUPSELECTED % (
        group_stats["count"],
        group_stats["min"],
        group_stats["max"],
        group_stats["name"],
    )
