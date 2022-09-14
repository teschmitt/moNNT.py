import asyncio
import time
from asyncio import AbstractEventLoop, Task
from collections import defaultdict
from datetime import datetime
from threading import Thread
from typing import (
    TYPE_CHECKING,
    Callable,
    ClassVar,
    DefaultDict,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

import cbor2
from cbor2 import CBORDecodeEOF
from py_dtn7 import Bundle, DTNRESTClient, DTNWSClient, from_dtn_timestamp
from requests.exceptions import ConnectionError
from tortoise import Tortoise, run_async
from tortoise.exceptions import IntegrityError, OperationalError
from tortoise.transactions import in_transaction

from backend.base import Backend
from backend.dtn7sqlite import get_all_newsgroups, get_all_spooled_messages
from backend.dtn7sqlite.config import config
from backend.dtn7sqlite.nntp_commands import (
    article,
    capabilities,
    current,
    date,
    group,
    hdr,
    head_body_stat,
    help,
    last,
    list_command,
    listgroup,
    mode,
    newgroups,
    newnews,
    next,
    over,
    post,
    quit_,
)
from backend.dtn7sqlite.utils import get_article_hash
from models import DTNMessage, Message, Newsgroup

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


def _bundleid_to_messageid(bid: str) -> str:
    """ """
    bid_data: List[str] = bid.rsplit(sep="-", maxsplit=2)
    src_like: str = bid_data[0].replace("dtn://", "").replace("//", "").replace("/", "-")
    return f"<{bid_data[-2]}-{bid_data[-1]}@{src_like}.dtn>"


class DTN7Backend(Backend):
    call_dict: ClassVar[Dict[str, Callable]] = {
        "article": article.do_article,
        "body": head_body_stat.do_head_body_stat,
        "capabilities": capabilities.do_capabilities,
        "current": current.do_current,
        "date": date.do_date,
        "group": group.do_group,
        "hdr": hdr.do_hdr,
        "head": head_body_stat.do_head_body_stat,
        "help": help.do_help,
        "last": last.do_last,
        "list": list_command.do_list,
        "listgroup": listgroup.do_listgroup,
        "mode": mode.do_mode,
        "newgroups": newgroups.do_newgroups,
        "newnews": newnews.do_newnews,
        "next": next.do_next,
        "over": over.do_over,
        "post": post.do_post,
        "quit": quit_.do_quit,
        "stat": head_body_stat.do_head_body_stat,
        "xhdr": hdr.do_hdr,
        "xover": over.do_over,
    }

    _group_names: List[str]
    _ready_to_send: bool
    _rest_client: Optional[DTNRESTClient]
    _ws_client: Optional[DTNWSClient]
    _ws_runner: Optional[Thread]
    # _loop: AbstractEventLoop
    _newsgroups: Dict
    _background_tasks: Set[Task]

    def __init__(self, server: "AsyncNNTPServer", loop: AbstractEventLoop):
        super().__init__(server=server, loop=loop)

        # Connect to db
        """
        This is the only connection that absolutely needs to be established for this backend to run.
        Even if there is no DTNd running or the connection to the daemon is unreliable, the
        middleware can start services as soon as the DB connection is up and should shut down
        gracefully if it can't be established.
        """
        run_async(self._init_db())
        self._loop = loop  # asyncio.new_event_loop()
        self._newsgroups = {}
        self._group_names = []
        self._background_tasks = set()

        self._rest_client = None
        self._ws_client = None
        self._ws_runner = None

    def stop(self) -> None:
        self.logger.info("Stopping DTN7Backend")
        self._ws_runner.join(timeout=config["backoff"]["constant_wait"])
        self._loop.stop()
        self._loop.close()

    async def start(self) -> None:
        """
        Initialize connections first and then run the start tasks
        """

        # config.toml is single source of truth, so:
        # add all newsgroups that are in config.toml but not in db,
        # delete all in db and not in config
        self._newsgroups = await get_all_newsgroups()
        self._group_names = list(self._newsgroups.keys())
        want_set: set = set(config["usenet"]["newsgroups"])
        have_set: set = set(self._group_names)
        self.logger.info("Reconciling newsgroup configuration with database")
        for gn in want_set - have_set:
            self.logger.info(f" -> Adding new group '{gn}'")
            new_group: Newsgroup = await Newsgroup.create(name=gn)
            self._group_names.append(gn)
            self._newsgroups[gn] = new_group
        for gn in have_set - want_set:
            self.logger.info(f" -> Removing group '{gn}'")
            await Newsgroup.filter(name=gn).delete()
            self._group_names.remove(gn)
            del self._newsgroups[gn]

        self.logger.debug(f"Found {len(self._group_names)} active newsgroups on this server.")

        await self._rest_connector()

        # execute the WS connector in a new thread
        # asyncio.new_event_loop().run_until_complete(self._ws_connector())
        # self._ws_runner = asyncio.create_task(self._ws_connector())

        await self._ingest_all_from_dtnd()
        await self._start_ws_client()
        await self._deliver_spool()

    async def _start_ws_client(self):
        self._ws_runner = Thread(target=self._ws_connector, daemon=True)
        self._ws_runner.start()

    async def _deliver_spool(self) -> None:
        """
        Gets all spooled messages from the DB and (re)sends them to the DTNd. In here, we assume all
        connections to the DTNd are alive and healthy, so we do only minimal error recovery.
        """
        self.logger.debug("Getting spooled msgs")
        msgs: List[dict] = await get_all_spooled_messages()

        while self._ws_client is None or not self._ws_client.running:
            await asyncio.sleep(config["backoff"]["constant_wait"])

        self.logger.info(f"Sending {len(msgs)} spooled messages to DTNd")
        await asyncio.gather(
            *(
                self._send_to_dtnd(
                    dtn_args={
                        "destination": msg["destination"],
                        "source": msg["source"],
                        "delivery_notification": msg["delivery_notification"],
                        "lifetime": msg["lifetime"],
                    },
                    dtn_payload=msg["data"],
                    hash_=msg["hash"],
                )
                for msg in msgs
            )
        )
        self.logger.info(f"Done sending {len(msgs)} spooled messages to DTNd")

    async def _send_to_dtnd(self, dtn_args: dict, dtn_payload: dict, hash_: str):
        """
        Uses the WS interface of the dtnd to send dtn_payload as a cbor encoded payload block.
        Args:
            dtn_args: all relevant dtnd-data: source, destination, lifetime, delivery notification
            dtn_payload: dict of payload data to be cbor-encoded and sent
            hash_: hash of spooled message used to update error log of spooled message entry on
                   difficulties connecting with dtnd
        """
        try:
            self.logger.debug(f"Sending article to DTNd with {dtn_args}")
            if self._ws_client is not None:
                self._ws_client.send_data(**dtn_args, data=cbor2.dumps(dtn_payload))
            else:
                raise ConnectionError(
                    "No current connection to WS client. Article is in spool and will be sent on"
                    " reconnect."
                )
        except Exception as e:  # noqa E722
            # log failure in spool entry
            try:
                msg: DTNMessage = await DTNMessage.get_or_none(hash=hash_)
                if msg.error_log is None:
                    msg.error_log = ""
                msg.error_log += (
                    f"\n{datetime.utcnow().isoformat()} ERROR Failure delivering to DTNd: {e}"
                )
                await msg.save()
            except Exception as e:  # noqa E722
                self.logger.warning(
                    f"Could not update the error log of spool entry for message {hash_}: {e}"
                )

    async def _register_all_groups(self) -> None:
        """
        First gets all active newsgroups from the DB. Then waits for the REST client to go online
        and then registers all groups with the DTNd backend.
        :return: None
        """
        for group_name in self._group_names:
            self.logger.debug(f"Registering endpoint with REST client: dtn://{group_name}/~news")
            self._rest_client.register(endpoint=f"dtn://{group_name}/~news")

        # also register the email address of sender, so we get info on sent
        # articles through WebSocket back channel
        sender_endpoint: str = self._nntpfrom_to_bp7sender(config["usenet"]["email"])
        self.logger.debug(f"Registering WS back-channel: {sender_endpoint}")
        self._rest_client.register(endpoint=sender_endpoint)

    async def _ingest_all_from_dtnd(self) -> None:
        """ """
        self.logger.info("Ingesting all newsgroup bundles in DTNd bundle store.")

        while self._rest_client is None:
            self.logger.debug("Waiting for REST client to come online")
            await asyncio.sleep(config["backoff"]["constant_wait"])

        # Gather all known message ids to compare to potential new articles later
        known_message_ids: Set[str] = set(
            msg["message_id"] for msg in await Message.all().values("message_id")
        )
        received_bundles: Set[str] = set()
        if self._rest_client is not None:
            for group_name in self._group_names:
                try:
                    self.logger.debug(f"Getting known bundles for group '{group_name}'")
                    new_bundles: List[str] = self._rest_client.get_filtered_bundles(
                        address_part_criteria=group_name
                    )
                    self.logger.debug(f"Got {len(new_bundles)} articles for group '{group_name}':")
                    received_bundles.update(new_bundles)
                except Exception as e:  # noqa E722
                    self.logger.warning(f"Error getting bundles from REST interface: {e}")
                    self.logger.exception(e)
        else:
            await self._rest_connector()

        try:
            # open a transaction and commit all new articles to db at once
            async with in_transaction() as connection:
                for bundle_id in received_bundles:
                    # filter out known articles PREMATURE
                    msg_id = _bundleid_to_messageid(bundle_id)
                    if msg_id in known_message_ids:
                        self.logger.debug(f"{msg_id} is a duplicate, discarding")
                        continue

                    if self._rest_client is None:
                        await self._rest_connector()

                    bundle = Bundle.from_cbor(self._rest_client.download(bundle_id=bundle_id))
                    # map BP7 to NNTP MAPPING
                    from_: str = self._bp7sender_to_nntpfrom(sender=bundle.source)

                    group_name: str = (
                        bundle.destination.replace("dtn://", "")
                        .replace("//", "")
                        .replace("/~news", "")
                    )

                    data: dict = cbor2.loads(bundle.payload_block.data)

                    # self.logger.debug(f"Writing article {msg_id} to DB")
                    await Message.create(
                        newsgroup=self._newsgroups[group_name],
                        from_=from_,
                        subject=data["subject"],
                        created_at=from_dtn_timestamp(int(bundle.timestamp)),
                        message_id=msg_id,
                        body=data["body"],
                        # path=f"!_ingest_all_from_dtnd",
                        references=data["references"],
                        # reply_to=data["reply_to"],
                        using_db=connection,
                    )
                    self.logger.info(
                        f"Created new newsgroup article {msg_id} in newsgroup '{group_name}'."
                    )
        except OperationalError as e:
            self.logger.error(
                "Something went very wrong committing the batch of ingested articles from the"
                f" dtnd. {len(received_bundles)} were not stored in the server DB! Error:"
                f" {e.__str__()}"
            )

    async def save_article(self, article_buffer: List[str]) -> None:
        """
        Takes an article posted ba an NNTP client as a list of strings and does three things with
        it:
          1. parses all relevant article information into data structures
          2. saves the article data to a spool which contains articles that are sent but do not have
             a message-id because the dtnd has not acknowledged then yet. In order to later identify
             the article, a hash on some article data is created and stored along with it
          3. sends the article data to the dtnd in order to receive a message-id through the WS
             back-channel and of course to propagate the article in the network

        Args:
            article_buffer: list of strings containing the raw lines of article data received from
                            the NNTP client
        """

        # TODO: support cross posting to multiple newsgroups
        #       this entails setting up a M2M relationship between message and newsgroup
        #       https://kb.iu.edu/d/affn

        self.logger.debug("Sending article to DTNd and local DTN message spool")
        header: DefaultDict[str] = defaultdict(str)
        line: str = article_buffer.pop(0)
        field_name: str = ""
        field_value: str
        while len(line) != 0:
            try:
                if ":" in line:
                    field_name, field_value = map(
                        lambda s: s.strip(), line.split(sep=":", maxsplit=1)
                    )
                    field_name = field_name.strip().lower()
                    header[field_name] = field_value.strip()
                elif len(field_name) > 0:
                    header[field_name] = f"{header[field_name]} {line}"
            except ValueError:
                # sometimes clients send fishy headers … we'll just ignore them.
                pass
            line = article_buffer.pop(0)

        # article_group = await Newsgroup.get_or_none(name=header["newsgroups"])
        article_group = self._newsgroups[header["newsgroups"]]
        # TODO: Error handling when newsgroup is not in DB

        # we've popped off the complete header, body is just the joined rest
        body: str = "\n".join(article_buffer)
        # dt: datetime = date_parse(
        #   header["date"]) if len(header["date"]) > 0 else datetime.utcnow()

        # some cleaning up:
        header["references"].replace("\t", "")

        group_name: str = article_group.name
        dtn_payload: dict = {
            "subject": header["subject"],
            "body": body,
            "references": header["references"],
            # disregarded headers (some are mapped to BP7 fields, some are reconstructed later when
            # the article has been sent to the dtnd, some are dropped entirely:
            # "newsgroup": group_name,
            # "from": header["from"],
            # "created_at": dt.isoformat(),
            # "message_id": f"<{uuid.uuid4()}@{server_config['domain_name']}>",
            # "path": f"!{server_config['domain_name']}",
            # "reply_to": header["reply-to"],
            # "organization": header["organization"],
            # "user_agent": header["user-agent"],
        }

        # sender email address is defined through backend config, so we don't need to parse it from
        # the incoming data:
        # if "sender" in header:
        #     header["from"] = header["sender"]
        # try:
        #     sender_email: str = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", header["from"]).group(0)
        # except AttributeError as e:
        #     self.logger.warning(f"Email address could not be parsed: {e}")
        #     sender_email: str = "not-recognized@email-address.net"
        sender_email = config["usenet"]["email"]
        source: str = self._nntpfrom_to_bp7sender(from_=sender_email)
        # TODO: get lifetime, destination settings from settings:
        dtn_args: dict = {
            # map NNTP to BP7 MAPPING
            "source": source,
            "destination": f"dtn://{group_name}/~news",
            "delivery_notification": config["bundles"]["delivery_notification"],
            "lifetime": config["bundles"]["lifetime"],
        }

        # HASHING
        message_hash = get_article_hash(
            source=dtn_args["source"], destination=dtn_args["destination"], data=dtn_payload
        )
        self.logger.debug(f"Sending article to DB, got message hash: {message_hash}")

        dtn_msg: DTNMessage = await DTNMessage.create(
            **dtn_args, data=dtn_payload, hash=message_hash
        )
        self.logger.debug(f"Created entry in DTNd message spool with id {dtn_msg.id}")
        self.logger.debug(f"Sending message {dtn_msg.id} to dtnd")

        # send_task: Task = self._loop.create_task(
        #     self._send_to_dtnd(dtn_args=dtn_args, dtn_payload=dtn_payload, hash_=message_hash)
        # )
        # self._background_tasks.add(send_task)
        # send_task.add_done_callback(self._background_tasks.discard)
        await self._send_to_dtnd(dtn_args=dtn_args, dtn_payload=dtn_payload, hash_=message_hash)
        self.logger.debug(f"Done sending message {dtn_msg.id} to dtnd")

    async def _init_db(self) -> None:
        await Tortoise.init(db_url=config["backend"]["db_url"], modules={"models": ["models"]})
        # generate schema only if table does not exist yet
        await Tortoise.generate_schemas(safe=True)

        self.logger.info(f"Connected to database {config['backend']['db_url']}")

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

        self.logger.debug("Setting up WS connection to dtnd")

        while not self.server.terminated:
            # naive exponential backoff implementation
            time.sleep((retries**2) * initial_wait)
            # register and subscribe to all newsgroup endpoints
            try:
                self._ws_client = DTNWSClient(
                    callback=self._ws_data_handler,
                    endpoints=[f"dtn://{gn}/~news" for gn in self._group_names],
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
            # we need to reconnect to REST interface and re-register all newsgroups
            # before we can try reconnecting to the WS interface
            self._rest_client = None
            self._ws_client = None
            self._loop.run_until_complete(self._rest_connector())
            # await self._rest_connector()

        self.logger.info("Permanently stopped backend (WebSocket Client)")

    async def _rest_connector(self) -> None:
        # TODO: in the backend object, install a periodic task that checks to see of the REST
        #  connection is still alive.
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

        while self._rest_client is None and retries <= max_retries:
            # naive exponential backoff implementation
            await asyncio.sleep((retries**2) * initial_wait)
            # register and subscribe to all newsgroup endpoints
            self.logger.debug("Contacting DTNs REST interface")
            try:
                self._rest_client = DTNRESTClient(host=host, port=port)
                self.logger.debug("Successfully contacted REST interface")
            except ConnectionError:
                if retries >= max_retries:
                    self.logger.error("DTNd REST interface not available, not trying again")
                    break
                new_sleep: int = (retries**2) * initial_wait
                self.logger.debug(
                    f"DTNd REST interface not available, waiting for {new_sleep} seconds"
                )
                await asyncio.sleep(new_sleep)
                retries += 1
            else:
                # register all groups with the DTNd backend.
                await self._register_all_groups()

    def _ws_data_handler(self, ws_data: Union[str, bytes]) -> None:
        """
        This gets called when data gets sent over the WebSockets connection from remote.
        In cases where an article has been sent over to the DTNd, the DTNd will return a
        struct with lots of handy information we can use to persist the article in our
        local DB, so we scrape all that meaningful DTN-data out of the returned struct and
        let the ORM handle the rest

        Args:
            ws_data: data sent from the DTNd over the Websockets connection
        """
        self._loop.run_until_complete(self._async_ws_data_handler(ws_data))
        # dh_task: Task = self._loop.create_task(self._async_ws_data_handler(ws_data))
        # self._background_tasks.add(dh_task)
        # dh_task.add_done_callback(self._background_tasks.discard)

    async def _async_ws_data_handler(self, ws_data: Union[str, bytes]) -> None:
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
                # self.logger.debug(f"Data dict: {ws_dict}")
            except (CBORDecodeEOF, MemoryError) as e:
                err: RuntimeError = RuntimeError(
                    "Something went wrong decoding a CBOR data object. Any intended save operation "
                    f"will fail on account of this error: {e}"
                )
                self.logger.exception(err)
                raise err

            try:
                self.logger.debug("Starting data handler.")
                await self._handle_sent_article(ws_struct=ws_dict)
            except Exception as e:  # noqa E722
                self.logger.exception(e)
                self.logger.warning("Ignoring the previous error and continuing processing.")
                # raise Exception(e)

        else:
            raise ValueError("Handler received unrecognizable data.")

    async def _handle_sent_article(self, ws_struct: dict):
        self.logger.debug("Mapping BP7 to NNTP fields")

        # map BP7 to NNTP fields MAPPING
        sender: str = self._bp7sender_to_nntpfrom(ws_struct["src"])
        self.logger.debug(f"      Sender: {ws_struct['src']} -> {sender}")

        group_name: str = ws_struct["dst"].replace("dtn://", "").replace("//", "").split("/")[0]
        self.logger.debug(f"  Group Name: {ws_struct['dst']} -> {group_name}")

        dt: datetime = from_dtn_timestamp(int(ws_struct["bid"].rsplit(sep="-", maxsplit=2)[-2]))
        self.logger.debug(f"    Datetime: {ws_struct['bid']} -> {dt}")

        msg_id: str = _bundleid_to_messageid(ws_struct["bid"])
        self.logger.debug(f"  Message ID: {ws_struct['bid']} -> {msg_id}")

        msg_data: dict = cbor2.loads(ws_struct["data"])

        self.logger.debug(f"Creating article entry for {msg_id} in newsgroup DB")
        article_group = await Newsgroup.get_or_none(name=group_name)
        # TODO: Error handling in case group does not exist

        try:
            msg: Message = await Message.create(
                newsgroup=article_group,
                from_=sender,
                subject=msg_data["subject"],
                created_at=dt,
                message_id=msg_id,
                body=msg_data["body"],
                # path=f"!_handle_sent_article",
                references=msg_data["references"],
                # reply_to=msg_data["reply_to"],
                # organization=header["organization"],
                # user_agent=header["user-agent"],
            )
            self.logger.debug(f"Created new entry with id {msg.id} in articles table")
        except IntegrityError as e:
            self.logger.error(
                f"Got IntegrityError from ORM: {e.__str__()}. No new article entry was created for"
                f" article with message-id {msg_id}."
            )
        else:
            # remove message from spool HASHING
            article_hash = get_article_hash(
                source=ws_struct["src"],
                destination=ws_struct["dst"],
                data=msg_data,
            )
            self.logger.debug(
                f"Removing corresponding entry from dtnd message spool: {article_hash}"
            )
            del_cnt: int = await DTNMessage.filter(hash=article_hash).delete()
            if del_cnt == 1:
                self.logger.debug("Successful, removed spool entry")
            elif del_cnt == 0:
                self.logger.debug("Article seems to have remote origin, no spool entry removed.")
            else:
                self.logger.error(
                    f"Something went wrong deleting the entry. {del_cnt} entries were deleted"
                    " instead of 1"
                )

    def _bp7sender_to_nntpfrom(self, sender: str) -> str:
        if not sender.startswith("//") and not sender.startswith("dtn://"):
            raise ValueError(f"'{sender}' does not seem to be a valid DTN identifier")
        sender_data: List[str] = sender.replace("dtn://", "").replace("//", "").split("/")
        return f"{sender_data[-1]}@{sender_data[-2]}"

    def _nntpfrom_to_bp7sender(self, from_: str) -> str:
        if "@" not in from_:
            raise ValueError(f"'{from_}' does not seem to be a valid email address")

        node_id: str
        try:
            node_id = self._rest_client.node_id
        except AttributeError:
            self.logger.error(
                "DTNd not online yet. Using node-id from config.toml. This might produce unexpected"
                " behaviour, e.g. if DTNd uses a different node id later on."
            )
            node_id = config["dtnd"]["node_id"]
        email_name, email_domain = from_.rsplit(sep="@", maxsplit=1)
        # note: node id gets returned as string with trailing backslash: dtn://<NODEID>/
        return f"{node_id}mail/{email_domain}/{email_name}"

    @property
    def available_commands(self) -> List[str]:
        return list(self.call_dict.keys())
