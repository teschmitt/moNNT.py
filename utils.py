import os
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import List

import toml

from config import server_config
from models import Article


class RangeParseStatus(Enum):
    SUCCESS = 0
    FAILURE = 1


class RangeType(Enum):
    CLOSED_RANGE = 0
    OPEN_RANGE = 1
    SINGLE_ITEM = 2


class ParsedRange:
    parse_status: RangeParseStatus = RangeParseStatus.SUCCESS
    range_type: RangeType
    start: int
    stop: int

    def __init__(self, range_str: str, max_value: int = None):
        if "-" in range_str:
            # parse range
            str_start, str_stop = range_str.split("-")
            try:
                self.start = int(str_start)
                if len(str_stop) > 0:
                    self.stop = int(str_stop)
                    self.range_type = RangeType.CLOSED_RANGE
                else:
                    if max_value is None:
                        max_value = 2**63
                    self.stop = max_value
                    self.range_type = RangeType.OPEN_RANGE
            except ValueError:
                self.parse_status = RangeParseStatus.FAILURE
        else:
            # single number
            try:
                self.start = self.stop = int(range_str)
                self.range_type = RangeType.SINGLE_ITEM
            except ValueError:
                self.parse_status = RangeParseStatus.FAILURE


def get_version() -> str:
    pyproject_path = Path(os.path.dirname(os.path.abspath(__file__))) / "pyproject.toml"
    pyproject = toml.loads(open(str(pyproject_path)).read())
    return pyproject["tool"]["poetry"]["version"]


def build_xref(article_id: int, group_name: str) -> str:
    return f"{server_config['domain_name']} {group_name}:{article_id}"


def get_bytes_len(article: Article) -> int:
    result = 0
    for val in article.__dict__.values():
        if type(val) is not bool:
            result += len(str(val).encode("utf-8"))
    return result


def get_num_lines(article: Article) -> int:
    return len(article.body.split("\n"))


def groupname_filter(groups: List[dict], pattern: str) -> filter:
    """
    A very incomplete wildmat implementation.

    :param groups: groups to filter
    :param pattern: pattern to filter with
    :return: filter object containing matching newsgroups
    """
    return filter(lambda v: fnmatch(v["name"], pattern), groups)


def get_datetime(date_str: str, time_str: str):
    year: int = int(date_str[0:4]) if len(date_str) > 6 else int(date_str[0:2])
    month: int = int(date_str[4:6]) if len(date_str) > 6 else int(date_str[2:4])
    day: int = int(date_str[6:8]) if len(date_str) > 6 else int(date_str[4:6])
    hour: int = int(time_str[:2])
    minute: int = int(time_str[2:4])
    second: int = int(time_str[4:6])
    gte_date: datetime = datetime(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
        tzinfo=timezone.utc,
    )
    return gte_date
