import asyncio
from hashlib import sha256
from logging import Logger
from typing import Optional

from py_dtn7 import DTNRESTClient

from backend.dtn7sqlite.config import config as dtn7config
from logger import global_logger
from models import DTNMessage, Newsgroup


async def get_all_newsgroups() -> list[str]:
    return [ng["name"] for ng in await Newsgroup.all().values("name")]


async def get_all_spooled_messages() -> list[dict]:
    return await DTNMessage.all().values(
        "source", "destination", "data", "hash", "delivery_notification", "lifetime"
    )


async def get_rest() -> DTNRESTClient:
    # TODO: in the backend object, install a periodic task that checks to see of the REST connection
    # is still alive.
    # - Maybe even a decorator for every function that contains a rest call to enable
    #   exponentioal backoff?
    # - Every rest call has to be wrapped in a try catch block that reinstates the REST client
    #   in case the call fails.
    # - One more possibility: move all the startup and reconnect tasks into a separate thread
    #   altogether so they can run in the background while the user can already use the program
    #   normally.
    logger: Logger = global_logger()
    rest: Optional[DTNRESTClient] = None
    host: str = dtn7config["dtnd"]["host"]
    port: int = dtn7config["dtnd"]["port"]
    retries: int = 0
    initial_wait: float = 0.5
    max_retries: int = 5

    while rest is None:
        logger.debug("Contacting DTNs REST interface")
        try:
            rest = DTNRESTClient(host=host, port=port)
        except Exception as e:
            logger.exception(e)
            if retries >= max_retries:
                break
            new_sleep: int = (retries**2) * initial_wait
            logger.debug(f"DTNd REST interface not available, waiting for {new_sleep} seconds")
            await asyncio.sleep(new_sleep)
            retries += 1

    return rest


def get_article_hash(source: str, destination: str, data: dict) -> str:
    return sha256(
        f"{source}+{destination}+{data['subject']}+{data['body']}+{data['references']}+"
        f"{data['reply_to']}".encode(encoding="utf-8")
    ).hexdigest()
