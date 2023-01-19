import datetime
import hashlib
import os.path
import re
from typing import Any, Callable, Iterable, Optional


def local_path(path: str) -> str:
    current_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(current_dir, path))


def file_hash(filename: str) -> str:
    with open(filename, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def find(function: Callable[[Any], bool], iterable: Iterable[Any]) -> Optional[Any]:
    for item in iterable:
        if function(item):
            return item
    return None


_TIMELIMIT_REGEXP = re.compile(
    "^(?:^(?P<days>[0-9]+)-)?(?P<hours>[0-9]+)(?::(?P<minutes>[0-5]?[0-9]))?(?::(?P<seconds>[0-5]?[0-9]))?$"
)


def parse_timelimit(timelimit: str) -> datetime.timedelta:
    """Parse a SLURM timelimit/walltime string.

    Raises ValueError if parsing failed.
    """
    if timelimit == "infinite":
        return datetime.timedelta.max
    match = _TIMELIMIT_REGEXP.match(timelimit)
    if match is None:
        raise ValueError(f"Failed to parse time limit: '{timelimit}'.")
    return datetime.timedelta(
        **{k: int(v) for k, v in match.groupdict().items() if v is not None}
    )
