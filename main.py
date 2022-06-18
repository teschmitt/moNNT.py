import asyncio
from threading import Thread

from py_dtn7 import DTNRESTClient, DTNWSClient
from tortoise import Tortoise, run_async

from backend.dtn7sqlite import get_all_newsgroups
from backend.dtn7sqlite.save import ws_handler
from logger import global_logger
from nntp_server import AsyncTCPServer
from settings import settings
from utils import get_version


async def init_db():
    await Tortoise.init(db_url=settings.DB_URL, modules={"models": ["models"]})
    logger.info(f"Connected to database {settings.DB_URL}")


async def register_all_groups():
    for group_name in await get_all_newsgroups():
        logger.debug(f"Registering endpoint with REST client: dtn://{group_name}/~news")
        rest.register(endpoint=f"dtn://{group_name}/~news")


if __name__ == "__main__":
    logger = global_logger()

    logger.info(f"moNNT.py Usenet Server {get_version()}")
    run_async(init_db())
    loop = asyncio.new_event_loop()

    """
    --------------------------------------------------------------------------------------------------------------------
    This is where the not so clean code begins
    TODO: make a Backend class that encapsulates all of this logic in its __init__ or something
    """
    ws_client = DTNWSClient(callback=ws_handler)
    nntp_server = AsyncTCPServer(
        hostname=settings.NNTP_HOSTNAME, port=settings.NNTP_PORT, backend=ws_client
    )
    ws_task: Thread = Thread(target=ws_client.start_client)
    ws_task.start()

    # subscribe to all newsgroup endpoints
    rest = DTNRESTClient()
    asyncio.new_event_loop().run_until_complete(register_all_groups())
    for eid in filter(lambda e: "/~news" in e, rest.endpoints):
        logger.debug(f"Subscribing to endpoint {eid}")
        ws_client.subscribe(endpoint=eid)
    """
    --------------------------------------------------------------------------------------------------------------------
    This is where the not so clean code ends
    """

    loop.run_until_complete(nntp_server.start_serving())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Received Ctrl-C, stopping server")

    """
    --------------------------------------------------------------------------------------------------------------------
    call the Backend cleanup crew
    """
    ws_client.stop_client()
    ws_task.join()
    print("Stopped WebSocket client. Exiting.")
    """
    --------------------------------------------------------------------------------------------------------------------
    """
