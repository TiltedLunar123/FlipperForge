"""Payload library manager for saving, loading, and searching payloads."""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


class PayloadLibrary:
    """Manages a local library of BadUSB payload scripts and metadata."""

    def __init__(self, payloads_dir: str | None = None) -> None:
        if payloads_dir is None:
            self.payloads_dir = Path(os.getcwd()) / "payloads"
        else:
            self.payloads_dir = Path(payloads_dir)
        self.payloads_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Validate and sanitize a payload name to prevent path traversal."""
        if not name or not _SAFE_NAME_RE.match(name):
            raise ValueError(
                f"Invalid payload name: '{name}'. "
                "Use only letters, digits, hyphens, and underscores."
            )
        return name

    def save(
        self,
        name: str,
        script: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Save a payload script and its metadata to the library.

        Writes name.txt with the script content and name.meta.json with
        the metadata plus a created_at timestamp.

        Raises:
            ValueError: If the name contains invalid characters.
        """
        name = self._sanitize_name(name)
        script_path = self.payloads_dir / f"{name}.txt"
        meta_path = self.payloads_dir / f"{name}.meta.json"

        script_path.write_text(script, encoding="utf-8")

        meta_data = dict(meta) if meta else {}
        meta_data["created_at"] = datetime.now(UTC).isoformat()

        meta_path.write_text(
            json.dumps(meta_data, indent=2),
            encoding="utf-8",
        )

    def load(self, name: str) -> dict[str, Any] | None:
        """Load a payload by name.

        Returns a dict with 'script' and 'meta' keys, or None if not found.
        """
        script_path = self.payloads_dir / f"{name}.txt"
        meta_path = self.payloads_dir / f"{name}.meta.json"

        if not script_path.exists():
            return None

        script = script_path.read_text(encoding="utf-8")
        meta: dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}

        return {"script": script, "meta": meta}

    def delete(self, name: str) -> bool:
        """Delete a payload by name.

        Returns True if the payload was deleted, False if it was not found.
        """
        script_path = self.payloads_dir / f"{name}.txt"
        meta_path = self.payloads_dir / f"{name}.meta.json"

        if not script_path.exists():
            return False

        script_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

        return True

    def list_all(self) -> list[dict[str, Any]]:
        """List all payloads in the library.

        Returns a list of dicts, each containing 'name' and 'meta'.
        """
        results: list[dict[str, Any]] = []

        for script_file in sorted(self.payloads_dir.glob("*.txt")):
            name = script_file.stem
            meta_path = self.payloads_dir / f"{name}.meta.json"
            meta: dict[str, Any] = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    meta = {}
            results.append({"name": name, "meta": meta})

        return results

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search payloads by name or metadata values (case-insensitive).

        Returns a list of dicts matching the query, each with 'name' and 'meta'.
        """
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for entry in self.list_all():
            # Check name
            if query_lower in entry["name"].lower():
                results.append(entry)
                continue

            # Check meta values
            for value in entry["meta"].values():
                if isinstance(value, str) and query_lower in value.lower():
                    results.append(entry)
                    break

        return results
