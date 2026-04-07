"""Tests for the payload library manager."""

import pytest

from flipperforge.library.manager import PayloadLibrary


@pytest.fixture
def library(tmp_path):
    """Create a PayloadLibrary using a temporary directory."""
    return PayloadLibrary(payloads_dir=str(tmp_path))


def test_save_and_list(library, tmp_path):
    """Saving a payload should make it appear in list_all."""
    library.save("test_payload", "STRING hello", {"tactic": "execution"})

    results = library.list_all()
    assert len(results) == 1
    assert results[0]["name"] == "test_payload"
    assert results[0]["meta"]["tactic"] == "execution"
    assert "created_at" in results[0]["meta"]

    # Verify files exist on disk
    assert (tmp_path / "test_payload.txt").exists()
    assert (tmp_path / "test_payload.meta.json").exists()


def test_load(library):
    """Loading a saved payload should return its script and meta."""
    script = "DELAY 500\nSTRING hello world"
    meta = {"tactic": "initial-access", "author": "tester"}
    library.save("my_payload", script, meta)

    result = library.load("my_payload")
    assert result is not None
    assert result["script"] == script
    assert result["meta"]["tactic"] == "initial-access"
    assert result["meta"]["author"] == "tester"
    assert "created_at" in result["meta"]


def test_load_not_found(library):
    """Loading a nonexistent payload should return None."""
    result = library.load("does_not_exist")
    assert result is None


def test_delete(library):
    """Deleting a saved payload should remove it and return True."""
    library.save("deleteme", "REM test", {"tactic": "persistence"})
    assert library.delete("deleteme") is True

    # Verify it is gone
    assert library.load("deleteme") is None
    assert library.list_all() == []


def test_delete_not_found(library):
    """Deleting a nonexistent payload should return False."""
    assert library.delete("no_such_payload") is False


def test_search_by_name(library):
    """Search should match payload names case-insensitively."""
    library.save("WiFi_Deauth", "REM deauth", {"tactic": "discovery"})
    library.save("usb_drop", "REM drop", {"tactic": "initial-access"})

    results = library.search("wifi")
    assert len(results) == 1
    assert results[0]["name"] == "WiFi_Deauth"


def test_search_by_tactic(library):
    """Search should match metadata values case-insensitively."""
    library.save("payload_a", "REM a", {"tactic": "Credential Access"})
    library.save("payload_b", "REM b", {"tactic": "Execution"})

    results = library.search("credential")
    assert len(results) == 1
    assert results[0]["name"] == "payload_a"
    assert results[0]["meta"]["tactic"] == "Credential Access"


# -- Path traversal prevention --


def test_save_rejects_path_traversal(library):
    """Names with path separators should be rejected."""
    with pytest.raises(ValueError, match="Invalid payload name"):
        library.save("../../etc/passwd", "REM bad", {})


def test_save_rejects_dots(library):
    """Names with dots should be rejected."""
    with pytest.raises(ValueError, match="Invalid payload name"):
        library.save("foo.bar", "REM bad", {})


def test_save_rejects_spaces(library):
    """Names with spaces should be rejected."""
    with pytest.raises(ValueError, match="Invalid payload name"):
        library.save("foo bar", "REM bad", {})


def test_save_rejects_empty(library):
    """Empty names should be rejected."""
    with pytest.raises(ValueError, match="Invalid payload name"):
        library.save("", "REM bad", {})


def test_save_accepts_valid_names(library):
    """Valid names with letters, digits, hyphens, underscores should work."""
    library.save("my-payload_v2", "REM ok", {})
    result = library.load("my-payload_v2")
    assert result is not None


# -- Corrupted JSON handling --


def test_load_corrupted_json(library, tmp_path):
    """Loading a payload with corrupted meta JSON should return empty meta."""
    (tmp_path / "corrupt.txt").write_text("STRING hello", encoding="utf-8")
    (tmp_path / "corrupt.meta.json").write_text("NOT JSON{{{", encoding="utf-8")

    result = library.load("corrupt")
    assert result is not None
    assert result["script"] == "STRING hello"
    assert result["meta"] == {}


def test_list_all_corrupted_json(library, tmp_path):
    """list_all should handle corrupted meta JSON gracefully."""
    (tmp_path / "bad.txt").write_text("REM bad", encoding="utf-8")
    (tmp_path / "bad.meta.json").write_text("{broken}", encoding="utf-8")

    results = library.list_all()
    assert len(results) == 1
    assert results[0]["name"] == "bad"
    assert results[0]["meta"] == {}
