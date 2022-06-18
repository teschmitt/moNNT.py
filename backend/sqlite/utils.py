from models.newsgroup import Newsgroup


async def get_all_newsgroups() -> list[str]:
    return [ng["name"] for ng in await Newsgroup.all().values("name")]
