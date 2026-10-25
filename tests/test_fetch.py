import hashlib

import pytest
import requests

from pyafrobarometer import fetch
from pyafrobarometer.errors import DownloadError

URL = "https://www.afrobarometer.org"


def response(status=200, content=b"", headers=None, url=URL + "/a"):
    resp = requests.Response()
    resp.status_code = status
    resp._content = content
    resp._content_consumed = True
    resp.close = lambda: None  # type: ignore[method-assign]
    resp.headers.update(headers or {})
    resp.url = url
    return resp


def install(monkeypatch, method, items):
    calls = []

    def fake(self, url, **kwargs):
        calls.append(url)
        item = items[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(requests.Session, method, fake)
    return calls


def test_download_writes_and_hashes(tmp_path, monkeypatch):
    body = b"PK\x03\x04fake"
    install(
        monkeypatch,
        "get",
        [response(200, body, {"content-type": "application/zip"})],
    )
    dest = tmp_path / "a.zip"
    result = fetch.download(URL + "/a.zip", dest, expected_types=("application/zip",))
    assert dest.read_bytes() == body
    assert result.sha256 == hashlib.sha256(body).hexdigest() and result.size == len(body)


def test_download_retries_5xx(tmp_path, monkeypatch):
    calls = install(
        monkeypatch,
        "get",
        [
            response(503),
            response(200, b"x", {"content-type": "application/x-spss-sav"}),
        ],
    )
    result = fetch.download(URL + "/a.sav", tmp_path / "a.sav")
    assert len(calls) == 2 and result.size == 1


def test_download_rejects_wrong_content_type(tmp_path, monkeypatch):
    install(
        monkeypatch,
        "get",
        [response(200, b"<html>", {"content-type": "text/html"})],
    )
    with pytest.raises(DownloadError):
        fetch.download(URL + "/x", tmp_path / "x", expected_types=("application/zip",))


def test_download_rejects_non_https(tmp_path):
    with pytest.raises(DownloadError):
        fetch.download("http://www.afrobarometer.org/a", tmp_path / "a")


def test_http_head_returns_status(monkeypatch):
    install(monkeypatch, "head", [response(200)])
    assert fetch.http_head(URL + "/a.sav").status_code == 200


def test_download_accepts_missing_content_type(tmp_path, monkeypatch):
    install(monkeypatch, "get", [response(200, b"x", {})])
    result = fetch.download(URL + "/a.sav", tmp_path / "a.sav")
    assert result.size == 1
