from status_codes import StatusCodes


async def do_help(_):
    """
    7.2.1.  Usage

    This command is mandatory.

    Syntax
        HELP

    Responses
        100    Help text follows (multi-line)
    """
    return [StatusCodes.STATUS_HELPMSG, "You're on your own."]
