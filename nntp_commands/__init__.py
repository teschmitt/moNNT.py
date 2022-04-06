from logger import global_logger

logger = global_logger(__name__)

from nntp_commands.article import do_article
from nntp_commands.capabilities import do_capabilities
from nntp_commands.group import do_group
from nntp_commands.list import do_list
from nntp_commands.mode import do_mode
from nntp_commands.xover import do_xover

call_dict = {
    "article": do_article,
    "capabilities": do_capabilities,
    "group": do_group,
    "list": do_list,
    "mode": do_mode,
    "over": do_xover,
    "xover": do_xover
}

commands = (
    "article",
    "body",
    "head",
    "stat",
    "group",
    "list",
    "post",
    "help",
    "last",
    "newgroups",
    "newnews",
    "next",
    "quit",
    "mode",
    "xover",
    "xpat",
    "listgroup",
    "xgtitle",
    "xhdr",
    "xgtitle",
    "xhdr",
    "slave",
    "date",
    "ihave",
    "over",
    "hdr",
    "authinfo",
    "capabilities",
    "xrover",
    "xversion",
)
