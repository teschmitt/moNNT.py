from typing import TYPE_CHECKING, Optional, Union

from tortoise.functions import Count, Max, Min
from tortoise.queryset import ValuesQuery

from models import Message, Newsgroup
from status_codes import StatusCodes
from utils import ParsedRange, RangeParseStatus

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


def get_group_stats(group_name: str) -> ValuesQuery:
    return (
        Message.annotate(count=Count("id"), max=Max("id"), min=Min("id"))
        .filter(newsgroup__name=group_name)
        .values(name="newsgroup__name", count="count", min="min", max="max")
    )


async def do_listgroup(server_state: "AsyncTCPServer") -> Union[list[str], str]:
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

    tokens: list[str] = server_state.cmd_args
    group_name: Optional[str] = tokens[0] if len(tokens) > 0 else None
    num_range: Optional[str] = tokens[1] if len(tokens) > 1 else None
    result: list[str]
    msgs: list[Message]

    if group_name is not None:
        # group name provided, so select the group
        new_group: Newsgroup = await Newsgroup.get_or_none(name=group_name)
        if new_group is None:
            return StatusCodes.ERR_NOSUCHGROUP
        server_state.selected_group = new_group

    if server_state.selected_group is None:
        return StatusCodes.ERR_NOGROUPSELECTED

    if num_range is None:
        msgs = await Message.filter(newsgroup__name=server_state.selected_group.name)
    else:
        parsed_range: ParsedRange = ParsedRange(range_str=num_range, max_value=2**63)
        if parsed_range.parse_status == RangeParseStatus.FAILURE:
            return StatusCodes.ERR_NOTPERFORMED
        msgs = await Message.filter(
            newsgroup__name=server_state.selected_group.name,
            id__gte=parsed_range.start,
            id__lte=parsed_range.stop,
        )

    ids: list[int] = [msg.id for msg in msgs]
    result = [
        StatusCodes.STATUS_LISTGROUP.substitute(
            number=len(msgs), low=min(ids), high=max(ids), group=server_state.selected_group.name
        )
    ]
    result.extend(map(str, ids))

    return result
