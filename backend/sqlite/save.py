import uuid
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, DefaultDict

from dateutil.parser import parse as date_parse

from config import server_config
from models import Message, Newsgroup

if TYPE_CHECKING:
    from nntp_server import AsyncNNTPServer


async def save_article(server_state: "AsyncNNTPServer") -> None:
    # TODO: support cross posting to multiple newsgroups
    #       this entails setting up a M2M relationship between message and newsgroup
    #       https://kb.iu.edu/d/affn
    header: DefaultDict[str] = defaultdict(str)
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
    dt: datetime = date_parse(header["date"]) if len(header["date"]) > 0 else datetime.utcnow()

    # some cleaning up:
    header["references"].replace("\t", "")

    try:
        await Message.create(
            newsgroup=group,
            from_=header["from"],
            subject=header["subject"],
            created_at=dt,
            message_id=f"<{uuid.uuid4()}@{server_config['domain_name']}>",
            body=body,
            path=f"!{server_config['domain_name']}",
            references=header["references"],
            reply_to=header["reply-to"],
            organization=header["organization"],
            user_agent=header["user-agent"],
        )
    except Exception as e:  # noqa E722
        # TODO: do some error handling here
        raise Exception(e)

    group_name: str = group.name
    dtn_payload: dict = {
        "newsgroup": group_name,
        "from": header["from"],
        "subject": header["subject"],
        "created_at": dt.isoformat(),
        "message_id": f"<{uuid.uuid4()}@{server_config['domain_name']}>",
        "body": body,
        "path": f"!{server_config['domain_name']}",
        "references": header["references"],
        "reply_to": header["reply-to"],
        "organization": header["organization"],
        "user_agent": header["user-agent"],
    }

    try:
        # TODO: get lifetime, destination settings from settings:
        server_state.dtn_client.send(payload=dtn_payload, destination=f"dtn://{group_name}/~news")
    except Exception as e:  # noqa E722
        # TODO: do some error handling here
        pass

    # self.logger.info(f"added article {article} to DB")
