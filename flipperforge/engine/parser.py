"""
DuckyScript parser for Flipper Zero BadUSB payloads.

Tokenizes and validates Flipper-flavored DuckyScript, returning structured
command lists with line-level error reporting and typo suggestions.

Author: TiltedLunar123 <hilgendorfjude@gmail.com>
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

# -- Valid commands and keys ------------------------------------------------

SINGLE_KEYS = frozenset(
    {
        "ENTER",
        "TAB",
        "ESCAPE",
        "SPACE",
        "BACKSPACE",
        "DELETE",
        "HOME",
        "END",
        "PAGEUP",
        "PAGEDOWN",
        "UPARROW",
        "DOWNARROW",
        "LEFTARROW",
        "RIGHTARROW",
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
    }
)

FUNCTION_KEYS = frozenset({f"F{n}" for n in range(1, 13)})

MODIFIER_KEYS = frozenset(
    {
        "GUI",
        "CTRL",
        "ALT",
        "SHIFT",
        "CONTROL",
        "WINDOWS",
        "COMMAND",
    }
)

# Commands that require an argument on the same line
ARG_COMMANDS = frozenset(
    {
        "STRING",
        "STRINGLN",
        "DELAY",
        "DEFAULTDELAY",
        "DEFAULT_DELAY",
        "REPEAT",
        "REM",
    }
)

# Every keyword the parser understands (used for typo matching)
ALL_KEYWORDS = SINGLE_KEYS | FUNCTION_KEYS | MODIFIER_KEYS | ARG_COMMANDS


# -- Data classes -----------------------------------------------------------


@dataclass
class Command:
    """A single parsed DuckyScript command."""

    line_number: int
    name: str
    args: str = ""


@dataclass
class ParseError:
    """An error encountered during parsing."""

    line_number: int
    message: str
    suggestion: str = ""


@dataclass
class ParseResult:
    """Aggregated result of parsing a DuckyScript payload."""

    commands: list[Command] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# -- Helpers ----------------------------------------------------------------


def _suggest(token: str) -> str:
    """Return a close-match suggestion for *token*, or empty string."""
    matches = difflib.get_close_matches(
        token.upper(),
        sorted(ALL_KEYWORDS),
        n=1,
        cutoff=0.6,
    )
    return matches[0] if matches else ""


# -- Parser -----------------------------------------------------------------


def parse(script: str) -> ParseResult:
    """Parse a DuckyScript payload string and return a ParseResult.

    Parameters
    ----------
    script:
        The raw DuckyScript text (may contain multiple lines).

    Returns
    -------
    ParseResult
        Contains a list of Command objects and any ParseError objects.
    """
    result = ParseResult()

    for line_number, raw_line in enumerate(script.splitlines(), start=1):
        line = raw_line.strip()

        # Skip blank lines
        if not line:
            continue

        token = line.split()[0].upper()
        rest = line[len(line.split()[0]) :].strip() if len(line.split()) > 1 else ""

        # -- REM (comment) --------------------------------------------------
        if token == "REM":
            result.commands.append(Command(line_number, "REM", rest))
            continue

        # -- STRING / STRINGLN ----------------------------------------------
        if token in ("STRING", "STRINGLN"):
            # Everything after the keyword is the payload (preserve original)
            text = raw_line.strip()[len(token) :]
            # There must be at least a space separator and some text
            if not text or not text.lstrip(" "):
                result.errors.append(
                    ParseError(
                        line_number,
                        f"{token} requires text argument",
                    )
                )
                continue
            # Strip only the first separating space
            if text.startswith(" "):
                text = text[1:]
            if not text:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"{token} requires text argument",
                    )
                )
                continue
            result.commands.append(Command(line_number, token, text))
            continue

        # -- DEFAULTDELAY / DEFAULT_DELAY -----------------------------------
        if token in ("DEFAULTDELAY", "DEFAULT_DELAY"):
            if not rest:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"{token} requires a numeric argument",
                    )
                )
                continue
            try:
                value = int(rest)
            except ValueError:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"{token} value must be a non-negative integer, got '{rest}'",
                    )
                )
                continue
            if value < 0:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"{token} value must be non-negative, got {value}",
                    )
                )
                continue
            result.commands.append(Command(line_number, token, rest))
            continue

        # -- DELAY ----------------------------------------------------------
        if token == "DELAY":
            if not rest:
                result.errors.append(
                    ParseError(
                        line_number,
                        "DELAY requires a numeric argument",
                    )
                )
                continue
            try:
                value = int(rest)
            except ValueError:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"DELAY value must be a non-negative integer, got '{rest}'",
                    )
                )
                continue
            if value < 0:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"DELAY value must be non-negative, got {value}",
                    )
                )
                continue
            result.commands.append(Command(line_number, "DELAY", rest))
            continue

        # -- REPEAT ---------------------------------------------------------
        if token == "REPEAT":
            if not rest:
                result.errors.append(
                    ParseError(
                        line_number,
                        "REPEAT requires a positive integer argument",
                    )
                )
                continue
            try:
                value = int(rest)
            except ValueError:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"REPEAT value must be a positive integer, got '{rest}'",
                    )
                )
                continue
            if value <= 0:
                result.errors.append(
                    ParseError(
                        line_number,
                        f"REPEAT value must be positive, got {value}",
                    )
                )
                continue
            result.commands.append(Command(line_number, "REPEAT", rest))
            continue

        # -- Single keys (ENTER, TAB, arrow keys, etc.) ---------------------
        if token in SINGLE_KEYS:
            result.commands.append(Command(line_number, token))
            continue

        # -- Function keys (F1-F12) -----------------------------------------
        if token in FUNCTION_KEYS:
            result.commands.append(Command(line_number, token))
            continue

        # -- Modifier combos (GUI r, CTRL ALT DELETE, etc.) -----------------
        if token in MODIFIER_KEYS:
            result.commands.append(Command(line_number, token, rest))
            continue

        # -- Unknown command - offer a suggestion if possible ---------------
        suggestion = _suggest(token)
        msg = f"Unknown command: {token}"
        result.errors.append(
            ParseError(
                line_number,
                msg,
                suggestion=f"Did you mean {suggestion}?" if suggestion else "",
            )
        )

    return result
