import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from logging import Logger
from threading import Thread
from typing import Optional, Union

import cbor2
from py_dtn7 import DTNWSClient, DTNRESTClient
from tortoise import Tortoise, run_async

from backend.dtn7sqlite.config import config
from logger import global_logger
from models import DTNMessage
from nntp_server import AsyncTCPServer
from settings import settings


class Backend(ABC):
    logger: Logger
    server: AsyncTCPServer

    def __init__(self, server: AsyncTCPServer):
        self.logger = global_logger()
        self.server = server

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def call_command(self):
        pass

    @abstractmethod
    async def save_article(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class DTN7Backend(Backend):
    rest_client = Optional[DTNRESTClient]
    ws_client: Optional[DTNWSClient]

    def __int__(self, server: AsyncTCPServer):
        super().__init__(server)

        self.rest_client = None
        self.ws_client = None

    def call_command(self):
        pass

    def stop(self):
        pass

    def start(self):
        """

        2. get WS client
        3. get REST client

        4. register all groups
        5. REST: ingest all from DTNd
        6. WS: send spool
        """

        # 1. Connect to db
        run_async(self._init_db())

        # 2. get WS client

    def save_article(self):
        pass

    async def _init_db(self):
        await Tortoise.init(db_url=settings.DB_URL, modules={"models": ["models"]})
        self.logger.info(f"Connected to database {settings.DB_URL}")

    async def send_to_dtnd(
            self, dtn_args: dict, dtn_payload: dict, hash: str
    ):
        # register the source endpoint so dtnd knows we want to keep the message in memory
        logger = global_logger()
        logger.debug(f"Registering message source as endpoint: {dtn_args['source']}")
        try:
            logger.debug(f"Sending article to DTNd with {dtn_args}")
            self.ws_client.send_data(**dtn_args, data=cbor2.dumps(dtn_payload))
        except Exception as e:
            # log failure in spool entry
            try:
                msg: DTNMessage = await DTNMessage.get_or_none(hash=hash)
                if msg.error_log is None:
                    msg.error_log = ""
                msg.error_log += (
                    f"\n{datetime.utcnow().isoformat()} ERROR Failure delivering to DTNd: {e}"
                )
                await msg.save()
            except Exception as e:  # noqa E722
                logger.warning(f"Could not update the error log of spool entry for message {hash}: {e}")

    def _ws_connector(self, endpoints: list[str]):
        """
        Must be run in a Thread and will keep a WS-connection open for as long as the
        server lives. Reconnects automatically when the connection drops.
        """
        retries: int = 0
        initial_wait: float = config["backoff"]["initial_wait"]
        max_retries: int = config["backoff"]["max_retries"]
        reconn_pause: int = config["backoff"]["reconn_pause"]

        while not self.server.terminated and retries <= max_retries:
            # naive exponential backoff implementation
            time.sleep((retries**2) * initial_wait)
            # register and subscribe to all newsgroup endpoints
            try:
                ws_client = DTNWSClient(callback=self._ws_data_handler,endpoints=endpoints,)
            except Exception as e:
                # requests is kind of stingy raising errors ... I was not able to catch a MaxRetries or
                # ConnectionError so for now we'll just catch all exceptions and get on with our lives.
                retries += 1
                self.logger.warning(e)
                if retries <= max_retries:
                    self.logger.warning(
                        "Connection to DTNd not possible, retrying after"
                        f" {(retries ** 2) * initial_wait} seconds."
                    )
                else:
                    self.logger.error(
                        "DTNd seems permanently down. Articles will be saved to spool and sent upon"
                        f" reconnection. Reconnection attempts paused for {reconn_pause} seconds."
                    )
                    time.sleep(reconn_pause)
                    retries = 0
                    self.logger.info("Restarting reconnection attempts with DTNd.")
                continue

            retries = 0
            dlv_spool: Thread = Thread(target=deliver_spool, kwargs={"server": self.server})
            dlv_spool.daemon = True
            dlv_spool.start()
            ws_client.start_client()
            # this will run only when start_client() returns/connection is lost.
            dlv_spool.join()  # we want to stay tidy, even if this might be superfluous
            ws_client.stop_client()

        self.logger.info("Permanently stopped backend (WebSocket Client)")

    def _ws_data_handler(self, ws_data: Union[str | bytes]) -> None:
        """
        This gets called when data gets sent over the WebSockets connection from remote.
        In cases where an article has been sent over to the DTNd, the DTNd will return a
        struct with lots of handy information we can use to persist the article in our
        local DB, so we scrape all that meaningful DTN-data out of the returned struct and
        let the ORM handle the rest
        :param ws_data: data sent from the DTNd over the Websockets connection
        :return: None
        """
        logger = global_logger()

        if isinstance(ws_data, str):
            logger.debug(f"Received WebSocket data from DTNd, probably a status message: {ws_data}")
            # probably a status code, so check if it's an error that should be logged
            if ws_data.startswith("4"):
                logger.info(f"User caused an error: {ws_data}")
            if ws_data.startswith("5"):
                logger.error(f"Server-side error: {ws_data}")

        elif isinstance(ws_data, bytes):
            logger.debug("Received WebSocket data from DTNd. Data determined to by bytes.")
            try:
                ws_dict: dict = cbor2.loads(ws_data)
            except (CBORDecodeEOF, MemoryError) as e:
                err: RuntimeError = RuntimeError(
                    "Something went wrong decoding a CBOR data object. Any intended save operation "
                    f"will fail on account of this error: {e}"
                )
                logger.exception(err)
                raise err

            try:
                logger.debug("Starting data handler.")
                asyncio.new_event_loop().run_until_complete(handle_sent_article(ws_struct=ws_dict))
            except Exception as e:  # noqa E722
                # TODO: do some error handling here
                raise Exception(e)

        else:
            raise ValueError("Handler received unrecognizable data.")
