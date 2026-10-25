"""Local cache paths, serialized state, TTL checks, and per-URL locks."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir

from pyafrobarometer.errors import CacheError

DEFAULT_TTL_SECONDS = 604800

_LAYOUT_DIRS = ("files", "metadata", "tmp", "index", "locks")


def cache_root() -> Path:
    override = os.environ.get("PYAFROBAROMETER_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path(user_cache_dir("pyafrobarometer"))


def cache_file(relative: str) -> Path:
    path = cache_root() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return cache_root() / "state.json"


def read_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheError(f"Could not read cache state at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CacheError(f"Cache state at {path} is not a JSON object")
    return data


def write_state(state: Mapping[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".state-", suffix=".json")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(state), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise CacheError(f"Could not write cache state at {path}: {exc}") from exc


def is_fresh(
    fetched_at: float,
    *,
    ttl: int = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> bool:
    if ttl == DEFAULT_TTL_SECONDS:
        override = os.environ.get("PYAFROBAROMETER_INDEX_TTL")
        if override:
            try:
                ttl = int(override)
            except ValueError as exc:
                raise CacheError(
                    f"PYAFROBAROMETER_INDEX_TTL must be an integer, got {override!r}"
                ) from exc
    current = time.time() if now is None else now
    return current - fetched_at < ttl


def _lock_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_file(f"locks/{digest}.lock")


@contextmanager
def url_lock(url: str, *, timeout: float = 300.0) -> Iterator[None]:
    path = _lock_path(url)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise CacheError(
                    f"Timed out after {timeout}s waiting for the download lock for {url}"
                ) from None
            time.sleep(0.05)
        except OSError as exc:
            raise CacheError(f"Could not create download lock for {url}: {exc}") from exc
        else:
            break
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        path.unlink(missing_ok=True)


def clear_cache(round_number: int | None = None) -> None:
    root = cache_root()
    state = read_state()
    files = state.get("files")
    if not isinstance(files, dict):
        files = {}

    if round_number is None:
        for name in _LAYOUT_DIRS:
            shutil.rmtree(root / name, ignore_errors=True)
        _state_path().unlink(missing_ok=True)
        return

    kept: dict[str, Any] = {}
    for url, record in files.items():
        if isinstance(record, dict) and record.get("round") == round_number:
            path = record.get("path")
            if isinstance(path, str):
                Path(path).unlink(missing_ok=True)
        else:
            kept[url] = record
    (root / "metadata" / f"round-{round_number}.json").unlink(missing_ok=True)
    state["files"] = kept
    write_state(state)
