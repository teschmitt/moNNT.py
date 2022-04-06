from typing import List, Optional, Union

from tortoise.functions import Count, Max, Min

from logger import global_logger
from models import Newsgroup, Message
from settings import settings
from status_codes import StatusCodes

logger = global_logger(__name__)

overview_headers = (
    "Subject:",
    "From:",
    "Date:",
    "Message-ID:",
    "References:",
    "Bytes:",
    "Lines:",
    "Xref:full",
)

extensions = (
    "XOVER",
    "XPAT",
    "LISTGROUP",
    "XGTITLE",
    "XHDR",
    "MODE",
    "OVER",
    "HDR",
    "AUTHINFO",
    "XROVER",
    "XVERSION",
)


async def do_list(tokens: List[str]) -> Union[List[str], str]:
    """
    Syntax:
        LIST (done)
        LIST ACTIVE [wildmat]
        LIST ACTIVE.TIMES
        LIST DISTRIBUTIONS
        LIST DISTRIB.PATS
        LIST NEWSGROUPS [wildmat]
        LIST OVERVIEW.FMT (done)
        LIST SUBSCRIPTIONS
        LIST EXTENSIONS (not documented) (done by comparing the results of other servers)
    Responses:
        215 list of newsgroups follows
        503 program error, function not performed
    """
    result_stats: List[str] = []

    if len(tokens) > 2:
        # invalid command, return an error-code
        return StatusCodes.ERR_CMDSYNTAXERROR

    if len(tokens) == 0:
        group_stats = (
            await Message.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
            .group_by("newsgroup__id")
            .order_by("newsgroup__name")
            .values(name="newsgroup__name", count="count", min="min", max="max")
        )
        post_allowed = "y" if settings.SERVER_TYPE == "read-write" else "n"
        result_stats = [StatusCodes.STATUS_LIST]
        result_stats.extend(
            [f"{g['name']} {g['max']} {g['min']} {post_allowed}" for g in group_stats]
            # [f"{g['name']} {g['count']} 1 {post_allowed}" for g in group_stats]
        )
    else:
        option = tokens[0]
        if option == "overview.fmt":
            result_stats = [StatusCodes.STATUS_OVERVIEWFMT]
            result_stats.extend(overview_headers)
        elif option == "extensions":
            result_stats = [StatusCodes.STATUS_EXTENSIONS]
            result_stats.extend(extensions)
        elif option == "active":
            pass
        elif option in ["newsgroups", "subscriptions"]:
            result_stats = [StatusCodes.STATUS_LISTNEWSGROUPS]
            query = Newsgroup.all().order_by("name")
            if len(tokens) == 2:
                pattern = tokens[1]
                pattern.replace("*", ".*").replace("?", ".*")
                query = query.filter(name__search=pattern)
            groups = await query.values("name", "description")
            result_stats.extend([f"{g['name']} {g['description']}" for g in groups])
        else:
            return StatusCodes.ERR_NOTPERFORMED

    return result_stats
