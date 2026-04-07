"""Tests for the safety linter."""

from flipperforge.engine.linter import lint


class TestLintRules:
    def test_no_initial_delay(self):
        warnings = lint("GUI r\nSTRING cmd\nENTER")
        codes = [w.code for w in warnings]
        assert "NO_INITIAL_DELAY" in codes

    def test_initial_delay_ok(self):
        warnings = lint("DELAY 500\nGUI r\nSTRING cmd\nENTER")
        codes = [w.code for w in warnings]
        assert "NO_INITIAL_DELAY" not in codes

    def test_short_delay_after_gui(self):
        warnings = lint("DELAY 500\nGUI r\nDELAY 50\nSTRING cmd")
        codes = [w.code for w in warnings]
        assert "SHORT_DELAY" in codes

    def test_adequate_delay_after_gui(self):
        warnings = lint("DELAY 500\nGUI r\nDELAY 200\nSTRING cmd")
        codes = [w.code for w in warnings]
        assert "SHORT_DELAY" not in codes

    def test_dangerous_format(self):
        warnings = lint("DELAY 500\nSTRING format C: /y")
        codes = [w.code for w in warnings]
        assert "DANGEROUS_COMMAND" in codes

    def test_dangerous_rm_rf(self):
        warnings = lint("DELAY 500\nSTRING rm -rf /")
        codes = [w.code for w in warnings]
        assert "DANGEROUS_COMMAND" in codes

    def test_dangerous_reg_delete(self):
        warnings = lint("DELAY 500\nSTRING reg delete HKLM\\Software /f")
        codes = [w.code for w in warnings]
        assert "DANGEROUS_COMMAND" in codes

    def test_dangerous_bcdedit(self):
        warnings = lint("DELAY 500\nSTRING bcdedit /set testsigning on")
        codes = [w.code for w in warnings]
        assert "DANGEROUS_COMMAND" in codes

    def test_dangerous_remove_item(self):
        warnings = lint("DELAY 500\nSTRING Remove-Item C:\\Temp -Recurse -Force")
        codes = [w.code for w in warnings]
        assert "DANGEROUS_COMMAND" in codes

    def test_no_rem_header(self):
        warnings = lint("DELAY 500\nGUI r")
        codes = [w.code for w in warnings]
        assert "NO_REM_HEADER" in codes

    def test_rem_header_ok(self):
        warnings = lint("REM My payload\nDELAY 500\nGUI r")
        codes = [w.code for w in warnings]
        assert "NO_REM_HEADER" not in codes

    def test_missing_confirmation_pause(self):
        warnings = lint("REM test\nDELAY 500\nGUI r", requires_confirmation=True)
        codes = [w.code for w in warnings]
        assert "MISSING_CONFIRMATION_PAUSE" in codes

    def test_confirmation_pause_present(self):
        warnings = lint("REM test\nDELAY 3000\nGUI r", requires_confirmation=True)
        codes = [w.code for w in warnings]
        assert "MISSING_CONFIRMATION_PAUSE" not in codes

    def test_clean_script_no_warnings(self):
        script = "REM Clean payload\nDELAY 500\nGUI r\nDELAY 300\nSTRING notepad\nENTER"
        warnings = lint(script)
        assert warnings == []


class TestNoCleanupRule:
    def test_opens_shell_no_cleanup(self):
        """Script opens cmd but never exits -- should warn."""
        script = "REM test\nDELAY 500\nGUI r\nDELAY 300\nSTRING cmd\nENTER\nDELAY 500\nSTRING whoami\nENTER"
        warnings = lint(script)
        codes = [w.code for w in warnings]
        assert "NO_CLEANUP" in codes

    def test_opens_shell_with_exit(self):
        """Script opens cmd and exits -- should not warn."""
        script = (
            "REM test\nDELAY 500\nGUI r\nDELAY 300\nSTRING cmd\nENTER\n"
            "DELAY 500\nSTRING whoami\nENTER\nSTRING exit\nENTER"
        )
        warnings = lint(script)
        codes = [w.code for w in warnings]
        assert "NO_CLEANUP" not in codes

    def test_opens_shell_with_alt_f4(self):
        """Script opens powershell and closes with ALT F4 -- should not warn."""
        script = (
            "REM test\nDELAY 500\nGUI r\nDELAY 300\nSTRING powershell\nENTER\n"
            "DELAY 500\nSTRING hostname\nENTER\nALT F4"
        )
        warnings = lint(script)
        codes = [w.code for w in warnings]
        assert "NO_CLEANUP" not in codes

    def test_no_shell_no_warning(self):
        """Script without shell commands should not trigger NO_CLEANUP."""
        script = "REM test\nDELAY 500\nGUI r\nDELAY 300\nSTRING notepad\nENTER"
        warnings = lint(script)
        codes = [w.code for w in warnings]
        assert "NO_CLEANUP" not in codes
