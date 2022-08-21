from hashlib import sha256
from typing import List

from models import DTNMessage, Newsgroup


async def get_all_newsgroups() -> dict:
    return {ng.name: ng for ng in await Newsgroup.all()}


async def get_all_spooled_messages() -> List[dict]:
    return await DTNMessage.all().values(
        "source", "destination", "data", "hash", "delivery_notification", "lifetime"
    )


def get_article_hash(source: str, destination: str, data: dict) -> str:
    return sha256(
        f"{source}+{destination}+{data['subject']}+{data['body']}+{data['references']}".encode(
            encoding="utf-8"
        )
    ).hexdigest()
