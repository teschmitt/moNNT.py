import asyncio
import re
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Union

import cbor2
from cbor2 import CBORDecodeEOF
from py_dtn7 import from_dtn_timestamp

from backend.dtn7sqlite.config import config
from backend.dtn7sqlite.utils import get_rest, get_article_hash
from logger import global_logger
from models import DTNMessage, Message, Newsgroup
from settings import settings

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


async def save_article(server_state: "AsyncTCPServer") -> None:
    # TODO: support cross posting to multiple newsgroups
    #       this entails setting up a M2M relationship between message and newsgroup
    #       https://kb.iu.edu/d/affn
    logger = global_logger()
    logger.debug("Sending article to DTNd and local DTN message spool")
    header: defaultdict[str] = defaultdict(str)
    line: str = server_state.article_buffer.pop(0)
    field_name: str = ""
    field_value: str
    while len(line) != 0:
        try:
            if ":" in line:
                field_name, field_value = map(lambda s: s.strip(), line.split(":", 1))
                field_name = field_name.strip().lower()
                header[field_name] = field_value.strip()
            elif len(field_name) > 0:
                header[field_name] = f"{header[field_name]} {line}"
        except ValueError:
            # something clients send fishy headers … we'll just ignore them.
            pass
        line = server_state.article_buffer.pop(0)

    group = await Newsgroup.get_or_none(name=header["newsgroups"])
    # TODO: Error handling when newsgroup is not in DB

    # we've popped off the complete header, body is just the joined rest
    body: str = "\n".join(server_state.article_buffer)
    # dt: datetime = date_parse(header["date"]) if len(header["date"]) > 0 else datetime.utcnow()

    # some cleaning up:
    header["references"].replace("\t", "")

    group_name: str = group.name
    dtn_payload: dict = {
        # "newsgroup": group_name,
        # "from": header["from"],
        "subject": header["subject"],
        # "created_at": dt.isoformat(),
        # "message_id": f"<{uuid.uuid4()}@{settings.DOMAIN_NAME}>",
        "body": body,
        # "path": f"!{settings.DOMAIN_NAME}",
        "references": header["references"],
        "reply_to": header["reply-to"],
        # "organization": header["organization"],
        # "user_agent": header["user-agent"],
    }

    try:
        sender_email: str = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", header["from"]).group(0)
    except AttributeError as e:
        logger.warning(f"Email address could ot be parsed: {e}")
        sender_email: str = "not-recognized@email-address.net"
    name_email, domain_email = sender_email.split("@")
    # TODO: get lifetime, destination settings from settings:
    dtn_args: dict = {
        "source": f"dtn://{domain_email}/mail/{name_email}",
        "destination": f"dtn://{group_name}/~news",
        "delivery_notification": config["bundles"]["deliv_notification"],
        "lifetime": config["bundles"]["lifetime"],
    }

    message_hash = get_article_hash(
        source=dtn_args["source"], destination=dtn_args["destination"], data=dtn_payload
    )
    logger.debug(f"Got message hash: {message_hash}")

    dtn_msg: DTNMessage = await DTNMessage.create(**dtn_args, data=dtn_payload, hash=message_hash)
    logger.debug(f"Created entry in DTNd message spool with id {dtn_msg.id}")

    await send_to_dtnd(
        dtn_args=dtn_args, dtn_payload=dtn_payload, hash=message_hash, server_state=server_state
    )


async def send_to_dtnd(
    dtn_args: dict, dtn_payload: dict, hash: str, server_state: "AsyncTCPServer"
):
    # register the source endpoint so dtnd knows we want to keep the message in memory
    logger = global_logger()
    logger.debug(f"Registering message source as endpoint: {dtn_args['source']}")
    try:
        rest = await get_rest()
        rest.register(endpoint=dtn_args["source"])
        logger.debug(f"Sending article to DTNd with {dtn_args}")
        server_state.backend.send_data(**dtn_args, data=cbor2.dumps(dtn_payload))
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


def ws_handler(ws_data: Union[str | bytes]) -> None:
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


async def handle_sent_article(ws_struct: dict):
    logger = global_logger()
    logger.debug("Mapping BP7 to NNTP fields")

    # map BP7 to NNTP fields
    sender_data: list[str] = ws_struct["src"].replace("dtn://", "").replace("//", "").split("/")
    sender: str = f"{sender_data[-1]}@{sender_data[0]}"

    group_name: str = ws_struct["dst"].replace("dtn://", "").replace("//", "").split("/")[0]

    bid_data: list[str] = ws_struct["bid"].split("-")
    src_like: str = bid_data[0].replace("dtn://", "").replace("/", "-")
    seq_str: str = bid_data[-1]
    ts_str: str = bid_data[-2]

    dt: datetime = from_dtn_timestamp(int(ts_str))
    msg_id: str = f"<{ts_str}-{seq_str}@{src_like}.dtn>"

    msg_data: dict = cbor2.loads(ws_struct["data"])

    logger.debug("Creating article entry in newsgroup DB")
    group = await Newsgroup.get_or_none(name=group_name)
    # TODO: Error handling in case group does not exist
    msg: Message = await Message.create(
        newsgroup=group,
        from_=sender,
        subject=msg_data["subject"],
        created_at=dt,
        message_id=msg_id,
        body=msg_data["body"],
        path=f"!{settings.DOMAIN_NAME}",
        references=msg_data["references"],
        reply_to=msg_data["reply_to"],
        # organization=header["organization"],
        # user_agent=header["user-agent"],
    )
    logger.debug(f"Created new entry with id {msg.id} in articles table")

    # remove message from spool
    article_hash = get_article_hash(
        source=ws_struct["src"],
        destination=ws_struct["dst"],
        data=msg_data,
    )
    logger.debug(f"Removing corresponding entry from dtnd message spool: {article_hash}")
    del_cnt: int = await DTNMessage.filter(hash=article_hash).delete()
    if del_cnt == 1:
        logger.debug("Successful, removed spool entry")
    else:
        logger.error(
            f"Something went wrong deleting the entry. {del_cnt} entries were deleted instead of 1"
        )
