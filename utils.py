import os
import re
from datetime import datetime, timezone
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path

from models import Message
from settings import settings


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


def get_version():
    # it is astonishingly hard to pry the version number out of pyproject.toml
    version = "[unidentified -- either pyproject.toml is missing or configured incorrectly]"
    compiled_version_regex = re.compile(r"\s*version\s*=\s*[\"']\s*([-.\w]{3,})\s*[\"']\s*")
    pyproject = Path(os.path.dirname(os.path.abspath(__file__))) / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open(mode="r") as fh:
            for line in fh:
                ver = compiled_version_regex.search(line)
                if ver is not None:
                    version = ver.group(1).strip()
                    break
    return version


def build_xref(article_id: int, group_name: str) -> str:
    return f"{settings.DOMAIN_NAME} {group_name}:{article_id}"


def get_bytes_len(article: Message) -> int:
    result = 0
    for val in article.__dict__.values():
        if type(val) is not bool:
            result += len(str(val).encode("utf-8"))
    return result


def get_num_lines(article: Message) -> int:
    return len(article.body.split("\n"))


def groupname_filter(groups: list[dict], pattern: str) -> filter:
    return filter(lambda v: fnmatch(v["name"], pattern), groups)


def get_datetime(tokens):
    year: int = int(tokens[0][0:4]) if len(tokens[0]) > 6 else int(tokens[0][0:2])
    month: int = int(tokens[0][4:6]) if len(tokens[0]) > 6 else int(tokens[0][2:4])
    day: int = int(tokens[0][6:8]) if len(tokens[0]) > 6 else int(tokens[0][4:6])
    hour: int = int(tokens[1][:2])
    minute: int = int(tokens[0][2:4])
    second: int = int(tokens[0][4:6])
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
