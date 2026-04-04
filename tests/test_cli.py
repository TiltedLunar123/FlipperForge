"""Tests for the FlipperForge CLI."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from flipperforge.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestCLIBasic:
    def setup_method(self):
        self.runner = CliRunner()

    def test_version(self):
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self):
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "FlipperForge" in result.output


class TestListCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_list_templates(self):
        result = self.runner.invoke(main, ["list", "--templates-dir", str(FIXTURES)])
        assert result.exit_code == 0
        assert "test-payload" in result.output

    def test_list_empty_dir(self, tmp_path):
        result = self.runner.invoke(main, ["list", "--templates-dir", str(tmp_path)])
        assert "No templates found" in result.output


class TestInfoCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_info_known_template(self):
        result = self.runner.invoke(main, ["info", "test-payload", "--templates-dir", str(FIXTURES)])
        assert result.exit_code == 0
        assert "test-payload" in result.output
        assert "discovery" in result.output
        assert "T1082" in result.output

    def test_info_unknown_template(self):
        result = self.runner.invoke(main, ["info", "nonexistent", "--templates-dir", str(FIXTURES)])
        assert result.exit_code != 0


class TestBuildCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_build_with_defaults(self, tmp_path):
        result = self.runner.invoke(main, [
            "build", "test-payload",
            "--templates-dir", str(FIXTURES),
            "--cache-dir", str(tmp_path / "cache"),
        ])
        assert result.exit_code == 0
        assert "Compiled" in result.output

    def test_build_with_params(self, tmp_path):
        result = self.runner.invoke(main, [
            "build", "test-payload",
            "--templates-dir", str(FIXTURES),
            "--cache-dir", str(tmp_path / "cache"),
            "-p", "msg=testing",
            "-p", "delay_ms=1000",
        ])
        assert result.exit_code == 0

    def test_build_unknown_template(self, tmp_path):
        result = self.runner.invoke(main, [
            "build", "nonexistent",
            "--templates-dir", str(FIXTURES),
            "--cache-dir", str(tmp_path / "cache"),
        ])
        assert result.exit_code != 0

    def test_build_invalid_param(self, tmp_path):
        result = self.runner.invoke(main, [
            "build", "test-payload",
            "--templates-dir", str(FIXTURES),
            "--cache-dir", str(tmp_path / "cache"),
            "-p", "delay_ms=not_a_number",
        ])
        assert result.exit_code != 0


class TestPreviewCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_preview_no_cache(self, tmp_path):
        result = self.runner.invoke(main, [
            "preview",
            "--cache-dir", str(tmp_path / "empty"),
        ])
        assert "No compiled payload" in result.output

    def test_preview_after_build(self, tmp_path):
        # Build first
        self.runner.invoke(main, [
            "build", "test-payload",
            "--templates-dir", str(FIXTURES),
            "--cache-dir", str(tmp_path / "cache"),
        ])
        # Then preview
        result = self.runner.invoke(main, [
            "preview",
            "--cache-dir", str(tmp_path / "cache"),
        ])
        assert result.exit_code == 0
        assert "test-payload" in result.output


class TestValidateCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_validate_good_script(self, tmp_path):
        script_file = tmp_path / "good.txt"
        script_file.write_text("REM test\nDELAY 500\nGUI r\nDELAY 300\nSTRING hello\nENTER")
        result = self.runner.invoke(main, ["validate", str(script_file)])
        assert result.exit_code == 0
        assert "No syntax errors" in result.output

    def test_validate_bad_script(self, tmp_path):
        script_file = tmp_path / "bad.txt"
        script_file.write_text("FOOBAR\nBADCOMMAND")
        result = self.runner.invoke(main, ["validate", str(script_file)])
        assert "Error" in result.output


class TestSaveCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_save_no_cache(self, tmp_path):
        result = self.runner.invoke(main, [
            "save", "test",
            "--cache-dir", str(tmp_path / "empty"),
        ])
        assert "No compiled payload" in result.output
