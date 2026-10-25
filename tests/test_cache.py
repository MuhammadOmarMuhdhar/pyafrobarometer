import threading

import pytest

from pyafrobarometer import cache
from pyafrobarometer.errors import CacheError


def test_cache_root_respects_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    assert cache.cache_root() == tmp_path


def test_is_fresh_boundaries():
    now = 1_000_000.0
    assert cache.is_fresh(now - 10, ttl=60, now=now)
    assert not cache.is_fresh(now - 60, ttl=60, now=now)


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    cache.write_state({"index_fetched_at": 1.0, "files": {}})
    assert cache.read_state()["index_fetched_at"] == 1.0


def test_lock_is_exclusive(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    started = threading.Event()
    release = threading.Event()

    def holder():
        with cache.url_lock("https://example.test/a"):
            started.set()
            release.wait(2)

    thread = threading.Thread(target=holder)
    thread.start()
    started.wait(2)
    with pytest.raises(CacheError), cache.url_lock("https://example.test/a", timeout=0.05):
        pass
    release.set()
    thread.join()


def test_clear_cache_by_round(tmp_path, monkeypatch):
    monkeypatch.setenv("PYAFROBAROMETER_CACHE_DIR", str(tmp_path))
    f = cache.cache_file("files/abc-round-9.sav")
    f.write_bytes(b"x")
    m = cache.cache_file("metadata/round-9.json")
    m.write_text("{}")
    cache.write_state({"files": {"u": {"path": str(f), "round": 9}}})
    cache.clear_cache(9)
    assert not f.exists() and not m.exists()
    assert cache.read_state()["files"] == {}
