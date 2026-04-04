"""
Tests for the DuckyScript parser.

Covers tokenisation, validation, error reporting with line numbers,
and typo suggestions for unknown commands.

Author: TiltedLunar123 <hilgendorfjude@gmail.com>
"""

from __future__ import annotations

import pytest

from flipperforge.engine.parser import Command, ParseError, ParseResult, parse


# -- Helpers ----------------------------------------------------------------

def _names(result: ParseResult) -> list[str]:
    """Return just the command names for quick assertions."""
    return [c.name for c in result.commands]


# -- Empty / comment scripts ------------------------------------------------

class TestEmptyAndComments:
    def test_empty_script(self):
        result = parse("")
        assert result.ok
        assert result.commands == []

    def test_blank_lines_ignored(self):
        result = parse("\n\n   \n\n")
        assert result.ok
        assert result.commands == []

    def test_single_comment(self):
        result = parse("REM this is a comment")
        assert result.ok
        assert len(result.commands) == 1
        assert result.commands[0].name == "REM"
        assert result.commands[0].args == "this is a comment"

    def test_comment_preserves_text(self):
        result = parse("REM   extra   spaces  ")
        assert result.commands[0].args == "extra   spaces"


# -- STRING -----------------------------------------------------------------

class TestString:
    def test_basic_string(self):
        result = parse("STRING Hello, world!")
        assert result.ok
        cmd = result.commands[0]
        assert cmd.name == "STRING"
        assert cmd.args == "Hello, world!"

    def test_string_preserves_spaces(self):
        result = parse("STRING   multiple   spaces")
        assert result.ok
        # First space is the separator; remainder is the argument.
        assert result.commands[0].args == "  multiple   spaces"

    def test_string_missing_text(self):
        result = parse("STRING")
        assert not result.ok
        assert result.errors[0].message == "STRING requires text argument"

    def test_string_only_spaces(self):
        # "STRING " with nothing after the space
        result = parse("STRING ")
        assert not result.ok


# -- DELAY ------------------------------------------------------------------

class TestDelay:
    def test_valid_delay(self):
        result = parse("DELAY 500")
        assert result.ok
        assert result.commands[0].name == "DELAY"
        assert result.commands[0].args == "500"

    def test_delay_zero(self):
        result = parse("DELAY 0")
        assert result.ok

    def test_delay_missing_value(self):
        result = parse("DELAY")
        assert not result.ok
        assert "numeric" in result.errors[0].message.lower()

    def test_delay_non_numeric(self):
        result = parse("DELAY abc")
        assert not result.ok
        assert "non-negative integer" in result.errors[0].message

    def test_delay_negative(self):
        result = parse("DELAY -100")
        assert not result.ok
        assert "non-negative" in result.errors[0].message


# -- Single keys ------------------------------------------------------------

class TestSingleKeys:
    @pytest.mark.parametrize("key", [
        "ENTER", "TAB", "ESCAPE", "SPACE", "BACKSPACE", "DELETE",
        "HOME", "END", "PAGEUP", "PAGEDOWN",
        "UPARROW", "DOWNARROW", "LEFTARROW", "RIGHTARROW",
        "UP", "DOWN", "LEFT", "RIGHT",
    ])
    def test_single_key(self, key: str):
        result = parse(key)
        assert result.ok
        assert result.commands[0].name == key


# -- Function keys ----------------------------------------------------------

class TestFunctionKeys:
    @pytest.mark.parametrize("key", [f"F{n}" for n in range(1, 13)])
    def test_function_key(self, key: str):
        result = parse(key)
        assert result.ok
        assert result.commands[0].name == key


# -- Modifier combos --------------------------------------------------------

class TestModifierCombos:
    def test_gui_alone(self):
        result = parse("GUI")
        assert result.ok
        assert result.commands[0].name == "GUI"

    def test_gui_with_key(self):
        result = parse("GUI r")
        assert result.ok
        assert result.commands[0].name == "GUI"
        assert result.commands[0].args == "r"

    def test_ctrl_alt_delete(self):
        result = parse("CTRL ALT DELETE")
        assert result.ok
        cmd = result.commands[0]
        assert cmd.name == "CTRL"
        assert cmd.args == "ALT DELETE"

    def test_alt_f4(self):
        result = parse("ALT F4")
        assert result.ok
        assert result.commands[0].args == "F4"

    def test_shift_key(self):
        result = parse("SHIFT TAB")
        assert result.ok
        assert result.commands[0].name == "SHIFT"
        assert result.commands[0].args == "TAB"


# -- REPEAT -----------------------------------------------------------------

class TestRepeat:
    def test_valid_repeat(self):
        result = parse("REPEAT 3")
        assert result.ok
        assert result.commands[0].name == "REPEAT"
        assert result.commands[0].args == "3"

    def test_repeat_missing_value(self):
        result = parse("REPEAT")
        assert not result.ok
        assert "positive integer" in result.errors[0].message

    def test_repeat_zero(self):
        result = parse("REPEAT 0")
        assert not result.ok
        assert "positive" in result.errors[0].message

    def test_repeat_negative(self):
        result = parse("REPEAT -1")
        assert not result.ok
        assert "positive" in result.errors[0].message

    def test_repeat_non_numeric(self):
        result = parse("REPEAT xyz")
        assert not result.ok
        assert "positive integer" in result.errors[0].message


# -- Multiline scripts ------------------------------------------------------

class TestMultiline:
    def test_simple_payload(self):
        script = "\n".join([
            "REM Open notepad",
            "DELAY 500",
            "GUI r",
            "DELAY 200",
            "STRING notepad",
            "ENTER",
            "DELAY 1000",
            "STRING Hello from FlipperForge!",
        ])
        result = parse(script)
        assert result.ok
        assert len(result.commands) == 8
        assert _names(result) == [
            "REM", "DELAY", "GUI", "DELAY",
            "STRING", "ENTER", "DELAY", "STRING",
        ]

    def test_blank_lines_between_commands(self):
        script = "ENTER\n\n\nDELAY 100\n\nSTRING hi"
        result = parse(script)
        assert result.ok
        assert len(result.commands) == 3

    def test_line_numbers_correct(self):
        script = "\n\nENTER\n\nDELAY 100"
        result = parse(script)
        assert result.commands[0].line_number == 3
        assert result.commands[1].line_number == 5


# -- Error cases ------------------------------------------------------------

class TestErrors:
    def test_unknown_command(self):
        result = parse("FOOBAR")
        assert not result.ok
        assert "Unknown command" in result.errors[0].message
        assert result.errors[0].line_number == 1

    def test_typo_suggestion_dely(self):
        result = parse("DELY 100")
        assert not result.ok
        err = result.errors[0]
        assert err.suggestion
        assert "DELAY" in err.suggestion

    def test_typo_suggestion_strng(self):
        result = parse("STRNG hello")
        assert not result.ok
        err = result.errors[0]
        assert "STRING" in err.suggestion

    def test_typo_suggestion_entr(self):
        result = parse("ENTR")
        assert not result.ok
        assert "ENTER" in result.errors[0].suggestion

    def test_no_suggestion_for_gibberish(self):
        result = parse("XYZZY123")
        assert not result.ok
        assert result.errors[0].suggestion == ""

    def test_multiple_errors(self):
        script = "FOOBAR\nDELAY abc\nREPEAT 0"
        result = parse(script)
        assert len(result.errors) == 3
        assert result.errors[0].line_number == 1
        assert result.errors[1].line_number == 2
        assert result.errors[2].line_number == 3

    def test_error_among_valid_lines(self):
        script = "ENTER\nBADCMD\nDELAY 100"
        result = parse(script)
        assert len(result.errors) == 1
        assert result.errors[0].line_number == 2
        # Valid commands still parsed
        assert len(result.commands) == 2


# -- ParseResult.ok property ------------------------------------------------

class TestParseResultOk:
    def test_ok_when_no_errors(self):
        result = parse("ENTER")
        assert result.ok is True

    def test_not_ok_when_errors(self):
        result = parse("BADCMD")
        assert result.ok is False
