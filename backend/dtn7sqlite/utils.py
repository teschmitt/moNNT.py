from datetime import datetime, timedelta
from hashlib import sha256
from typing import List

from backend.dtn7sqlite.config import config
from backend.dtn7sqlite.models import Article, Newsgroup


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


async def _delete_expired_articles() -> int:
    cutoff_dt: datetime = datetime.utcnow() - timedelta(
        milliseconds=config["usenet"]["expiry_time"]
    )
    return await Article.filter(created_at__lt=cutoff_dt).delete()


def _bp7sender_to_nntpfrom(sender: str) -> str:
    if not sender.startswith("//") and not sender.startswith("dtn://"):
        raise ValueError(f"'{sender}' does not seem to be a valid DTN identifier")
    sender_data: List[str] = sender.replace("dtn://", "").replace("//", "").split("/")
    return f"{sender_data[-1]}@{sender_data[-2]}"


def group_name_to_endpoint(group_name: str):
    return f"dtn://{group_name}/~news"
