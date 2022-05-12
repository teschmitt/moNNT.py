async def do_capabilities(_):
    return [
        "101 Capability list:",
        "VERSION 2",
        "IMPLEMENTATION SGUG-MONTTPY",
        "LIST ACTIVE NEWSGROUPS OVERVIEW.FMT SUBSCRIPTIONS",
        "OVER MSGID",
        "READER",
    ]
