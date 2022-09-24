from typing import TYPE_CHECKING, List, Union

from tortoise.queryset import QuerySet

from models import Article
from status_codes import StatusCodes
from utils import get_bytes_len, get_num_lines

if TYPE_CHECKING:
    from client_connection import ClientConnection


def get_current_messages(limit: int) -> QuerySet[Article]:
    return Article.all().order_by("created_at").limit(limit)


async def do_current(client_conn: "ClientConnection") -> Union[List[str], str]:
    """
    this is a non-standard command only for the moboard web frontend
    """

    options: List[str] = client_conn.cmd_args
    article_list: List[Article] = []
    lim: int = 10

    if options is not None and len(options) > 0 or options is None:
        lim = int(options[0])

    try:
        article_list = await get_current_messages(limit=lim)
    except Exception as e:
        print(e)

    headers: List[str] = []
    for msg in article_list:
        references: str = msg.references if msg.references is not None else ""
        group_name: str = (await msg.newsgroup).name
        headers.append(
            "\t".join(
                [
                    str(msg.id),
                    msg.subject,
                    msg.from_,
                    msg.created_at.strftime("%a, %d %b %Y %H:%M:%S %Z"),
                    msg.message_id,
                    group_name,
                    references,
                    str(get_bytes_len(msg)),
                    str(get_num_lines(msg)),
                ]
            )
        )
    return [StatusCodes.STATUS_XOVER] + headers
