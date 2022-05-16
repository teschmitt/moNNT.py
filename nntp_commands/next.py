from typing import TYPE_CHECKING

from models import Message, Newsgroup
from status_codes import StatusCodes

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


async def do_next(server_state: "AsyncTCPServer") -> str:
    """
    6.1.4.1.  Usage

        Indicating capability: READER

        Syntax
            NEXT

        Responses
            223 n message-id    Article found
            412                 No newsgroup selected
            420                 Current article number is invalid
            421                 No next article in this group

        Parameters
            n             Article number
            message-id    Article message-id
    """

    selected_group: Newsgroup = server_state.selected_group
    selected_article: Message = server_state.selected_article
    if selected_group is None:
        return StatusCodes.ERR_NOGROUPSELECTED
    if selected_article is None:
        return StatusCodes.ERR_NOARTICLESELECTED

    msg: Message = (
        await Message.filter(newsgroup__name=selected_group.name, id__gt=selected_article.id)
        .order_by("id")
        .first()
    )

    if msg is None:
        return StatusCodes.ERR_NONEXTARTICLE

    server_state.selected_article = msg

    return StatusCodes.STATUS_STAT.substitute(number=msg.id, msg_id=f"<{msg.message_id}>")
