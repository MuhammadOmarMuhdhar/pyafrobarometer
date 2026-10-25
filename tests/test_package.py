import pyafrobarometer as ab


def test_version():
    assert ab.__version__ == "0.1.0"


def test_public_errors_are_exported():
    for name in [
        "AfrobarometerError",
        "CatalogError",
        "DownloadError",
        "CacheError",
        "NotFoundError",
        "HarmonizationError",
        "CodebookError",
    ]:
        assert hasattr(ab, name)
