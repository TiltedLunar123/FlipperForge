"""Tests for flipperforge.templates.loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from flipperforge.templates.loader import (
    Template,
    TemplateError,
    discover_templates,
    load_template,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
VALID_TEMPLATE = FIXTURES / "test-template.yaml"


# ------------------------------------------------------------------
# Loading a valid template
# ------------------------------------------------------------------

class TestLoadValidTemplate:
    """Verify that all fields are parsed correctly from a valid file."""

    @pytest.fixture()
    def tpl(self) -> Template:
        return load_template(VALID_TEMPLATE)

    def test_name(self, tpl: Template) -> None:
        assert tpl.name == "test-payload"

    def test_description(self, tpl: Template) -> None:
        assert tpl.description == "A test payload for unit tests"

    def test_author(self, tpl: Template) -> None:
        assert tpl.author == "test"

    def test_version(self, tpl: Template) -> None:
        assert tpl.version == "1.0"

    def test_platform(self, tpl: Template) -> None:
        assert tpl.platform == "windows"

    def test_mitre_tactic(self, tpl: Template) -> None:
        assert tpl.mitre.tactic == "discovery"

    def test_mitre_technique(self, tpl: Template) -> None:
        assert tpl.mitre.technique == "T1082"

    def test_source_path(self, tpl: Template) -> None:
        assert tpl.source_path is not None
        assert tpl.source_path.name == "test-template.yaml"

    def test_script_contains_duckyscript(self, tpl: Template) -> None:
        assert "DELAY" in tpl.script
        assert "GUI r" in tpl.script


# ------------------------------------------------------------------
# Parameter parsing
# ------------------------------------------------------------------

class TestParameterTypes:
    """Ensure every parameter type is parsed and carries correct metadata."""

    @pytest.fixture()
    def params(self) -> dict:
        tpl = load_template(VALID_TEMPLATE)
        return {p.name: p for p in tpl.parameters}

    def test_string_param(self, params: dict) -> None:
        p = params["msg"]
        assert p.type == "string"
        assert p.default == "hello"

    def test_integer_param(self, params: dict) -> None:
        p = params["delay_ms"]
        assert p.type == "integer"
        assert p.default == 500

    def test_boolean_param(self, params: dict) -> None:
        p = params["verbose"]
        assert p.type == "boolean"
        assert p.default is False

    def test_choice_param(self, params: dict) -> None:
        p = params["shell"]
        assert p.type == "choice"
        assert p.default == "cmd"

    def test_choice_has_choices_list(self, params: dict) -> None:
        p = params["shell"]
        assert p.choices == ["cmd", "powershell", "terminal"]

    def test_parameter_count(self, params: dict) -> None:
        assert len(params) == 4


# ------------------------------------------------------------------
# Safety metadata
# ------------------------------------------------------------------

class TestSafetyInfo:

    @pytest.fixture()
    def tpl(self) -> Template:
        return load_template(VALID_TEMPLATE)

    def test_requires_confirmation(self, tpl: Template) -> None:
        assert tpl.safety.requires_confirmation is False

    def test_scope_note(self, tpl: Template) -> None:
        assert tpl.safety.scope_note == "Test only"


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------

class TestErrorHandling:

    def test_missing_file_raises_template_error(self) -> None:
        with pytest.raises(TemplateError, match="not found"):
            load_template("/nonexistent/path/template.yaml")

    def test_invalid_yaml_raises_template_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("{{invalid yaml content", encoding="utf-8")
        with pytest.raises(TemplateError, match="Invalid YAML"):
            load_template(bad)

    def test_missing_required_keys_raises_template_error(self, tmp_path: Path) -> None:
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text("name: only-name\n", encoding="utf-8")
        with pytest.raises(TemplateError, match="missing required keys"):
            load_template(incomplete)

    def test_invalid_param_type_raises_template_error(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            name: bad-param
            description: bad
            author: test
            version: "1.0"
            mitre:
              tactic: execution
              technique: T1059
            platform: windows
            parameters:
              - name: x
                type: foobar
                default: 1
            script: "STRING hello"
        """)
        bad = tmp_path / "bad-param.yaml"
        bad.write_text(content, encoding="utf-8")
        with pytest.raises(TemplateError, match="Invalid parameter type"):
            load_template(bad)

    def test_choice_without_choices_raises_template_error(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            name: no-choices
            description: bad
            author: test
            version: "1.0"
            mitre:
              tactic: execution
              technique: T1059
            platform: windows
            parameters:
              - name: x
                type: choice
                default: a
            script: "STRING hello"
        """)
        bad = tmp_path / "no-choices.yaml"
        bad.write_text(content, encoding="utf-8")
        with pytest.raises(TemplateError, match="no 'choices' list"):
            load_template(bad)


# ------------------------------------------------------------------
# Template discovery
# ------------------------------------------------------------------

class TestDiscoverTemplates:

    def test_finds_templates_in_directory(self, tmp_path: Path) -> None:
        # Create a valid template in a subdirectory
        sub = tmp_path / "payloads" / "recon"
        sub.mkdir(parents=True)
        content = textwrap.dedent("""\
            name: discovered
            description: found it
            author: test
            version: "1.0"
            mitre:
              tactic: discovery
              technique: T1082
            platform: windows
            script: "STRING hello"
        """)
        (sub / "found.yaml").write_text(content, encoding="utf-8")

        results = discover_templates(tmp_path)
        assert len(results) == 1
        assert results[0].name == "discovered"

    def test_skips_invalid_templates(self, tmp_path: Path) -> None:
        (tmp_path / "bad.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
        results = discover_templates(tmp_path)
        assert len(results) == 0

    def test_nonexistent_directory_raises_template_error(self) -> None:
        with pytest.raises(TemplateError, match="Directory not found"):
            discover_templates("/nonexistent/dir")

    def test_discovers_fixture_template(self) -> None:
        results = discover_templates(FIXTURES)
        names = [t.name for t in results]
        assert "test-payload" in names
