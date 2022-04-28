from fnmatch import fnmatch
from typing import TYPE_CHECKING, Optional, Union

from tortoise.functions import Count, Max, Min
from tortoise.queryset import ValuesQuery

from logger import global_logger
from models import Message, Newsgroup
from settings import settings
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer

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


def get_group_stats() -> ValuesQuery:
    return (
        Message.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .group_by("newsgroup__id")
        .order_by("newsgroup__name")
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )


def groupname_filter(groups: list[dict], pattern: str) -> filter:
    return filter(lambda v: fnmatch(v["name"], pattern), groups)


async def do_list(server_state: "AsyncTCPServer") -> Union[list[str], str]:
    """
    Syntax:
        LIST
        LIST ACTIVE [wildmat]
        LIST ACTIVE.TIMES
        LIST DISTRIBUTIONS
        LIST DISTRIB.PATS
        LIST NEWSGROUPS [wildmat]
        LIST OVERVIEW.FMT
        LIST SUBSCRIPTIONS
        LIST EXTENSIONS (not documented) (done by comparing the results of other servers)
    Responses:
        215 list of newsgroups follows
        503 program error, function not performed
    """
    tokens: list[str] = server_state.cmd_args
    result_stats: list[str] = []
    option: Optional[str] = tokens[0] if len(tokens) > 0 else None

    if len(tokens) > 2:
        # invalid command, return an error-code
        return StatusCodes.ERR_CMDSYNTAXERROR

    if option is None or option == "active":
        group_stats = get_group_stats()
        if len(tokens) == 2:
            # a wildmat was passed and there is no sane way to query a modern
            # DB against this sort of pattern since it was created more or less
            # only for NNTP *sheesh*
            pattern: str = tokens[1]
            group_stats = groupname_filter(await group_stats, pattern)

        post_allowed = "y" if settings.SERVER_TYPE == "read-write" else "n"
        result_stats = [StatusCodes.STATUS_LIST]
        result_stats.extend(
            [f"{g['name']} {g['max']} {g['min']} {post_allowed}" for g in group_stats]
        )
    else:
        if option == "active":
            group_stats = get_group_stats()
        elif option == "overview.fmt":
            result_stats = [StatusCodes.STATUS_OVERVIEWFMT]
            result_stats.extend(overview_headers)
        elif option == "extensions":
            result_stats = [StatusCodes.STATUS_EXTENSIONS]
            result_stats.extend(extensions)
        elif option == "subscriptions":
            # TODO: implement default subscriptions
            pass
        elif option == "newsgroups":
            result_stats = [StatusCodes.STATUS_LISTNEWSGROUPS]
            groups: Union[filter, list[dict]] = (
                await Newsgroup.all().order_by("name").values("name", "description")
            )
            if len(tokens) == 2:
                # a wildmat was passed and there is no sane way to query a modern
                # DB against this sort of pattern since it was created more or less
                # only for NNTP *sheesh*
                pattern: str = tokens[1]
                # pattern.replace("*", ".*").replace("?", ".*")
                # query = query.filter(name__search=pattern)
                groups = groupname_filter(groups, pattern)
            result_stats.extend([f"{g['name']} {g['description']}" for g in groups])
        else:
            # if option in ["distributions", "active.times", "distrib.pats"]
            return StatusCodes.ERR_NOTPERFORMED

    return result_stats
