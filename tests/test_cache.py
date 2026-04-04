"""Tests for the FlipperForge build cache."""

import os

import pytest

from flipperforge.cache import BuildCache


@pytest.fixture
def cache(tmp_path):
    """Return a BuildCache that uses a temporary directory."""
    return BuildCache(cache_dir=str(tmp_path / "cache"))


def test_save_and_load_roundtrip(cache):
    """Saving a script and meta then loading should return the same data."""
    script = "DELAY 500\nSTRING hello"
    meta = {"name": "test_payload", "version": 1}

    cache.save(script, meta)
    result = cache.load()

    assert result is not None
    assert result["script"] == script
    assert result["meta"] == meta


def test_load_empty_returns_none(cache):
    """Loading from an empty (non-existent) cache should return None."""
    assert cache.load() is None


def test_save_creates_directory(tmp_path):
    """Saving should create the cache directory if it does not exist."""
    cache_dir = tmp_path / "deep" / "nested" / "cache"
    assert not cache_dir.exists()

    cache = BuildCache(cache_dir=str(cache_dir))
    cache.save("REM test", {"ok": True})

    assert cache_dir.exists()
    assert (cache_dir / "last_build.txt").exists()
    assert (cache_dir / "last_build_meta.json").exists()


def test_clear_removes_cache(cache):
    """Clearing the cache should remove both cached files."""
    cache.save("DELAY 100", {"cleared": False})
    assert cache.load() is not None

    cache.clear()
    assert cache.load() is None
