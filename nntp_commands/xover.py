from typing import TYPE_CHECKING, List, Union

from tortoise.queryset import QuerySet

from models import Message
from settings import settings
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


def get_messages(group: str, start: int, stop: int) -> QuerySet[Message]:
    return Message.filter(newsgroup__name=group, id__gte=start, id__lte=stop)


async def do_xover(server_state: "AsyncTCPServer") -> Union[List[str], str]:
    tokens: list[str] = server_state.cmd_args
    selected_group: str = server_state.selected_group

    if selected_group is None:
        return StatusCodes.ERR_NOGROUPSELECTED

    if len(tokens) == 0:
        return StatusCodes.ERR_NOTPERFORMED

    msg_range: List[str] = tokens[0].split("-")
    start: int = 0
    stop: int = 2**63  # max bigint

    if len(msg_range) == 1:
        start = stop = int(msg_range[0])
    elif len(msg_range) == 2:
        start = int(msg_range[0])
        stop_str: str = msg_range[1]
        if stop_str != "ggg":
            # Todo: this is not entirely correct. Find out the exact different forms
            #       the parameters for XOVER and OVER can have
            stop = int(stop_str)

    headers = []
    msgs_queryset: QuerySet[Message] = get_messages(selected_group, start, stop)
    for msg in await msgs_queryset:
        body = msg.body
        num_lines = len(body.split("\n"))
        xref = "Xref: %s %s:%s" % (settings.DOMAIN_NAME, selected_group, msg.id)

        headers.append(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                msg.id,
                msg.subject,
                msg.sender,
                msg.created_at.strftime("%a, %d %b %Y %H:%M:%S %Z"),
                msg.message_id,
                "",
                len(body),
                num_lines,
                xref,
            )
        )
    result = "%s\r\n%s\r\n." % (StatusCodes.STATUS_XOVER, "\r\n".join(headers))
    # result = [StatusCodes.STATUS_XOVER]
    # result.extend(headers)
    return result
