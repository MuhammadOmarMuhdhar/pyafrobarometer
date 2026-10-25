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
