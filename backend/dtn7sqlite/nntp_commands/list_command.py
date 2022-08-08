from typing import TYPE_CHECKING, List, Optional, Union

from tortoise.functions import Max, Min

from logger import global_logger
from models import Newsgroup
from status_codes import StatusCodes
from utils import groupname_filter

if TYPE_CHECKING:
    from client_connection import ClientConnection

logger = global_logger()

overview_headers = (
    "Subject:",
    "From:",
    "Date:",
    "Message-ID:",
    "References:",
    ":bytes",
    ":lines",
    "Xref:full",
)

list_headers = (
    "Subject",
    "From",
    "Date",
    "Message-ID",
    "References",
    ":bytes",
    ":lines",
    "Xref",
    "Newsgroups",
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


async def do_list(client_conn: "ClientConnection") -> Union[List[str], str]:
    """
    7.6.1.1.  Usage

        Indicating capability: LIST

        Syntax
            LIST [keyword [wildmat|argument]]

        Responses
            215    Information follows (multi-line)

        Parameters
            keyword     Information requested [1]
            argument    Specific to keyword
            wildmat     Groups of interest

        [1] If no keyword is provided, it defaults to ACTIVE.

    7.6.2.  Standard LIST Keywords

        +--------------+---------------+------------------------------------+
        | Keyword      | Definition    | Status                             |
        +--------------+---------------+------------------------------------+
        | ACTIVE       | Section 7.6.3 | Mandatory if the READER capability |
        |              |               | is advertised                      |
        | ACTIVE.TIMES | Section 7.6.4 | Optional                           |
        | DISTRIB.PATS | Section 7.6.5 | Optional                           |
        | HEADERS      | Section 8.6   | Mandatory if the HDR capability is |
        |              |               | advertised                         |
        | NEWSGROUPS   | Section 7.6.6 | Mandatory if the READER capability |
        |              |               | is advertised                      |
        | OVERVIEW.FMT | Section 8.4   | Mandatory if the OVER capability   |
        |              |               | is advertised                      |
        +--------------+---------------+------------------------------------+
    """
    tokens: List[str] = client_conn.cmd_args
    result_stats: List[str] = []
    option: Optional[str] = tokens[0] if len(tokens) > 0 else None

    if len(tokens) > 2:
        # invalid command, return an error-code
        return StatusCodes.ERR_CMDSYNTAXERROR

    if option is None or option == "active" or len(option) == 0:
        group_stats = (
            await Newsgroup.annotate(high=Max("messages__id"), low=Min("messages__id"))
            .order_by("name")
            .values("high", "low", "name", "status")
        )
        if len(tokens) == 2:
            # a wildmat was passed and there is no sane way to query a modern
            # DB against this sort of pattern since it was created more or less
            # only for NNTP *sheesh*
            pattern: str = tokens[1]
            group_stats = groupname_filter(group_stats, pattern)

        result_stats = [StatusCodes.STATUS_LIST]
        result_stats.extend(
            [
                f"{g['name']} {g['high'] if g['high'] is not None else '0'} "
                f"{g['low'] if g['low'] is not None else '0'} {g['status']}"
                for g in group_stats
            ]
        )
    else:
        if option == "overview.fmt":
            result_stats = [StatusCodes.STATUS_OVERVIEWFMT]
            result_stats.extend(overview_headers)
        elif option == "headers":
            result_stats = [StatusCodes.STATUS_OVERVIEWFMT]
            result_stats.extend(list_headers)
        elif option == "extensions":
            result_stats = [StatusCodes.STATUS_EXTENSIONS]
            result_stats.extend(extensions)
        elif option == "subscriptions":
            # TODO: implement default subscriptions
            pass
        elif option == "newsgroups":
            result_stats = [StatusCodes.STATUS_LISTNEWSGROUPS]
            groups: Union[filter, List[dict]] = (
                await Newsgroup.all().order_by("name").values("name", "description")
            )
            if len(tokens) == 2:
                # a wildmat was passed and there is no sane way to query a modern
                # DB against this sort of pattern since it was created more or less
                # only for NNTP *sheesh*
                pattern: str = tokens[1]
                groups = groupname_filter(groups, pattern)
            result_stats.extend([f"{g['name']} {g['description']}" for g in groups])
        else:
            # if option in ["distributions", "active.times", "distrib.pats"]
            return StatusCodes.ERR_NOTPERFORMED

    return result_stats
