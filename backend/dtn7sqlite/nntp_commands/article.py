from typing import TYPE_CHECKING, List, Optional, Union

from tortoise.queryset import QuerySetSingle

from config import server_config
from models import Message, Newsgroup
from status_codes import StatusCodes
from utils import build_xref

if TYPE_CHECKING:
    from client_connection import ClientConnection


def get_messages_by_num(num: int, group: Newsgroup) -> QuerySetSingle[Message]:
    return Message.get_or_none(id=num, newsgroup=group)


def get_messages_by_msg_id(message_id: str) -> QuerySetSingle[Message]:
    return Message.get_or_none(message_id=message_id)


async def do_article(client_conn: "ClientConnection") -> Union[List[str], str]:
    """
    6.2.1.1.  Usage

        Indicating capability: READER

        Syntax
            ARTICLE message-id
            ARTICLE number
            ARTICLE

        Responses

        First form (message-id specified)
            220 0|n message-id    Article follows (multi-line)
            430                   No article with that message-id

        Second form (article number specified)
            220 n message-id      Article follows (multi-line)
            412                   No newsgroup selected
            423                   No article with that number

        Third form (current article number used)
            220 n message-id      Article follows (multi-line)
            412                   No newsgroup selected
            420                   Current article number is invalid

        Parameters
            number        Requested article number
            n             Returned article number
            message-id    Article message-id
    """
    article_info: list
    response_status: str

    identifier: Optional[str] = client_conn.cmd_args[0] if len(client_conn.cmd_args) > 0 else None
    selected_group: Optional[Newsgroup] = client_conn.selected_group

    # figure out how the article is supposed to be identified
    id_provided: bool = identifier is not None and "<" in identifier and ">" in identifier
    nr_provided: bool = not id_provided and identifier is not None

    if id_provided:
        # RFC 3977 Sec. 6.2.1.1. First form
        identifier = identifier.replace("<", "").replace(">", "")
        msg: Message = await get_messages_by_msg_id(identifier)
    elif nr_provided:
        # second form
        if selected_group is None:
            # when a msg nr is provided, a group must be selected
            return StatusCodes.ERR_NOGROUPSELECTED
        try:
            num: int = int(identifier)
        except ValueError:
            return StatusCodes.ERR_NOARTICLESELECTED
        msg: Message = await get_messages_by_num(num, selected_group)
    else:
        # third form
        msg: Message = client_conn.selected_article

    if msg is None:
        return StatusCodes.ERR_NOSUCHARTICLE

    client_conn.selected_article = msg

    try:
        response_status = StatusCodes.STATUS_ARTICLE % (
            msg.id,
            msg.message_id,
        )
    except AttributeError:
        return StatusCodes.ERR_NOSUCHARTICLENUM

    result = [
        response_status,
        f"Path: {server_config['domain_name']}",
        f"From: {msg.from_}",
        f"Newsgroups: {selected_group.name}",
        f"Date: {msg.created_at.strftime('%a, %d %b %Y %H:%M:%S %Z')}",
        f"Subject: {msg.subject}",
        f"Message-ID: {msg.message_id}",
        f"Xref: {build_xref(article_id=msg.id, group_name=selected_group.name)}",
        f"References: {msg.references}",
        f"Path: {msg.path}",
        f"Organization: {msg.organization}",
        f"User-Agent: {msg.user_agent}",
        "",
        f"{msg.body}",
    ]

    return result
