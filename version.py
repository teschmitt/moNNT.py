import os
import re
from pathlib import Path


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
