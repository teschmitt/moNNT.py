import asyncio
from threading import Thread

from py_dtn7 import DTNRESTClient, DTNWSClient
from tortoise import Tortoise, run_async

from backend.sqlite.save import ws_handler
from logger import global_logger
from nntp_server import AsyncTCPServer
from settings import settings
from utils import get_version


async def init_db():
    await Tortoise.init(db_url=settings.DB_URL, modules={"models": ["models"]})
    logger.info(f"Connected to database {settings.DB_URL}")


if __name__ == "__main__":
    logger = global_logger()

    logger.info(f"moNNT.py Usenet Server {get_version()}")
    run_async(init_db())
    loop = asyncio.new_event_loop()

    ws_client = DTNWSClient(callback=ws_handler)
    nntp_server = AsyncTCPServer(
        hostname=settings.NNTP_HOSTNAME, port=settings.NNTP_PORT, backend=ws_client
    )
    # TODO: set up WS DTN Client here like this:
    # https://stackoverflow.com/a/40225614
    ws_task: Thread = Thread(target=ws_client.start_client)
    ws_task.start()

    # subscribe to all newsgroup endpoints
    rest = DTNRESTClient()
    for eid in filter(lambda e: "/~news" in e, rest.endpoints):
        ws_client.subscribe(endpoint=eid)

    loop.run_until_complete(nntp_server.start_serving())
    loop.run_forever()
    ws_client.stop_client()
    ws_task.join()
