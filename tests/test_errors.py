import pyafrobarometer as ab


def test_error_hierarchy():
    for exc in [
        ab.CatalogError,
        ab.DownloadError,
        ab.CacheError,
        ab.NotFoundError,
        ab.HarmonizationError,
        ab.CodebookError,
    ]:
        assert issubclass(exc, ab.AfrobarometerError)
