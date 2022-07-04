import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from logging import Logger
from threading import Thread
from typing import Optional, Union, TYPE_CHECKING, Callable

import cbor2
from cbor2 import CBORDecodeEOF
from py_dtn7 import DTNWSClient, DTNRESTClient, from_dtn_timestamp, Bundle
from tortoise import Tortoise, run_async
from urllib3.exceptions import NewConnectionError, MaxRetryError

from backend.dtn7sqlite import get_all_spooled_messages, get_all_newsgroups
from backend.dtn7sqlite.config import config
from logger import global_logger
from models import DTNMessage
from settings import settings

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


class Backend(ABC):
    logger: Logger
    server: "AsyncTCPServer"

    def __init__(self, server: "AsyncTCPServer"):
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
    _groups: list[str]
    _ready_to_send: bool
    _rest_client: Optional[DTNRESTClient]
    _rest_runner: Optional[Thread]
    _ws_client: Optional[DTNWSClient]
    _ws_runner: Optional[Thread]
    _thread_runners: list[Thread]

    def __init__(self, server: "AsyncTCPServer"):
        super().__init__(server)

        # Connect to db
        """
        This is the only connection that absolutely needs to be established for this backend to run.
        Even if there is no DTNd running or the connection to the daemon is unreliable, the
        middleware can start services as soon as the DB connection is up and should shut down
        gracefully if it can't be established.
        """
        run_async(self._init_db())
        self._groups: list[str] = asyncio.new_event_loop().run_until_complete(get_all_newsgroups())

        self._ready_to_send = False
        self._rest_client = None
        self._rest_runner = None
        self._ws_client = None
        self._ws_runner = None
        self._thread_runners = []

    def call_command(self):
        pass

    def stop(self) -> None:
        for t in self._thread_runners:
            t.join(timeout=0.2)

    def start(self) -> None:
        """
        Initializes all needed connections and starts running the backend.
        :return: None
        """

        for c in [
            self._ws_connector,
            self._rest_connector,
            self._register_all_groups,
            self._ingest_all_from_dtnd,
            self._deliver_spool
        ]:
            t = Thread(target=c, daemon=True)
            t.start()
            self._thread_runners.append(t)


    def save_article(self) -> None:
        pass

    async def _init_db(self) -> None:
        await Tortoise.init(db_url=settings.DB_URL, modules={"models": ["models"]})
        self.logger.info(f"Connected to database {settings.DB_URL}")

    async def _send_to_dtnd(self, dtn_args: dict, dtn_payload: dict, hash: str) -> None:
        # register the source endpoint so dtnd knows we want to keep the message in memory
        logger = global_logger()
        logger.debug(f"Registering message source as endpoint: {dtn_args['source']}")
        try:
            logger.debug(f"Sending article to DTNd with {dtn_args}")
            self._ws_client.send_data(**dtn_args, data=cbor2.dumps(dtn_payload))
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
                logger.warning(
                    f"Could not update the error log of spool entry for message {hash}: {e}"
                )

    def _ws_connector(self) -> None:
        """
        Must be run in a Thread and will keep a WS-connection open for as long as the
        server lives. Reconnects automatically when the connection drops and uses exponential
        backoff to pace reconnection attempts
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
                self._ws_client = DTNWSClient(
                    callback=self._ws_data_handler,
                    endpoints=self._groups,
                )
            except ConnectionError as e:
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
            self._ws_client.start_client()

            # this will run only when start_client() returns/connection is lost.
            self._ws_client.stop_client()

        self.logger.info("Permanently stopped backend (WebSocket Client)")

    def _rest_connector(self) -> None:
        # TODO: in the backend object, install a periodic task that checks to see of the REST connection
        # is still alive.
        # - Maybe even a decorator for every function that contains a rest call to enable
        #   exponentioal backoff?
        # - Every rest call has to be wrapped in a try catch block that reinstates the REST client
        #   in case the call fails.
        # - One more possibility: move all the startup and reconnect tasks into a separate thread
        #   altogether so they can run in the background while the user can already use the program
        #   normally.

        host: str = config["dtnd"]["host"]
        port: int = config["dtnd"]["port"]
        retries: int = 0
        initial_wait: float = config["backoff"]["initial_wait"]
        max_retries: int = config["backoff"]["max_retries"]

        while not self.server.terminated and retries <= max_retries:
            # naive exponential backoff implementation
            time.sleep((retries**2) * initial_wait)
            # register and subscribe to all newsgroup endpoints
            self.logger.debug("Contacting DTNs REST interface")
            try:
                self._rest_client = DTNRESTClient(host=host, port=port)
            except ConnectionError | NewConnectionError | MaxRetryError as e:
                self.logger.exception(e)
                if retries >= max_retries:
                    self.logger.error(f"DTNd REST interface not available, not trying again")
                    break
                new_sleep: int = (retries**2) * initial_wait
                self.logger.debug(
                    f"DTNd REST interface not available, waiting for {new_sleep} seconds"
                )
                time.sleep(new_sleep)
                retries += 1

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

        if isinstance(ws_data, str):
            self.logger.debug(
                f"Received WebSocket data from DTNd, probably a status message: {ws_data}"
            )
            # probably a status code, so check if it's an error that should be logged
            if ws_data.startswith("4"):
                self.logger.info(f"User caused an error: {ws_data}")
            if ws_data.startswith("5"):
                self.logger.error(f"Server-side error: {ws_data}")

        elif isinstance(ws_data, bytes):
            self.logger.debug("Received WebSocket data from DTNd. Data determined to by bytes.")
            try:
                ws_dict: dict = cbor2.loads(ws_data)
            except (CBORDecodeEOF, MemoryError) as e:
                err: RuntimeError = RuntimeError(
                    "Something went wrong decoding a CBOR data object. Any intended save operation "
                    f"will fail on account of this error: {e}"
                )
                self.logger.exception(err)
                raise err

            try:
                self.logger.debug("Starting data handler.")
                asyncio.new_event_loop().run_until_complete(
                    self.handle_sent_article(ws_struct=ws_dict)
                )
            except Exception as e:  # noqa E722
                # TODO: do some error handling here
                raise Exception(e)

        else:
            raise ValueError("Handler received unrecognizable data.")

    def _deliver_spool(self) -> None:
        self.logger.debug("Getting spooled msgs")
        msgs: list[dict] = asyncio.new_event_loop().run_until_complete(get_all_spooled_messages())

        # exponential backoff again:
        retries: int = 0
        initial_wait: float = 0.1
        while not self.server.backend.running:
            self.logger.debug(
                "WebSocket backend not started, waiting for"
                f" {(retries ** 2) * initial_wait} seconds"
            )
            time.sleep((retries**2) * initial_wait)
            retries += 1


    def _register_all_groups(self) -> None:
        """
        First gets all active newsgroups from the DB. Then waits for the REST client to go online
        and then registers all groups with the DTNd backend.
        :return: None
        """
        # wait for REST client to come online
        while not self.server.terminated and self._rest_client is None:
            time.sleep(0.5)
        if self._rest_client is not None:
            for group_name in self._groups:
                self.logger.debug(
                    f"Registering endpoint with REST client: dtn://{group_name}/~news"
                )
                self._rest_client.register(endpoint=f"dtn://{group_name}/~news")
            self._ready_to_send = True

    def _ingest_all_from_dtnd(self) -> None:
        self.logger.debug("Ingesting all newsgroup bundles in DTNd bundle store.")
        self.logger.debug(f"Found {len(self._groups)} active newsgroups on this server.")

        # wait for REST client to come online
        while self._rest_client is None:
            time.sleep(0.5)

        received_bundles: list[Bundle] = []
        for group in self._groups:
            received_bundles.append(self._rest_client.get_filtered_bundles(address_part_criteria=)

        all_bundles: filter = filter(
            lambda b: b.destination.replace("dtn://", "").replace("//", "").replace("/~news", "")
            in self._groups,
            rest.get_all_bundles(),
        )

        for bundle in all_bundles:
            msg_id: str = (
                f"<{bundle.timestamp}-{bundle.sequence_number}@"
                f"{bundle.source.replace('dtn://', '').replace('/', '-')}.dtn>"
            )

            mail_domain, mail_name = (
                bundle.source.replace("dtn://", "").replace("//", "").split("/mail/", maxsplit=1)
            )
            from_: str = f"{mail_name}@{mail_domain}"

            group_name: str = (
                bundle.destination.replace("dtn://", "").replace("//", "").replace("/~news", "")
            )
            group: Newsgroup = await Newsgroup.get_or_none(name=group_name)

            data: dict = cbor2.loads(bundle.payload_block.data)

            _, created = await Message.get_or_create(
                newsgroup=group,
                from_=from_,
                subject=data["subject"],
                created_at=from_dtn_timestamp(int(bundle.timestamp)),
                message_id=msg_id,
                body=data["body"],
                # path=f"!{settings.DOMAIN_NAME}",
                references=data["references"],
                reply_to=data["reply-to"],
            )
            if created:
                self.logger.debug(
                    f"Created new newsgroup article {msg_id} in newsgroup '{group.name}'."
                )
            else:
                self.logger.debug(f"Article {msg_id} already present in newsgroup '{group.name}'.")
