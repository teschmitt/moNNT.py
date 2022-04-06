async def do_capabilities(_):
    return (
        "101 Capability list:\r\n"
        + "VERSION 2\r\n"
        + "IMPLEMENTATION SGUG-MONTTPY\r\n"
        + "LIST ACTIVE NEWSGROUPS OVERVIEW.FMT SUBSCRIPTIONS\r\n"
        + "OVER\r\n"
        + "READER\r\n"
        + "."
    )
