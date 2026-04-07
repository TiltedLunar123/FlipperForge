"""Integration tests that exercise the full pipeline across multiple modules."""

from pathlib import Path

import pytest

from flipperforge.engine.compiler import compile_template
from flipperforge.templates.loader import discover_templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class TestCompileAllBuiltinTemplates:
    """Every built-in template must compile with its default parameters."""

    @pytest.fixture
    def templates(self):
        return discover_templates(TEMPLATES_DIR)

    def test_at_least_six_templates(self, templates):
        assert len(templates) >= 6

    @pytest.mark.parametrize(
        "name",
        [
            "system-info",
            "wifi-passwords",
            "reverse-shell",
            "scheduled-task",
            "file-grab",
            "network-scan",
        ],
    )
    def test_compile_with_defaults(self, templates, name):
        """Each template should compile without errors using defaults."""
        match = [t for t in templates if t.name == name]
        assert match, f"Template '{name}' not found"
        template = match[0]

        result = compile_template(template)
        assert result.script, f"Template '{name}' produced empty script"
        assert result.errors == [], f"Template '{name}' has errors: {result.errors}"
        assert result.template_name == name
        assert result.mitre_tactic
        assert result.mitre_technique
