import asyncio
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Union

import cbor2
from cbor2 import CBORDecodeEOF
from py_dtn7 import from_dtn_timestamp

from models import Message, Newsgroup
from settings import settings

if TYPE_CHECKING:
    from nntp_server import AsyncTCPServer


async def save_article(server_state: "AsyncTCPServer") -> None:
    # TODO: support cross posting to multiple newsgroups
    #       this entails setting up a M2M relationship between message and newsgroup
    #       https://kb.iu.edu/d/affn
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
        "from": header["from"],
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
        # TODO: get lifetime, destination settings from settings:
        # server_state.dtn_rest_client.send(
        #     payload=dtn_payload, destination=f"dtn://{group_name}/~news"
        # )
        server_state.dtn_ws_client.send_data(
            destination=f"dtn://{group_name}/~news",
            data=cbor2.dumps(dtn_payload),
            delivery_notification=False,
            lifetime=24 * 3600 * 1000,
        )
    except Exception as e:  # noqa E722
        # TODO: do some error handling here
        pass

    # self.logger.info(f"added article {article} to DB")


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
    print(f"Hello from {__name__}")
    print(f"Data: {ws_data}")
    if isinstance(ws_data, str):
        # probably a status code, so check if it's an error that should be logged
        if ws_data.startswith("4") or ws_data.startswith("5"):
            # TODO: log error
            pass
    elif isinstance(ws_data, bytes):
        try:
            ws_dict: dict = cbor2.loads(ws_data)
            print(ws_dict)
        except (CBORDecodeEOF, MemoryError) as e:
            raise RuntimeError(
                "Something went wrong decoding a CBOR data object. Any intended save operation "
                f"will fail on account of this error: {e}"
            )
        try:
            # map BP7 to NNTP fields
            group: str = ws_dict["dst"].replace("dtn://", "").replace("//", "").split("/")[0]
            node_id, ts_str, seq_str = (
                ws_dict["bid"].replace("dtn://", "").replace("/", "").split("-")
            )
            dt: datetime = from_dtn_timestamp(int(ts_str))
            msg_id: str = f"<{ts_str}-{seq_str}@{node_id}.dtn>"

            msg_data: dict = cbor2.loads(ws_dict["data"])

            asyncio.new_event_loop().run_until_complete(
                create_message(dt=dt, group_name=group, msg_data=msg_data, msg_id=msg_id)
            )
        except Exception as e:  # noqa E722
            # TODO: do some error handling here
            raise Exception(e)

    else:
        raise ValueError("Handler received unrecognizable data.")


async def create_message(dt, group_name, msg_data, msg_id):
    group = await Newsgroup.get_or_none(name=group_name)
    await Message.create(
        newsgroup=group,
        from_=msg_data["from"],
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
