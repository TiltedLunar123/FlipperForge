"""Build cache for FlipperForge - stores the last compiled payload."""

import json
import os
from pathlib import Path


class BuildCache:
    """Persistent cache that saves and loads the most recent build output."""

    def __init__(self, cache_dir: str | None = None) -> None:
        if cache_dir is None:
            cache_dir = os.path.join(os.getcwd(), ".flipperforge", "cache")
        self._cache_dir = Path(cache_dir)

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def save(self, script: str, meta: dict) -> None:
        """Write the last build script and metadata to disk."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        script_path = self._cache_dir / "last_build.txt"
        meta_path = self._cache_dir / "last_build_meta.json"

        script_path.write_text(script, encoding="utf-8")
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def load(self) -> dict | None:
        """Return a dict with 'script' and 'meta', or None when nothing is cached."""
        script_path = self._cache_dir / "last_build.txt"
        meta_path = self._cache_dir / "last_build_meta.json"

        if not script_path.exists() or not meta_path.exists():
            return None

        script = script_path.read_text(encoding="utf-8")
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            meta = {}
        return {"script": script, "meta": meta}

    def clear(self) -> None:
        """Remove cached build files."""
        script_path = self._cache_dir / "last_build.txt"
        meta_path = self._cache_dir / "last_build_meta.json"

        if script_path.exists():
            script_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
