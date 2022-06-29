import asyncio
import time
from threading import Thread
from typing import Optional

import cbor2
from py_dtn7 import DTNRESTClient, DTNWSClient, from_dtn_timestamp
from tortoise import Tortoise, run_async

from backend.dtn7sqlite import get_all_newsgroups, get_all_spooled_messages
from backend.dtn7sqlite.save import send_to_dtnd, ws_handler
from backend.dtn7sqlite.utils import get_rest
from logger import global_logger
from models import Message, Newsgroup
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


async def send_all(msgs: list[dict], server: AsyncTCPServer):
    await asyncio.gather(
        *(
            send_to_dtnd(
                dtn_args={
                    "destination": msg["destination"],
                    "source": msg["source"],
                    "delivery_notification": msg["delivery_notification"],
                    "lifetime": msg["lifetime"],
                },
                dtn_payload=msg["data"],
                hash=msg["hash"],
                server_state=server,
            )
            for msg in msgs
        )
    )


async def ingest_all_from_dtnd() -> None:
    logger.debug("Ingesting all newsgroup bundles in DTNd bundle store.")

    all_groups: list[str]
    rest: Optional[DTNRESTClient]
    all_groups, rest = await asyncio.gather(get_all_newsgroups(), get_rest())
    logger.debug(f"Found {len(all_groups)} active newsgroups on this server.")

    if rest is None:
        return

    all_bundles: filter = filter(
        lambda b: b.destination.replace("dtn://", "").replace("//", "").replace("/~news", "")
        in all_groups,
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
            logger.debug(f"Created new newsgroup article {msg_id} in newsgroup '{group.name}'.")
        else:
            logger.debug(f"Article {msg_id} already present in newsgroup '{group.name}'.")


def deliver_spool(server: AsyncTCPServer):
    logger.debug("Getting spooled msgs")
    msgs: list[dict] = asyncio.new_event_loop().run_until_complete(get_all_spooled_messages())

    # exponential backoff again:
    retries: int = 0
    initial_wait: float = 0.1
    while not server.backend.running:
        logger.debug(
            f"WebSocket backend not started, waiting for {(retries ** 2) * initial_wait} seconds"
        )
        time.sleep((retries**2) * initial_wait)
        retries += 1

    asyncio.run(send_all(msgs=msgs, server=server))
    asyncio.run(ingest_all_from_dtnd())


def reconnect_handler(server: AsyncTCPServer):
    # TODO: put all of this in settings:
    retries: int = 0
    initial_wait: float = 0.1
    max_retries: int = 20
    reconn_pause: int = 300
    while not server.terminated and retries <= max_retries:
        # naive exponential backoff implementation
        time.sleep((retries**2) * initial_wait)
        # register and subscribe to all newsgroup endpoints
        try:
            # TODO: add args for port and host from settings here:
            rest = asyncio.run(get_rest())
            if rest is None:
                return
            asyncio.new_event_loop().run_until_complete(register_all_groups(client=rest))
            ws_client = DTNWSClient(
                callback=ws_handler, endpoints=filter(lambda eid: "/~news" in eid, rest.endpoints)
            )
            server.backend = ws_client
        except Exception as e:
            # requests is kind of stingy raising errors ... I was not able to catch a MaxRetries or
            # ConnectionError so for now we'll just catch all exceptions and get on with our lives.
            retries += 1
            logger.warning(e)
            if retries <= max_retries:
                logger.warning(
                    "Connection to DTNd not possible, retrying after"
                    f" {(retries ** 2) * initial_wait} seconds."
                )
            else:
                logger.error(
                    "DTNd seems permanently down. Articles will be saved to spool and sent upon"
                    f" reconnection. Reconnection attempts paused for {reconn_pause} seconds."
                )
                time.sleep(reconn_pause)
                retries = 0
                logger.info("Restarting reconnection attempts with DTNd.")
            continue

        retries = 0
        dlv_spool: Thread = Thread(target=deliver_spool, kwargs={"server": server})
        dlv_spool.daemon = True
        dlv_spool.start()
        ws_client.start_client()
        # this will run only when start_client() returns/connection is lost.
        dlv_spool.join()  # we want to stay tidy, even if this might be superfluous
        ws_client.stop_client()

    logger.info("Permanently stopped backend (WebSocket Client)")


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

    asyncio.run(ingest_all_from_dtnd())

    """
    --------------------------------------------------------------------------------------------------------------------
    This is where the not so clean code ends
    """

    loop.run_until_complete(nntp_server.start_serving())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Received Ctrl-C, stopping server")
        nntp_server.stop_serving()

    reconn_task.join()
