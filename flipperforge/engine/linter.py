"""Safety-focused linter for DuckyScript payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass

from flipperforge.engine.parser import parse


@dataclass
class Warning:
    line: int
    code: str
    message: str
    suggestion: str = ""


DANGEROUS_PATTERNS = [
    re.compile(r"\bformat\b.*[A-Za-z]:", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\bdel\s+/[fFsS]", re.IGNORECASE),
    re.compile(r"\bdiskpart\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\breg\s+delete\b", re.IGNORECASE),
    re.compile(r"\bbcdedit\b", re.IGNORECASE),
    re.compile(r"\bcipher\s+/w", re.IGNORECASE),
    re.compile(r"Remove-Item\s+.*-Recurse.*-Force", re.IGNORECASE),
    re.compile(r"Remove-Item\s+.*-Force.*-Recurse", re.IGNORECASE),
]

# Commands that open a shell/window
_SHELL_OPENERS = frozenset({"cmd", "powershell", "terminal", "bash", "sh"})
_CLOSE_PATTERNS = [
    re.compile(r"\bexit\b", re.IGNORECASE),
    re.compile(r"\bquit\b", re.IGNORECASE),
]


def lint(script: str, *, requires_confirmation: bool = False) -> list[Warning]:
    """Run safety lint rules on a DuckyScript string. Returns warnings."""
    result = parse(script)
    commands = result.commands
    warnings: list[Warning] = []

    if not commands:
        return warnings

    # Rule: NO_REM_HEADER -- first non-blank command should be REM
    if commands[0].name != "REM":
        warnings.append(
            Warning(
                line=commands[0].line_number,
                code="NO_REM_HEADER",
                message="Script has no REM comment header",
                suggestion="Add a REM line at the top describing this payload",
            )
        )

    # Rule: NO_INITIAL_DELAY -- first action command (after optional REM) should be DELAY
    first_action_idx = 0
    if commands[0].name == "REM":
        first_action_idx = 1 if len(commands) > 1 else 0
    if first_action_idx < len(commands) and commands[first_action_idx].name != "DELAY":
        warnings.append(
            Warning(
                line=commands[first_action_idx].line_number,
                code="NO_INITIAL_DELAY",
                message="Script has no initial DELAY before actions",
                suggestion="Add 'DELAY 500' or longer so the target is ready",
            )
        )

    # Rule: SHORT_DELAY -- DELAY < 100ms after GUI/modifier keys
    for i, cmd in enumerate(commands):
        if cmd.name in ("GUI", "CTRL", "ALT", "SHIFT") and i + 1 < len(commands):
            next_cmd = commands[i + 1]
            if next_cmd.name == "DELAY" and next_cmd.args and int(next_cmd.args) < 100:
                warnings.append(
                    Warning(
                        line=next_cmd.line_number,
                        code="SHORT_DELAY",
                        message=f"DELAY {next_cmd.args}ms after {cmd.name} may be too short",
                        suggestion="Use at least DELAY 100 after modifier keys",
                    )
                )

    # Rule: DANGEROUS_COMMAND -- check STRING args for dangerous patterns
    for cmd in commands:
        if cmd.name == "STRING" and cmd.args:
            for pattern in DANGEROUS_PATTERNS:
                if pattern.search(cmd.args):
                    warnings.append(
                        Warning(
                            line=cmd.line_number,
                            code="DANGEROUS_COMMAND",
                            message=f"Potentially dangerous command detected: {cmd.args[:60]}",
                            suggestion="Verify this is intentional and you have authorization",
                        )
                    )
                    break

    # Rule: MISSING_CONFIRMATION_PAUSE -- requires_confirmation but no long DELAY in first 5 lines
    if requires_confirmation:
        first_5 = commands[:5]
        has_long_delay = any(c.name == "DELAY" and c.args and int(c.args) >= 2000 for c in first_5)
        if not has_long_delay:
            warnings.append(
                Warning(
                    line=1,
                    code="MISSING_CONFIRMATION_PAUSE",
                    message="Template requires confirmation but no DELAY >= 2000ms in first 5 lines",
                    suggestion="Add a DELAY 3000 near the start so operator can abort",
                )
            )

    # Rule: NO_CLEANUP -- script opens a shell but never closes it
    opens_shell = False
    has_cleanup = False
    for cmd in commands:
        if cmd.name == "STRING" and cmd.args:
            text_lower = cmd.args.lower().strip()
            if any(text_lower == s for s in _SHELL_OPENERS):
                opens_shell = True
            if any(p.search(cmd.args) for p in _CLOSE_PATTERNS):
                has_cleanup = True
    # Also check for ALT F4 as cleanup
    for cmd in commands:
        if cmd.name == "ALT" and "F4" in cmd.args.upper():
            has_cleanup = True

    if opens_shell and not has_cleanup:
        warnings.append(
            Warning(
                line=commands[-1].line_number,
                code="NO_CLEANUP",
                message="Script opens a shell but does not close it (no 'exit' or ALT F4)",
                suggestion="Add 'STRING exit' and 'ENTER' or 'ALT F4' at the end",
            )
        )

    return warnings
