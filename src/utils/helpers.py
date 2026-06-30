"""Generic helper functions used across the pipeline."""
import hashlib
from pathlib import Path
from typing import List


def list_files(directory: str, extensions: List[str]) -> List[str]:
    """Return sorted list of file paths under `directory` matching given extensions."""
    p = Path(directory)
    if not p.exists():
        return []
    files = []
    for ext in extensions:
        files.extend(p.rglob(f"*{ext}"))
    return sorted(str(f) for f in files)


def file_hash(file_path: str) -> str:
    """Return a short md5 hash of a file's contents (useful for dedupe / caching)."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
