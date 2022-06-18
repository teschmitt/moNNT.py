from datetime import datetime

from status_codes import StatusCodes


async def do_date(_) -> str:
    """
    7.1.1.  Usage

        Indicating capability: READER

    Syntax
        DATE

    Responses
        111 yyyymmddhhmmss    Server date and time

    Parameters
        yyyymmddhhmmss    Current UTC date and time on server
    """

    return StatusCodes.STATUS_DATE.substitute(date=datetime.utcnow().strftime("%Y%m%d%H%M%S"))
