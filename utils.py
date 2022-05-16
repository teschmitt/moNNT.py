import os
import re
from enum import Enum
from pathlib import Path


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
