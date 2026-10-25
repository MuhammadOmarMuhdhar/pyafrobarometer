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
