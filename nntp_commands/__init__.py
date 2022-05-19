from logger import global_logger

logger = global_logger()


from nntp_commands import (  # noqa: E402
    article,
    capabilities,
    date,
    group,
    hdr,
    head_body_stat,
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
    "body": head_body_stat.do_head_body_stat,
    "capabilities": capabilities.do_capabilities,
    "date": date.do_date,
    "group": group.do_group,
    "hdr": hdr.do_hdr,
    "head": head_body_stat.do_head_body_stat,
    "help": help.do_help,
    "last": last.do_last,
    "list": list.do_list,
    "listgroup": listgroup.do_listgroup,
    "mode": mode.do_mode,
    "next": next.do_next,
    "over": over.do_over,
    "post": post.do_post,
    "quit": quit_.do_quit,
    "stat": head_body_stat.do_head_body_stat,
    "xhdr": hdr.do_hdr,
    "xover": over.do_over,
}
