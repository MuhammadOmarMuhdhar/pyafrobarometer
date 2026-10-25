import importlib
from pathlib import Path

import pytest

codebook = importlib.import_module("pyafrobarometer.codebook")
from pyafrobarometer.errors import CodebookError


def test_extract_text_without_dependency(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(
        CodebookError, match="pip install pyafrobarometer\\[codebook\\]"
    ):
        codebook.extract_text(Path("x.pdf"))


def test_extract_text_uses_pypdf(monkeypatch):
    class Page:
        def extract_text(self):
            return "hello"

    class Reader:
        def __init__(self, path):
            self.pages = [Page()]

    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", Reader)
    assert codebook.extract_text(Path("x.pdf")) == "hello"


def test_missing_codebook_url_does_not_fetch_dataset(monkeypatch):
    from pyafrobarometer.catalog import CatalogEntry

    entry = CatalogEntry(
        kind="merged",
        round=9,
        country=None,
        year=2023,
        language="en",
        data_url="https://www.afrobarometer.org/x.sav",
        codebook_url=None,
        page_url="https://www.afrobarometer.org/x.sav",
        filename="x.sav",
        size_bytes=None,
    )

    def fail(*args, **kwargs):
        raise AssertionError("network")

    monkeypatch.setattr(codebook.fetch, "fetch_text", fail)
    with pytest.raises(CodebookError, match="codebook"):
        codebook.get_codebook(entry)


def test_get_codebook_follows_resource_page(monkeypatch, tmp_path):
    from pyafrobarometer.catalog import CatalogEntry
    from pyafrobarometer.fetch import DownloadResult

    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    entry = CatalogEntry(
        kind="merged",
        round=7,
        country=None,
        year=2019,
        language="en",
        data_url="https://www.afrobarometer.org/x.sav",
        codebook_url="https://www.afrobarometer.org/survey-resource/merged-round-7-codebook-34-countries-2020/",
        page_url="https://www.afrobarometer.org/data/merged-data/",
        filename="x.sav",
        size_bytes=None,
    )
    page = (
        '<a href="https://www.afrobarometer.org/wp-content/uploads/2023/02/'
        'r7_merged.codebook_final_14dec20-1-1.pdf">Merged Round 7 codebook</a>'
    )

    downloaded = []

    def fake_download(url, dest, **kwargs):
        downloaded.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"%PDF")
        return DownloadResult(dest, "x", 4, "application/pdf")

    monkeypatch.setattr(codebook.fetch, "fetch_text", lambda *a, **k: page)
    monkeypatch.setattr(codebook.fetch, "download", fake_download)
    path = codebook.get_codebook(entry)
    assert path.read_bytes() == b"%PDF"
    assert downloaded and downloaded[0].endswith(".pdf")
