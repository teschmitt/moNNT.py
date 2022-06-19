from models import DTNMessage, Newsgroup


async def get_all_newsgroups() -> list[str]:
    return [ng["name"] for ng in await Newsgroup.all().values("name")]


async def get_all_spooled_messages() -> list[dict]:
    return await DTNMessage.all().values(
        "source", "destination", "data", "delivery_notification", "lifetime"
    )
