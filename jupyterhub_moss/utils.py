import hashlib
import os.path
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
