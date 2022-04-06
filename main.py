import asyncio
import logging
import multiprocessing
from logging.config import fileConfig

from tortoise import Tortoise, run_async

from logger import global_logger

# from nntp_reqest_handler import NNTPRequestHandler
from nntp_server import AsyncTCPServer
from settings import settings
from version import get_version


async def init_db():
    await Tortoise.init(db_url=settings.DB_URL, modules={"models": ["models"]})
    # logger.info(f"Connected to database {settings.DB_URL}")


if __name__ == "__main__":
    logger = global_logger(__name__)

    # with NNTPServer(
    #     (settings.NNTP_HOSTNAME, settings.NNTP_PORT), NNTPRequestHandler
    # ) as server:
    #     addr, port = server.server_address
    #     logger.info(f"moNNT.py Usenet Server {get_version()}")
    #     run_async(init_db())
    #     logger.info(f"Server running at {addr}:{port}")
    #     server.serve_forever()
    #     logger.info(f"Server shutdown")

    logger.info(f"moNNT.py Usenet Server {get_version()}")
    run_async(init_db())
    loop = asyncio.new_event_loop()
    server = AsyncTCPServer(settings.NNTP_HOSTNAME, settings.NNTP_PORT)
    loop.run_until_complete(server.start_serving())
    loop.run_forever()
