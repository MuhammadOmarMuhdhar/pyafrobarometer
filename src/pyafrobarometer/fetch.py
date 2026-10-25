"""HTTP fetching, retries, and atomic streamed downloads."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from pyafrobarometer import __version__, cache
from pyafrobarometer.errors import DownloadError

DEFAULT_CONTENT_TYPES = (
    "application/zip",
    "application/x-spss-sav",
    "application/octet-stream",
    "application/pdf",
)

_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_ALLOWED_HOST = "www.afrobarometer.org"


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    sha256: str
    size: int
    content_type: str


def _user_agent() -> str:
    return f"pyafrobarometer/{__version__} (+https://github.com/pyafrobarometer/pyafrobarometer)"


def _new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": _user_agent()})
    return session


def _require_https(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise DownloadError(f"Refusing non-HTTPS URL: {url}")
    if parsed.hostname != _ALLOWED_HOST:
        raise DownloadError(f"Refusing URL outside {_ALLOWED_HOST}: {url}")


def _backoff_seconds(attempt: int) -> float:
    value = 0.5 * (2.0**attempt)
    return min(value, 2.0)


def _retry_delay(response: requests.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            pass
    return _backoff_seconds(attempt)


def http_get(url: str, *, timeout: float = 60.0, retries: int = 3) -> requests.Response:
    _require_https(url)
    session = _new_session()
    last_error: Exception | None = None
    attempts = max(1, retries)
    for attempt in range(attempts):
        try:
            response = session.get(url, timeout=timeout, stream=True, allow_redirects=True)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            time.sleep(_backoff_seconds(attempt))
            continue
        try:
            _require_https(response.url or url)
            if response.status_code >= 400:
                if response.status_code in _RETRY_STATUSES and attempt + 1 < attempts:
                    time.sleep(_retry_delay(response, attempt))
                    response.close()
                    continue
                response.close()
                raise DownloadError(f"HTTP {response.status_code} for {url}")
        except Exception:
            if response.status_code < 400:
                response.close()
            raise
        return response
    raise DownloadError(f"Could not fetch {url}: {last_error}")


def http_head(url: str, *, timeout: float = 30.0) -> requests.Response:
    _require_https(url)
    session = _new_session()
    try:
        return session.head(url, timeout=timeout, allow_redirects=True)
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise DownloadError(f"Could not reach {url}: {exc}") from exc


def fetch_text(url: str, *, timeout: float = 60.0) -> str:
    response = http_get(url, timeout=timeout)
    try:
        return response.text
    finally:
        response.close()


def _content_type(response: requests.Response) -> str:
    return response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()


def download(
    url: str,
    dest: Path,
    *,
    expected_types: tuple[str, ...] | None = None,
    timeout: float = 60.0,
    retries: int = 3,
) -> DownloadResult:
    _require_https(url)
    allowed = expected_types or DEFAULT_CONTENT_TYPES
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")

    with cache.url_lock(url):
        try:
            response = http_get(url, timeout=timeout, retries=retries)
            try:
                content_type = _content_type(response)
                if content_type and content_type not in allowed:
                    raise DownloadError(
                        f"Unexpected Content-Type {content_type!r} for {url}; "
                        f"expected one of {', '.join(allowed)}"
                    )
                digest = hashlib.sha256()
                size = 0
                with part.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
            finally:
                response.close()
            os.replace(part, dest)
        except DownloadError:
            part.unlink(missing_ok=True)
            raise
        except (OSError, requests.RequestException) as exc:
            part.unlink(missing_ok=True)
            raise DownloadError(f"Could not download {url}: {exc}") from exc

    return DownloadResult(path=dest, sha256=digest.hexdigest(), size=size, content_type=content_type)
