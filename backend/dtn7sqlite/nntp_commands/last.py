from typing import TYPE_CHECKING

from backend.dtn7sqlite.models import Article, Newsgroup
from status_codes import StatusCodes

if TYPE_CHECKING:
    from client_connection import ClientConnection


async def do_last(client_conn: "ClientConnection") -> str:
    """
    6.1.3.1.  Usage

        Indicating capability: READER

        Syntax
            LAST

        Responses
            223 n message-id    Article found
            412                 No newsgroup selected
            420                 Current article number is invalid
            422                 No previous article in this group

        Parameters
            n             Article number
            message-id    Article message-id
    """

    selected_group: Newsgroup = client_conn.selected_group
    selected_article: Article = client_conn.selected_article
    if selected_group is None:
        return StatusCodes.ERR_NOGROUPSELECTED
    if selected_article is None:
        return StatusCodes.ERR_NOARTICLESELECTED

    msg: Article = (
        await Article.filter(newsgroup__name=selected_group.name, id__lt=selected_article.id)
        .order_by("-id")
        .first()
    )

    if msg is None:
        return StatusCodes.ERR_NOPREVIOUSARTICLE

    client_conn.selected_article = msg

    return StatusCodes.STATUS_NEXTLAST.substitute(number=msg.id, message_id=msg.message_id)
