from typing import TYPE_CHECKING, List, Optional, Union

from tortoise.functions import Count, Max, Min
from tortoise.queryset import ValuesQuery

from backend.dtn7sqlite.models import Article, Newsgroup
from status_codes import StatusCodes
from utils import ParsedRange, RangeParseStatus

if TYPE_CHECKING:
    from client_connection import ClientConnection


def get_group_stats(group_name: str) -> ValuesQuery:
    return (
        Article.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .filter(newsgroup__name=group_name)
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )


async def do_listgroup(client_conn: "ClientConnection") -> Union[List[str], str]:
    """
    6.1.2.1.  Usage

        Indicating capability: READER

        Syntax
            LISTGROUP [group [range]]

        Responses
            211 number low high group     Article numbers follow (multi-line)
            411                           No such newsgroup
            412                           No newsgroup selected [1]

        Parameters
            group     Name of newsgroup
            range     Range of articles to report
            number    Estimated number of articles in the group
            low       Reported low water mark
            high      Reported high water mark

        [1] The 412 response can only occur if no group has been specified.

    """

    tokens: List[str] = client_conn.cmd_args
    group_name: Optional[str] = tokens[0] if len(tokens) > 0 else None
    num_range: Optional[str] = tokens[1] if len(tokens) > 1 else None
    result: List[str]
    msgs: List[Article]
    status_str: str

    if group_name is not None:
        # group name provided, so select the group
        new_group: Newsgroup = await Newsgroup.get_or_none(name=group_name)
        if new_group is None:
            return StatusCodes.ERR_NOSUCHGROUP
        client_conn.selected_group = new_group

    if client_conn.selected_group is None:
        return StatusCodes.ERR_NOGROUPSELECTED

    if num_range is None:
        # msgs = await Message.filter(newsgroup__name=client_conn.selected_group.name)
        msgs = await Article.filter(newsgroup=client_conn.selected_group)
    else:
        parsed_range: ParsedRange = ParsedRange(range_str=num_range, max_value=2**63)
        if parsed_range.parse_status == RangeParseStatus.FAILURE:
            return StatusCodes.ERR_NOTPERFORMED
        msgs = await Article.filter(
            newsgroup__name=client_conn.selected_group.name,
            id__gte=parsed_range.start,
            id__lte=parsed_range.stop,
        )

    ids: List[int] = [msg.id for msg in msgs]
    if len(ids) > 0:
        status_str = StatusCodes.STATUS_LISTGROUP.substitute(
            number=len(msgs), low=min(ids), high=max(ids), group=client_conn.selected_group.name
        )
        result = [status_str] + list(map(str, ids))
    else:
        status_str = StatusCodes.STATUS_LISTGROUP.substitute(
            number=len(msgs), low=0, high=0, group=client_conn.selected_group.name
        )
        result = [status_str]

    return result
