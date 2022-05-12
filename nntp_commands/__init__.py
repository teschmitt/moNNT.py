from logger import global_logger

logger = global_logger(__name__)


from nntp_commands import (  # noqa: E402
    article,
    capabilities,
    group,
    list,
    mode,
    quit_,
    xover,
)

call_dict = {
    "article": article.do_article,
    "capabilities": capabilities.do_capabilities,
    "group": group.do_group,
    "list": list.do_list,
    "mode": mode.do_mode,
    "over": xover.do_xover,
    "quit": quit_.do_quit,
    "xover": xover.do_xover,
}
