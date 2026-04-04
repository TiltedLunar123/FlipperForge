"""MITRE ATT&CK mapper for FlipperForge payloads."""

import json
from pathlib import Path
from typing import List, Optional


_DATA_FILE = Path(__file__).parent / "attack_data.json"


class MitreMapper:
    """Loads the local ATT&CK dataset and provides lookup helpers."""

    def __init__(self, data_path: Optional[str] = None) -> None:
        path = Path(data_path) if data_path else _DATA_FILE
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._techniques: List[dict] = raw["techniques"]

    def lookup(self, technique_id: str) -> Optional[dict]:
        """Return the technique dict for a given ID, or None if not found."""
        for tech in self._techniques:
            if tech["id"] == technique_id:
                return dict(tech)
        return None

    def get_by_tactic(self, tactic: str) -> List[dict]:
        """Return all techniques that belong to the specified tactic."""
        return [dict(t) for t in self._techniques if t["tactic"] == tactic]

    def all_tactics(self) -> List[str]:
        """Return a sorted list of unique tactic names."""
        return sorted({t["tactic"] for t in self._techniques})
