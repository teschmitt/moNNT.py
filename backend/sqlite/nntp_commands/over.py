from typing import TYPE_CHECKING, List, Optional, Union

from tortoise.queryset import QuerySet

from models import Message, Newsgroup
from status_codes import StatusCodes
from utils import (
    ParsedRange,
    RangeParseStatus,
    build_xref,
    get_bytes_len,
    get_num_lines,
)

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


def get_messages(group: Newsgroup, start: int, stop: int) -> QuerySet[Message]:
    return Message.filter(newsgroup__name=group.name, id__gte=start, id__lte=stop).order_by(
        "created_at"
    )


async def do_over(server_state: "AsyncTCPServer") -> Union[List[str], str]:
    """
    8.3.1.  Usage

        Indicating capability: OVER

        Syntax
            OVER message-id
            OVER range
            OVER

        Responses

        First form (message-id specified)
            224    Overview information follows (multi-line)
            430    No article with that message-id

        Second form (range specified)
            224    Overview information follows (multi-line)
            412    No newsgroup selected
            423    No articles in that range

        Third form (current article number used)
            224    Overview information follows (multi-line)
            412    No newsgroup selected
            420    Current article number is invalid

        Parameters
            range         Number(s) of articles
            message-id    Message-id of article
    """
    selected_group: Optional[Newsgroup] = server_state.selected_group
    selected_article = server_state.selected_article
    options: List[str] = server_state.cmd_args
    article_list: List[Message] = []

    if len(options) == 0 or options is None:
        if selected_group is None:
            return StatusCodes.ERR_NOGROUPSELECTED
        if selected_article is None:
            return StatusCodes.ERR_NOARTICLESELECTED
        article_list = [selected_article]
    elif len(options) == 1:
        arg: str = options[0]

        if "<" in arg and ">" in arg:
            article_list = [await Message.get_or_none(message_id=arg)]
            if len(article_list) == 0:
                return StatusCodes.ERR_NOSUCHARTICLE
        else:
            if server_state.selected_group is None:
                return StatusCodes.ERR_NOGROUPSELECTED

            parsed_range: ParsedRange = ParsedRange(range_str=arg, max_value=2**63)
            if parsed_range.parse_status == RangeParseStatus.FAILURE:
                return StatusCodes.ERR_NOTPERFORMED

            try:
                article_list = await get_messages(
                    selected_group, parsed_range.start, parsed_range.stop
                )
            except Exception as e:
                print(e)
            if len(article_list) == 0:
                return StatusCodes.ERR_NOSUCHARTICLENUM

    headers: List[str] = []
    for msg in article_list:
        references: str = msg.references if msg.references is not None else ""
        headers.append(
            "\t".join(
                [
                    str(msg.id),
                    msg.subject,
                    msg.from_,
                    msg.created_at.strftime("%a, %d %b %Y %H:%M:%S %Z"),
                    msg.message_id,
                    references,
                    str(get_bytes_len(msg)),
                    str(get_num_lines(msg)),
                    f"Xref: {build_xref(article_id=msg.id, group_name=selected_group.name)}",
                ]
            )
        )
    return [StatusCodes.STATUS_XOVER] + headers
