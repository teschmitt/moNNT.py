from typing import List, Union, Awaitable

from tortoise.queryset import QuerySet, QuerySetSingle

from models import Message
from settings import settings
from status_codes import StatusCodes


def get_messages_by_id(_id: int) -> QuerySetSingle[Message]:
    return Message.get_or_none(id=_id)


def get_messages_by_msg_id(message_id: str) -> QuerySetSingle[Message]:
    return Message.get_or_none(message_id=message_id)


async def do_article(tokens: List[str]) -> Union[List[str], str]:
    article_info: list
    response_status: str

    selected_group = tokens.pop(0)

    try:
        selected_article: str = tokens.pop(0)
    except IndexError:
        return StatusCodes.ERR_NOARTICLESELECTED

    if "<" in selected_article and ">" in selected_article:
        msg: Message = await get_messages_by_msg_id(selected_article)
        # TODO: Maybe msg.id must always be 1 … if error then try 1:
    else:
        try:
            _id: int = int(selected_article)
        except ValueError:
            # TODO: an unintelligible value was passed, maybe find a better error
            return StatusCodes.ERR_NOARTICLESELECTED
        msg: Message = await get_messages_by_id(_id)

    try:
        response_status = StatusCodes.STATUS_ARTICLE % (
            msg.id,
            msg.message_id,
        )
    except AttributeError:
        return StatusCodes.ERR_NOSUCHARTICLENUM

    result = [
        response_status,
        f"Path: {settings.DOMAIN_NAME}",
        f"From: {msg.sender}",
        f"Newsgroups: {selected_group}",
        f"Date: {msg.created_at.strftime('%a, %d %b %Y %H:%M:%S %Z')}",
        f"Subject: {msg.subject}",
        f"Message-ID: {msg.message_id}",
        f"Xref: {settings.DOMAIN_NAME} {selected_group}:{msg.id}",
        f"References: ",
        f"",
        f"{msg.body}",
    ]

    return result
