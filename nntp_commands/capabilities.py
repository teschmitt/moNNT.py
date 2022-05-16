async def do_capabilities(_):
    """
    5.2.1.  Usage

        This command is mandatory.

        Syntax
            CAPABILITIES [keyword]

        Responses
            101    Capability list follows (multi-line)
    """

    return [
        "101 Capability list:",
        "VERSION 2",
        "IMPLEMENTATION MONTTPY",
        "LIST ACTIVE NEWSGROUPS OVERVIEW.FMT SUBSCRIPTIONS",
        "OVER MSGID",
        "READER",
    ]
