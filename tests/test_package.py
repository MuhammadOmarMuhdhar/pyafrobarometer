import pyafrobarometer as ab


def test_version():
    assert ab.__version__ == "0.1.2"


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


def test_question_apis_are_exported():
    assert hasattr(ab, "questions")
    assert hasattr(ab, "question")
    assert "questions" in ab.__all__
    assert "question" in ab.__all__
