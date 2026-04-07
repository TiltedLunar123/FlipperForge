"""Tests for the FlipperForge CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from flipperforge.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestCLIBasic:
    def setup_method(self):
        self.runner = CliRunner()

    def test_version(self):
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output

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

    def test_list_filter_tactic_case_insensitive(self):
        """Tactic filter should match case-insensitively."""
        result = self.runner.invoke(
            main, ["list", "--tactic", "Discovery", "--templates-dir", str(FIXTURES)]
        )
        assert result.exit_code == 0
        assert "test-payload" in result.output

        # Also works lowercase
        result2 = self.runner.invoke(
            main, ["list", "--tactic", "discovery", "--templates-dir", str(FIXTURES)]
        )
        assert result2.exit_code == 0
        assert "test-payload" in result2.output


class TestInfoCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_info_known_template(self):
        result = self.runner.invoke(
            main, ["info", "test-payload", "--templates-dir", str(FIXTURES)]
        )
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
        result = self.runner.invoke(
            main,
            [
                "build",
                "test-payload",
                "--templates-dir",
                str(FIXTURES),
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
        )
        assert result.exit_code == 0
        assert "Compiled" in result.output

    def test_build_with_params(self, tmp_path):
        result = self.runner.invoke(
            main,
            [
                "build",
                "test-payload",
                "--templates-dir",
                str(FIXTURES),
                "--cache-dir",
                str(tmp_path / "cache"),
                "-p",
                "msg=testing",
                "-p",
                "delay_ms=1000",
            ],
        )
        assert result.exit_code == 0

    def test_build_unknown_template(self, tmp_path):
        result = self.runner.invoke(
            main,
            [
                "build",
                "nonexistent",
                "--templates-dir",
                str(FIXTURES),
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
        )
        assert result.exit_code != 0

    def test_build_invalid_param(self, tmp_path):
        result = self.runner.invoke(
            main,
            [
                "build",
                "test-payload",
                "--templates-dir",
                str(FIXTURES),
                "--cache-dir",
                str(tmp_path / "cache"),
                "-p",
                "delay_ms=not_a_number",
            ],
        )
        assert result.exit_code != 0

    def test_build_unknown_param_rejected(self, tmp_path):
        """Unknown parameters should cause a compile error."""
        result = self.runner.invoke(
            main,
            [
                "build",
                "test-payload",
                "--templates-dir",
                str(FIXTURES),
                "--cache-dir",
                str(tmp_path / "cache"),
                "-p",
                "nonexistent_param=value",
            ],
        )
        assert result.exit_code != 0
        assert "Unknown parameter" in result.output


class TestPreviewCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_preview_no_cache(self, tmp_path):
        result = self.runner.invoke(
            main,
            [
                "preview",
                "--cache-dir",
                str(tmp_path / "empty"),
            ],
        )
        assert "No compiled payload" in result.output

    def test_preview_after_build(self, tmp_path):
        # Build first
        self.runner.invoke(
            main,
            [
                "build",
                "test-payload",
                "--templates-dir",
                str(FIXTURES),
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
        )
        # Then preview
        result = self.runner.invoke(
            main,
            [
                "preview",
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
        )
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
        result = self.runner.invoke(
            main,
            [
                "save",
                "test",
                "--cache-dir",
                str(tmp_path / "empty"),
            ],
        )
        assert "No compiled payload" in result.output


class TestDeviceCommands:
    """Tests for device subcommands (all serial mocked)."""

    def setup_method(self):
        self.runner = CliRunner()

    @patch("flipperforge.deploy.serial.FlipperConnection")
    def test_device_ls(self, mock_conn_cls):
        """device ls should display files from the Flipper."""
        mock_conn = MagicMock()
        mock_conn_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.list_badusb_files.return_value = [
            {"name": "test.txt", "size": "128"},
        ]

        result = self.runner.invoke(main, ["device", "ls", "--port", "COM3"])
        assert result.exit_code == 0
        assert "test.txt" in result.output

    @patch("flipperforge.deploy.serial.FlipperConnection")
    def test_device_ls_empty(self, mock_conn_cls):
        """device ls with no files should show a message."""
        mock_conn = MagicMock()
        mock_conn_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.list_badusb_files.return_value = []

        result = self.runner.invoke(main, ["device", "ls", "--port", "COM3"])
        assert "No BadUSB payloads" in result.output

    @patch("flipperforge.deploy.serial.FlipperConnection")
    def test_device_pull(self, mock_conn_cls, tmp_path):
        """device pull should save pulled content to local library."""
        mock_conn = MagicMock()
        mock_conn_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.read_file.return_value = "REM pulled\nDELAY 100"

        result = self.runner.invoke(main, ["device", "pull", "test.txt", "--port", "COM3"])
        assert result.exit_code == 0
        assert "Pulled" in result.output

    @patch("flipperforge.deploy.serial.FlipperConnection")
    def test_device_rm(self, mock_conn_cls):
        """device rm should delete a file from the Flipper."""
        mock_conn = MagicMock()
        mock_conn_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = self.runner.invoke(main, ["device", "rm", "test.txt", "--port", "COM3", "-y"])
        assert result.exit_code == 0
        assert "Deleted" in result.output


class TestLibraryCommands:
    """Tests for library subcommands."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_library_ls_empty(self):
        """library ls with no payloads should show a message."""
        result = self.runner.invoke(main, ["library", "ls"])
        # May show "No saved payloads" or list items depending on cwd
        assert result.exit_code == 0

    def test_library_search_no_results(self):
        """library search with no matches should show a message."""
        result = self.runner.invoke(main, ["library", "search", "nonexistent_xyz"])
        assert "No payloads matching" in result.output

    def test_library_load_not_found(self, tmp_path):
        """library load should fail for nonexistent payloads."""
        result = self.runner.invoke(
            main,
            [
                "library",
                "load",
                "nonexistent",
                "--cache-dir",
                str(tmp_path / "cache"),
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_library_rm_not_found(self):
        """library rm should fail for nonexistent payloads."""
        result = self.runner.invoke(main, ["library", "rm", "nonexistent_xyz", "-y"])
        assert result.exit_code != 0
        assert "not found" in result.output
