from logger import global_logger

logger = global_logger()


from nntp_commands import (  # noqa: E402
    article,
    capabilities,
    date,
    group,
    help,
    last,
    list,
    listgroup,
    mode,
    next,
    over,
    post,
    quit_,
)

call_dict = {
    "article": article.do_article,
    "capabilities": capabilities.do_capabilities,
    "date": date.do_date,
    "group": group.do_group,
    "help": help.do_help,
    "last": last.do_last,
    "list": list.do_list,
    "listgroup": listgroup.do_listgroup,
    "mode": mode.do_mode,
    "next": next.do_next,
    "over": over.do_over,
    "post": post.do_post,
    "quit": quit_.do_quit,
    "xover": over.do_over,
}
