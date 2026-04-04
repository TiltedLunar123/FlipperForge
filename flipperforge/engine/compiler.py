"""
Template compiler for FlipperForge.

Validates parameters, renders Jinja2 templates, parses the resulting
DuckyScript, and runs lint checks -- returning a single CompileResult.

Author: TiltedLunar123 <hilgendorfjude@gmail.com>
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import jinja2

from flipperforge.engine.linter import Warning, lint
from flipperforge.engine.parser import parse
from flipperforge.templates.loader import Parameter, Template


# -- Exceptions -------------------------------------------------------------

class CompileError(Exception):
    """Raised when template compilation fails due to invalid parameters."""


# -- Result dataclass -------------------------------------------------------

@dataclass
class CompileResult:
    """Aggregated result of compiling a template."""

    script: str
    template_name: str
    mitre_tactic: str
    mitre_technique: str
    mitre_subtechnique: str
    params_used: dict[str, Any] = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list[Warning] = field(default_factory=list)


# -- Parameter validation ---------------------------------------------------

_MAX_STRING_LENGTH = 500


def _validate_params(
    template: Template,
    params: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate user-supplied *params* against the template's parameter defs.

    Missing params are filled from defaults.  Returns the merged dict of
    validated parameter values ready for Jinja2 rendering.

    Raises
    ------
    CompileError
        If any parameter value is invalid.
    """
    params = dict(params) if params else {}
    merged: dict[str, Any] = {}

    for pdef in template.parameters:
        value = params.pop(pdef.name, None)

        # Fall back to default when the caller did not supply a value
        if value is None:
            value = pdef.default

        # Validate by type
        if pdef.type == "string":
            value = _validate_string(pdef, value)
        elif pdef.type == "integer":
            value = _validate_integer(pdef, value)
        elif pdef.type == "boolean":
            value = _validate_boolean(pdef, value)
        elif pdef.type == "choice":
            value = _validate_choice(pdef, value)

        merged[pdef.name] = value

    return merged


def _validate_string(pdef: Parameter, value: Any) -> str:
    """Validate a string parameter value."""
    value = str(value) if value is not None else ""
    if "\x00" in value:
        raise CompileError(
            f"Parameter '{pdef.name}' contains null bytes"
        )
    if len(value) > _MAX_STRING_LENGTH:
        raise CompileError(
            f"Parameter '{pdef.name}' exceeds max length of "
            f"{_MAX_STRING_LENGTH} characters (got {len(value)})"
        )
    return value


def _validate_integer(pdef: Parameter, value: Any) -> str:
    """Validate an integer parameter and return its string representation."""
    try:
        int_val = int(value)
    except (TypeError, ValueError):
        raise CompileError(
            f"Parameter '{pdef.name}' must be an integer, got '{value}'"
        )

    if pdef.min is not None and int_val < pdef.min:
        raise CompileError(
            f"Parameter '{pdef.name}' value {int_val} is below "
            f"minimum {pdef.min}"
        )
    if pdef.max is not None and int_val > pdef.max:
        raise CompileError(
            f"Parameter '{pdef.name}' value {int_val} is above "
            f"maximum {pdef.max}"
        )

    return str(int_val)


def _validate_boolean(pdef: Parameter, value: Any) -> str:
    """Validate a boolean parameter and return 'true' or 'false'."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
        return "true" if value.lower() in ("true", "1") else "false"
    # Accept integer-like truthy/falsy values
    try:
        return "true" if int(value) else "false"
    except (TypeError, ValueError):
        raise CompileError(
            f"Parameter '{pdef.name}' must be a boolean, got '{value}'"
        )


def _validate_choice(pdef: Parameter, value: Any) -> str:
    """Validate a choice parameter against the allowed list."""
    value = str(value)
    if pdef.choices and value not in pdef.choices:
        raise CompileError(
            f"Parameter '{pdef.name}' must be one of "
            f"{pdef.choices}, got '{value}'"
        )
    return value


# -- Public API --------------------------------------------------------------

def compile_template(
    template: Template,
    *,
    params: dict[str, Any] | None = None,
) -> CompileResult:
    """Compile a FlipperForge template into a validated DuckyScript payload.

    Steps
    -----
    1. Validate and merge parameters with defaults.
    2. Render the Jinja2 template with the merged params.
    3. Parse the rendered script and collect errors.
    4. Lint the rendered script and collect warnings.
    5. Return a CompileResult with all metadata.

    Parameters
    ----------
    template:
        A loaded Template object.
    params:
        Optional dict of parameter overrides.

    Returns
    -------
    CompileResult
        The compiled script along with metadata, errors, and warnings.

    Raises
    ------
    CompileError
        If parameter validation fails.
    """
    # Step 1 -- validate and merge params
    merged = _validate_params(template, params)

    # Step 2 -- render Jinja2 template
    try:
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        jinja_tmpl = env.from_string(template.script)
        rendered = jinja_tmpl.render(**merged)
    except jinja2.TemplateError as exc:
        raise CompileError(f"Template rendering failed: {exc}") from exc

    # Step 3 -- parse rendered script
    parse_result = parse(rendered)
    errors = [
        f"Line {e.line_number}: {e.message}" for e in parse_result.errors
    ]

    # Step 4 -- lint rendered script
    requires_conf = template.safety.requires_confirmation
    warnings = lint(rendered, requires_confirmation=requires_conf)

    # Step 5 -- build subtechnique from technique string if present
    # Subtechnique is the portion after the dot, e.g. T1059.001 -> 001
    technique = template.mitre.technique
    subtechnique = ""
    if "." in technique:
        parts = technique.split(".", 1)
        technique = parts[0]
        subtechnique = parts[1]

    return CompileResult(
        script=rendered,
        template_name=template.name,
        mitre_tactic=template.mitre.tactic,
        mitre_technique=technique,
        mitre_subtechnique=subtechnique,
        params_used=merged,
        errors=errors,
        warnings=warnings,
    )
