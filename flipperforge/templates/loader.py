"""YAML template loader for FlipperForge payload templates."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class TemplateError(Exception):
    """Raised when a template file is invalid or cannot be loaded."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Parameter:
    """A single template parameter definition."""

    name: str
    type: str  # string | integer | boolean | choice
    default: Any
    description: str = ""
    choices: list[str] | None = None
    min: int | None = None
    max: int | None = None


@dataclass
class MitreInfo:
    """MITRE ATT&CK mapping for a template."""

    tactic: str
    technique: str


@dataclass
class SafetyInfo:
    """Safety metadata attached to a template."""

    requires_confirmation: bool = True
    scope_note: str = ""


@dataclass
class Template:
    """A fully-parsed payload template."""

    name: str
    description: str
    author: str
    version: str
    mitre: MitreInfo
    platform: str
    parameters: list[Parameter] = field(default_factory=list)
    safety: SafetyInfo = field(default_factory=SafetyInfo)
    script: str = ""
    source_path: Path | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_VALID_PARAM_TYPES = {"string", "integer", "boolean", "choice"}

_VALID_PLATFORMS = {"windows", "macos", "linux", "cross-platform"}

_REQUIRED_TOP_KEYS = {"name", "description", "author", "version", "mitre", "platform", "script"}


def _parse_parameter(raw: dict[str, Any]) -> Parameter:
    """Parse a single parameter dict into a Parameter dataclass."""
    if "name" not in raw or "type" not in raw:
        raise TemplateError("Each parameter must have 'name' and 'type' keys")

    ptype = raw["type"]
    if ptype not in _VALID_PARAM_TYPES:
        raise TemplateError(
            f"Invalid parameter type '{ptype}' for '{raw['name']}'. "
            f"Must be one of: {', '.join(sorted(_VALID_PARAM_TYPES))}"
        )

    if ptype == "choice" and not raw.get("choices"):
        raise TemplateError(f"Parameter '{raw['name']}' is type 'choice' but has no 'choices' list")

    return Parameter(
        name=raw["name"],
        type=ptype,
        default=raw.get("default"),
        description=raw.get("description", ""),
        choices=raw.get("choices"),
        min=raw.get("min"),
        max=raw.get("max"),
    )


def _parse_mitre(raw: dict[str, Any]) -> MitreInfo:
    """Parse the mitre section."""
    if "tactic" not in raw or "technique" not in raw:
        raise TemplateError("'mitre' section must contain 'tactic' and 'technique'")
    return MitreInfo(tactic=raw["tactic"], technique=raw["technique"])


def _parse_safety(raw: dict[str, Any] | None) -> SafetyInfo:
    """Parse the safety section (optional)."""
    if raw is None:
        return SafetyInfo()
    return SafetyInfo(
        requires_confirmation=raw.get("requires_confirmation", True),
        scope_note=raw.get("scope_note", ""),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_template(path: str | Path) -> Template:
    """Load and validate a single YAML template from *path*.

    Parameters
    ----------
    path:
        Filesystem path to a ``.yaml`` template file.

    Returns
    -------
    Template
        Fully validated template object.

    Raises
    ------
    TemplateError
        If the file is missing, unreadable, or contains invalid data.
    """
    path = Path(path)

    if not path.exists():
        raise TemplateError(f"Template file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Cannot read template file: {path} - {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise TemplateError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise TemplateError(f"Template root must be a mapping, got {type(data).__name__}")

    missing = _REQUIRED_TOP_KEYS - data.keys()
    if missing:
        raise TemplateError(f"Template is missing required keys: {', '.join(sorted(missing))}")

    platform = data["platform"].lower()
    if platform not in _VALID_PLATFORMS:
        raise TemplateError(
            f"Invalid platform '{data['platform']}'. "
            f"Must be one of: {', '.join(sorted(_VALID_PLATFORMS))}"
        )

    parameters = [_parse_parameter(p) for p in data.get("parameters", [])]
    mitre = _parse_mitre(data["mitre"])
    safety = _parse_safety(data.get("safety"))

    return Template(
        name=data["name"],
        description=data["description"],
        author=data["author"],
        version=str(data["version"]),
        mitre=mitre,
        platform=platform,
        parameters=parameters,
        safety=safety,
        script=data.get("script", ""),
        source_path=path.resolve(),
    )


def discover_templates(directory: str | Path) -> list[Template]:
    """Recursively discover and load all ``.yaml`` templates under *directory*.

    Parameters
    ----------
    directory:
        Root directory to search.

    Returns
    -------
    list[Template]
        All successfully loaded templates, sorted by name.

    Raises
    ------
    TemplateError
        If *directory* does not exist.
    """
    directory = Path(directory)

    if not directory.is_dir():
        raise TemplateError(f"Directory not found: {directory}")

    templates: list[Template] = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if not fname.endswith(".yaml"):
                continue
            fpath = Path(root) / fname
            try:
                templates.append(load_template(fpath))
            except TemplateError as exc:
                logger.warning("Skipping invalid template %s: %s", fpath, exc)
                continue

    templates.sort(key=lambda t: t.name)
    return templates
