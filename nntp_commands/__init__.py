from logger import global_logger

logger = global_logger(__name__)


from nntp_commands import article, capabilities, group, list, mode, xover  # noqa: E402

call_dict = {
    "article": article.do_article,
    "capabilities": capabilities.do_capabilities,
    "group": group.do_group,
    "list": list.do_list,
    "mode": mode.do_mode,
    "over": xover.do_xover,
    "xover": xover.do_xover,
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
