#!/usr/bin/python3 -u

import asyncio

from backend.dtn7sqlite.backend import DTN7Backend
from logger import global_logger
from nntp_server import AsyncNNTPServer
from settings import settings
from utils import get_version

if __name__ == "__main__":
    logger = global_logger()

    logger.info(f"moNNT.py Usenet Server {get_version()}")

    """
    Required procedure:
    1. create server
    2. attach backend
    3. start backend
    4. start server
    """
    loop = asyncio.new_event_loop()
    nntp_server = AsyncNNTPServer(hostname=settings.NNTP_HOSTNAME, port=settings.NNTP_PORT)
    nntp_server.backend = DTN7Backend(server=nntp_server)

    loop.run_until_complete(nntp_server.start_serving())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Received Ctrl-C, stopping server")
    finally:
        nntp_server.stop_serving()
        logger.info("Stopped server")
        loop.stop()
        loop.close()
