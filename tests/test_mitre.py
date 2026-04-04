"""Tests for the MITRE ATT&CK mapper."""

import pytest

from flipperforge.mitre.mapper import MitreMapper


@pytest.fixture
def mapper():
    """Return a MitreMapper loaded from the default data file."""
    return MitreMapper()


def test_lookup_known_technique(mapper):
    """Looking up a known technique ID should return its full record."""
    result = mapper.lookup("T1082")
    assert result is not None
    assert result["id"] == "T1082"
    assert result["name"] == "System Information Discovery"
    assert result["tactic"] == "discovery"
    assert result["parent"] is None


def test_lookup_subtechnique_with_parent(mapper):
    """Subtechniques should include the parent field."""
    result = mapper.lookup("T1059.001")
    assert result is not None
    assert result["id"] == "T1059.001"
    assert result["name"] == "PowerShell"
    assert result["parent"] == "T1059"


def test_lookup_unknown_returns_none(mapper):
    """An unknown technique ID should return None."""
    assert mapper.lookup("T9999") is None


def test_get_by_tactic_returns_correct_techniques(mapper):
    """Filtering by tactic should return only matching techniques."""
    discovery = mapper.get_by_tactic("discovery")
    ids = {t["id"] for t in discovery}
    assert ids == {"T1082", "T1046"}


def test_get_by_tactic_empty(mapper):
    """A tactic with no techniques should return an empty list."""
    assert mapper.get_by_tactic("nonexistent-tactic") == []


def test_all_tactics_returns_expected_set(mapper):
    """all_tactics should return every unique tactic, sorted."""
    tactics = mapper.all_tactics()
    expected = sorted([
        "credential-access",
        "discovery",
        "execution",
        "exfiltration",
        "persistence",
    ])
    assert tactics == expected
