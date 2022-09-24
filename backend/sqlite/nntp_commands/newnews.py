from typing import TYPE_CHECKING, List, Union

from models import Article, Newsgroup
from status_codes import StatusCodes
from utils import get_datetime, groupname_filter

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


async def do_newnews(server_state: "AsyncNNTPServer") -> Union[List[str], str]:
    """
    7.4.1.  Usage

        Indicating capability: NEWNEWS

        Syntax
            NEWNEWS wildmat date time [GMT]

        Responses
            230    List of new articles follows (multi-line)

        Parameters
            wildmat    Newsgroups of interest
            date       Date in yymmdd or yyyymmdd format
            time       Time in hhmmss format
    """
    tokens: List[str] = server_state.cmd_args
    if len(tokens) > 4 or (len(tokens) == 4 and tokens[3] != "gmt"):
        # invalid command, return an error-code
        return StatusCodes.ERR_CMDSYNTAXERROR
    try:
        wildmat: str = tokens[0]
        gte_date = get_datetime(date_str=tokens[1], time_str=tokens[2])
    except (IndexError, ValueError):
        return StatusCodes.ERR_CMDSYNTAXERROR

    matching_groups = groupname_filter(
        groups=(await Newsgroup.all().values("id", "name")), pattern=wildmat
    )
    group_ids: List[int] = [g["id"] for g in matching_groups]
    articles: List[dict] = await Article.filter(
        created_at__gte=gte_date, newsgroup__id__in=group_ids
    ).values("message_id")

    result_stats = [StatusCodes.STATUS_NEWNEWS] + [art["message_id"] for art in articles]

    return result_stats
