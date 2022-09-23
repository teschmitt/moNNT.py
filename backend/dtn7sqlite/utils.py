from hashlib import sha256
from typing import List

from models import Newsgroup


async def get_all_newsgroups() -> dict:
    return {ng.name: ng for ng in await Newsgroup.all()}


def get_article_hash(source: str, destination: str, data: dict) -> str:
    return sha256(
        f"{source}+{destination}+{data['subject']}+{data['body']}+{data['references']}".encode(
            encoding="utf-8"
        )
    ).hexdigest()


def _bundleid_to_messageid(bid: str) -> str:
    """ """
    bid_data: List[str] = bid.rsplit(sep="-", maxsplit=2)
    src_like: str = bid_data[0].replace("dtn://", "").replace("//", "").replace("/", "-")
    return f"<{bid_data[-2]}-{bid_data[-1]}@{src_like}.dtn>"
