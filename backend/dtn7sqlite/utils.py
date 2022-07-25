from hashlib import sha256
from typing import List

from models import DTNMessage, Newsgroup


async def get_all_newsgroups() -> List[str]:
    return [ng["name"] for ng in await Newsgroup.all().values("name")]


async def get_all_spooled_messages() -> List[dict]:
    return await DTNMessage.all().values(
        "source", "destination", "data", "hash", "delivery_notification", "lifetime"
    )


def get_article_hash(source: str, destination: str, data: dict) -> str:
    return sha256(
        f"{source}+{destination}+{data['subject']}+{data['body']}+{data['references']}+"
        f"{data['reply_to']}".encode(encoding="utf-8")
    ).hexdigest()
