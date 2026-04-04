"""
Tests for the template compiler.

Covers parameter validation, template rendering, metadata propagation,
and integration with the parser and linter.

Author: TiltedLunar123 <hilgendorfjude@gmail.com>
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flipperforge.engine.compiler import CompileError, CompileResult, compile_template
from flipperforge.templates.loader import load_template

# -- Fixtures ---------------------------------------------------------------

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "test-template.yaml"


@pytest.fixture
def template():
    """Load the shared test template fixture."""
    return load_template(FIXTURE_PATH)


# -- Compile with defaults --------------------------------------------------

class TestCompileDefaults:
    def test_compile_with_defaults(self, template):
        result = compile_template(template)
        assert isinstance(result, CompileResult)
        assert result.script  # non-empty
        assert "hello" in result.script  # default msg value
        assert "500" in result.script  # default delay_ms value

    def test_default_params_used(self, template):
        result = compile_template(template)
        assert result.params_used["msg"] == "hello"
        assert result.params_used["delay_ms"] == "500"
        assert result.params_used["verbose"] == "false"
        assert result.params_used["shell"] == "cmd"


# -- Compile with custom params --------------------------------------------

class TestCompileCustomParams:
    def test_compile_with_custom_params(self, template):
        result = compile_template(template, params={
            "msg": "world",
            "delay_ms": 1000,
        })
        assert "world" in result.script
        assert "1000" in result.script

    def test_custom_params_recorded(self, template):
        result = compile_template(template, params={"msg": "custom"})
        assert result.params_used["msg"] == "custom"
        # Others should still be defaults
        assert result.params_used["delay_ms"] == "500"


# -- Integer validation -----------------------------------------------------

class TestValidateInteger:
    def test_invalid_integer_raises(self, template):
        with pytest.raises(CompileError, match="must be an integer"):
            compile_template(template, params={"delay_ms": "not_a_number"})

    def test_valid_integer_accepted(self, template):
        result = compile_template(template, params={"delay_ms": "200"})
        assert result.params_used["delay_ms"] == "200"


# -- Choice validation ------------------------------------------------------

class TestValidateChoice:
    def test_invalid_choice_raises(self, template):
        with pytest.raises(CompileError, match="must be one of"):
            compile_template(template, params={"shell": "zsh"})

    def test_valid_choice_accepted(self, template):
        result = compile_template(template, params={"shell": "powershell"})
        assert result.params_used["shell"] == "powershell"


# -- String length validation -----------------------------------------------

class TestValidateStringLength:
    def test_string_too_long_raises(self, template):
        long_string = "a" * 501
        with pytest.raises(CompileError, match="exceeds max length"):
            compile_template(template, params={"msg": long_string})

    def test_string_at_max_length_ok(self, template):
        max_string = "a" * 500
        result = compile_template(template, params={"msg": max_string})
        assert result.params_used["msg"] == max_string


# -- Warnings list ----------------------------------------------------------

class TestResultWarnings:
    def test_result_has_warnings_list(self, template):
        result = compile_template(template)
        assert isinstance(result.warnings, list)
        # The linter may or may not produce warnings for this template,
        # but the field must always be a list.


# -- Metadata ---------------------------------------------------------------

class TestResultMetadata:
    def test_template_name(self, template):
        result = compile_template(template)
        assert result.template_name == "test-payload"

    def test_mitre_tactic(self, template):
        result = compile_template(template)
        assert result.mitre_tactic == "discovery"

    def test_mitre_technique(self, template):
        result = compile_template(template)
        assert result.mitre_technique == "T1082"

    def test_mitre_subtechnique_empty_when_absent(self, template):
        result = compile_template(template)
        assert result.mitre_subtechnique == ""
