import asyncio
import time
from threading import Thread

from py_dtn7 import DTNRESTClient, DTNWSClient
from tortoise import Tortoise, run_async
from urllib3.exceptions import NewConnectionError, MaxRetryError

from backend.dtn7sqlite import get_all_newsgroups
from backend.dtn7sqlite.save import ws_handler
from logger import global_logger
from nntp_server import AsyncTCPServer
from settings import settings
from utils import get_version


async def init_db():
    await Tortoise.init(db_url=settings.DB_URL, modules={"models": ["models"]})
    logger.info(f"Connected to database {settings.DB_URL}")


async def register_all_groups(client: DTNRESTClient):
    for group_name in await get_all_newsgroups():
        logger.debug(f"Registering endpoint with REST client: dtn://{group_name}/~news")
        client.register(endpoint=f"dtn://{group_name}/~news")


def reconnect_handler(server: AsyncTCPServer):
    retries: int = 0
    initial_wait: float = 0.1
    max_retries: int = 5
    reconn_pause: int = 5
    while not server.terminated and retries <= max_retries:
        # naive exponential backoff implementation
        time.sleep((retries ** 2) * initial_wait)
        # register and subscribe to all newsgroup endpoints
        try:
            rest = DTNRESTClient()
            asyncio.new_event_loop().run_until_complete(register_all_groups(client=rest))
            ws_client = DTNWSClient(
                callback=ws_handler, endpoints=filter(lambda e: "/~news" in e, rest.endpoints)
            )
            server.backend = ws_client
        except Exception as e:
            retries += 1
            logger.warning(e)
            if retries <= max_retries:
                logger.warning(f"Connection to DTNd not possible, retrying after {(retries ** 2) * initial_wait} seconds.")
            else:
                logger.error(
                    f"DTNd seems permanently down. Reconnection attempts paused for {reconn_pause} seconds.")
                time.sleep(reconn_pause)
                retries = 0
                logger.info("Restarting reconnection attempts with DTNd.")
            continue

        retries = 0
        ws_client.start_client()
        # this will run only when start_client() returns/connection is lost.
        ws_client.stop_client()

    logger.info("Stopped WebSocket client.")


if __name__ == "__main__":
    logger = global_logger()

    logger.info(f"moNNT.py Usenet Server {get_version()}")
    run_async(init_db())
    loop = asyncio.new_event_loop()
    nntp_server = AsyncTCPServer(
        hostname=settings.NNTP_HOSTNAME, port=settings.NNTP_PORT, backend=None
    )

    """
    --------------------------------------------------------------------------------------------------------------------
    This is where the not so clean code begins
    TODO: make a Backend class that encapsulates all of this logic in its __init__ or something
    """

    reconn_task: Thread = Thread(target=reconnect_handler, kwargs={"server": nntp_server})
    reconn_task.daemon = True
    reconn_task.start()

    """
    --------------------------------------------------------------------------------------------------------------------
    This is where the not so clean code ends
    """

    loop.run_until_complete(nntp_server.start_serving())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Received Ctrl-C, stopping server")

    reconn_task.join()
