from typing import TYPE_CHECKING, Union

from backend.dtn7sqlite.nntp_commands.article import do_article
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


async def do_head_body_stat(server_state: "AsyncTCPServer") -> Union[list[str], str]:
    """
    6.2.2/3.2.  Description

        The HEAD/BODY command behaves identically to the ARTICLE command except
        that, if the article exists, the response code is 221/222 instead of 220
        and only the headers are presented (the empty line separating the
        headers and body MUST NOT be included).

    [...]

    6.2.4.2.  Description

        The STAT command behaves identically to the ARTICLE command except
        that, if the article exists, it is NOT presented to the client and
        the response code is 223 instead of 220.  Note that the response is
        NOT multi-line.
    """

    res = await do_article(server_state)

    # pipe through any errors:
    status, num, msg_id, _ = res[0].split(" ", 3)
    if status[0] != "2":
        return res

    last_header_line: int = 0
    while res[last_header_line] != "":
        last_header_line += 1
    if server_state.command == "head":
        res[0] = StatusCodes.STATUS_HEAD.substitute(number=num, message_id=msg_id)
        res = res[:last_header_line]
    if server_state.command == "stat":
        res = StatusCodes.STATUS_STAT.substitute(number=num, message_id=msg_id)
    else:
        last_header_line += 1
        res = res[last_header_line:]
        res = [StatusCodes.STATUS_BODY.substitute(number=num, message_id=msg_id)] + res
    return res
