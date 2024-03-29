from typing import TYPE_CHECKING, List, Optional, Union

from backend.dtn7sqlite.models import Article
from status_codes import StatusCodes
from utils import (
    ParsedRange,
    RangeParseStatus,
    build_xref,
    get_bytes_len,
    get_num_lines,
)

if TYPE_CHECKING:
    from client_connection import ClientConnection


async def augment_article(art: Article) -> Article:
    await art.fetch_related("newsgroup")
    return art


def get_header(art: Article, field_name: str) -> str:
    fn = field_name.lower()
    if fn == "subject":
        return art.subject
    elif fn == "from":
        return art.from_
    elif fn == "date":
        return art.created_at
    elif fn == "message-id":
        return art.message_id
    elif fn == "references":
        return art.references
    elif fn == "newsgroups":
        return art.newsgroup.name
    elif fn == ":bytes":
        return str(get_bytes_len(art))
    elif fn == ":lines":
        return str(get_num_lines(art))
    elif fn == "xref":
        try:
            return build_xref(art.id, art.newsgroup.name)
        except Exception as e:
            print(e)
            return ""
    else:
        return ""


async def do_hdr(client_conn: "ClientConnection") -> Union[List[str], str]:
    """
    8.5.1.  Usage

        Indicating capability: HDR

        Syntax
            HDR field message-id
            HDR field range
            HDR field

        Responses

        First form (message-id specified)
            225    Headers follow (multi-line)
            430    No article with that message-id

        Second form (range specified)
            225    Headers follow (multi-line)
            412    No newsgroup selected
            423    No articles in that range

        Third form (current article number used)
            225    Headers follow (multi-line)
            412    No newsgroup selected
            420    Current article number is invalid

        Parameters
            field         Name of field
            range         Number(s) of articles
            message-id    Message-id of article

    """

    tokens: List[str] = client_conn.cmd_args
    try:
        field_name: Optional[str] = tokens[0]
    except IndexError:
        return StatusCodes.ERR_CMDSYNTAXERROR

    identifier: Optional[str] = tokens[1] if len(tokens) > 1 else None
    articles: List[Article] = []
    status_str: str
    msg_id_provided: bool = False

    if identifier is not None:
        if "-" in identifier:
            if client_conn.selected_group is None:
                return StatusCodes.ERR_NOGROUPSELECTED

            parsed_range: ParsedRange = ParsedRange(range_str=identifier, max_value=2**63)
            if parsed_range.parse_status == RangeParseStatus.FAILURE:
                return StatusCodes.ERR_NOTPERFORMED
            articles = await Article.filter(
                newsgroup__name=client_conn.selected_group.name,
                id__gte=parsed_range.start,
                id__lte=parsed_range.stop,
            ).prefetch_related("newsgroup")
            if len(articles) == 0:
                return StatusCodes.ERR_NOARTICLESINRANGE

        elif "<" in identifier and ">" in identifier:
            msg_id_provided = True
            articles = [
                await Article.get_or_none(message_id=identifier).prefetch_related("newsgroup")
            ]
            if len(articles) == 0:
                return StatusCodes.ERR_NOSUCHARTICLE
    else:
        if client_conn.selected_group is None:
            return StatusCodes.ERR_NOGROUPSELECTED
        if client_conn.selected_article is None:
            return StatusCodes.ERR_NOARTICLESELECTED
        await client_conn.selected_article.fetch_related("newsgroup")
        articles = [client_conn.selected_article]

    return [StatusCodes.STATUS_HEADERS_FOLLOW] + [
        f"{0 if msg_id_provided else art.id} {get_header(art, field_name)}" for art in articles
    ]
