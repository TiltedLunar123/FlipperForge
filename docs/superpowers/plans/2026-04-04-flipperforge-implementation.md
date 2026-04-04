# FlipperForge Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-first Python tool for creating, validating, and deploying BadUSB payloads to Flipper Zero with MITRE ATT&CK tagging.

**Architecture:** CLI (Click) wraps an engine layer (parser, linter, compiler) that processes YAML templates into DuckyScript payloads. A serial module deploys to Flipper Zero over USB. A build cache persists state between CLI invocations. MITRE ATT&CK metadata enriches every payload.

**Tech Stack:** Python 3.11+, Click, Rich, PySerial, Jinja2, PyYAML, pytest

**Spec:** `docs/superpowers/specs/2026-04-04-flipperforge-design.md`

---

## Chunk 1: Project Scaffolding

### Task 1: Create pyproject.toml and package structure

**Files:**
- Create: `pyproject.toml`
- Create: `flipperforge/__init__.py`
- Create: `flipperforge/engine/__init__.py`
- Create: `flipperforge/templates/__init__.py`
- Create: `flipperforge/deploy/__init__.py`
- Create: `flipperforge/library/__init__.py`
- Create: `flipperforge/mitre/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/engine/__init__.py`
- Create: `templates/.gitkeep`
- Create: `payloads/.gitkeep`
- Create: `.gitignore`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "flipperforge"
version = "0.1.0"
description = "BadUSB payload workshop for Flipper Zero"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
authors = [{name = "TiltedLunar123", email = "hilgendorfjude@gmail.com"}]
keywords = ["flipper-zero", "badusb", "duckyscript", "pentesting", "mitre-attack"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Information Technology",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Topic :: Security",
]
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "pyserial>=3.5",
    "jinja2>=3.1",
    "pyyaml>=6.0",
]

[project.scripts]
flipperforge = "flipperforge.cli:main"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

- [ ] **Step 2: Create __init__.py files**

`flipperforge/__init__.py`:
```python
"""FlipperForge  - BadUSB payload workshop for Flipper Zero."""

__version__ = "0.1.0"
```

All other `__init__.py` files (engine, templates, deploy, library, mitre, tests, tests/engine): empty files.

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.flipperforge/
.venv/
*.egg
.pytest_cache/
```

- [ ] **Step 4: Create placeholder files**

`templates/.gitkeep` and `payloads/.gitkeep`: empty files.

- [ ] **Step 5: Install in dev mode and verify**

Run: `pip install -e ".[dev]"`
Expected: Successful install, `flipperforge` command available (will error since cli.py doesn't exist yet  - that's fine).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: scaffold project structure and packaging"
```

---

## Chunk 2: DuckyScript Parser

### Task 2: DuckyScript Parser

**Files:**
- Create: `flipperforge/engine/parser.py`
- Create: `tests/engine/test_parser.py`

The parser tokenizes DuckyScript lines and validates syntax. It returns a list of parsed commands or a list of errors with line numbers.

- [ ] **Step 1: Write parser tests**

`tests/engine/test_parser.py`:
```python
import pytest
from flipperforge.engine.parser import parse, ParseError


class TestParseValidScripts:
    def test_empty_script(self):
        result = parse("")
        assert result.commands == []
        assert result.errors == []

    def test_rem_comment(self):
        result = parse("REM This is a comment")
        assert len(result.commands) == 1
        assert result.commands[0].type == "REM"
        assert result.commands[0].arg == "This is a comment"

    def test_string_command(self):
        result = parse("STRING Hello World")
        assert result.commands[0].type == "STRING"
        assert result.commands[0].arg == "Hello World"

    def test_delay_command(self):
        result = parse("DELAY 500")
        assert result.commands[0].type == "DELAY"
        assert result.commands[0].arg == "500"

    def test_single_keys(self):
        for key in ["ENTER", "TAB", "ESCAPE", "SPACE", "BACKSPACE", "DELETE",
                     "UP", "DOWN", "LEFT", "RIGHT", "HOME", "END",
                     "PAGEUP", "PAGEDOWN"]:
            result = parse(key)
            assert result.commands[0].type == key, f"Failed for {key}"

    def test_function_keys(self):
        for i in range(1, 13):
            result = parse(f"F{i}")
            assert result.commands[0].type == f"F{i}"

    def test_modifier_combos(self):
        result = parse("CTRL ALT DELETE")
        cmd = result.commands[0]
        assert cmd.type == "CTRL"
        assert cmd.arg == "ALT DELETE"

    def test_gui_key(self):
        result = parse("GUI r")
        assert result.commands[0].type == "GUI"
        assert result.commands[0].arg == "r"

    def test_repeat(self):
        result = parse("REPEAT 3")
        assert result.commands[0].type == "REPEAT"
        assert result.commands[0].arg == "3"

    def test_multiline_script(self):
        script = "REM Test\nDELAY 500\nGUI r\nDELAY 200\nSTRING cmd\nENTER"
        result = parse(script)
        assert len(result.commands) == 6
        assert result.errors == []

    def test_blank_lines_ignored(self):
        result = parse("REM start\n\n\nDELAY 100\n\n")
        assert len(result.commands) == 2


class TestParseErrors:
    def test_unknown_command(self):
        result = parse("FOOBAR")
        assert len(result.errors) == 1
        assert result.errors[0].line == 1
        assert "Unknown" in result.errors[0].message

    def test_typo_suggestion(self):
        result = parse("CNTRL c")
        assert len(result.errors) == 1
        assert "CTRL" in result.errors[0].message

    def test_string_no_arg(self):
        result = parse("STRING")
        assert len(result.errors) == 1
        assert "requires text" in result.errors[0].message.lower()

    def test_delay_not_numeric(self):
        result = parse("DELAY abc")
        assert len(result.errors) == 1

    def test_delay_negative(self):
        result = parse("DELAY -100")
        assert len(result.errors) == 1

    def test_repeat_not_numeric(self):
        result = parse("REPEAT abc")
        assert len(result.errors) == 1

    def test_multiple_errors(self):
        script = "FOOBAR\nSTRING\nDELAY abc"
        result = parse(script)
        assert len(result.errors) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/engine/test_parser.py -v`
Expected: FAIL  - `flipperforge.engine.parser` has no `parse` function

- [ ] **Step 3: Implement parser**

`flipperforge/engine/parser.py`:
```python
"""DuckyScript parser and validator for Flipper Zero BadUSB payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import get_close_matches


SINGLE_KEYS = frozenset({
    "ENTER", "TAB", "ESCAPE", "SPACE", "BACKSPACE", "DELETE",
    "UP", "DOWN", "LEFT", "RIGHT", "HOME", "END",
    "PAGEUP", "PAGEDOWN",
    "F1", "F2", "F3", "F4", "F5", "F6",
    "F7", "F8", "F9", "F10", "F11", "F12",
})

MODIFIER_KEYS = frozenset({"GUI", "CTRL", "ALT", "SHIFT"})

COMMANDS_WITH_ARG = frozenset({"STRING", "DELAY", "REPEAT", "REM"})

ALL_KEYWORDS = SINGLE_KEYS | MODIFIER_KEYS | COMMANDS_WITH_ARG


@dataclass
class Command:
    type: str
    arg: str | None = None
    line: int = 0


@dataclass
class Error:
    line: int
    message: str


@dataclass
class ParseResult:
    commands: list[Command] = field(default_factory=list)
    errors: list[Error] = field(default_factory=list)


def parse(script: str) -> ParseResult:
    """Parse a DuckyScript string and return commands + errors."""
    result = ParseResult()
    lines = script.split("\n") if script.strip() else []

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(None, 1)
        keyword = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else None

        # REM  - comment, preserve original case of arg
        if keyword == "REM":
            result.commands.append(Command(type="REM", arg=arg or "", line=line_num))
            continue

        # STRING  - requires text argument
        if keyword == "STRING":
            if arg is None:
                result.errors.append(Error(line=line_num, message="STRING requires text after it"))
                continue
            result.commands.append(Command(type="STRING", arg=arg, line=line_num))
            continue

        # DELAY  - requires numeric argument
        if keyword == "DELAY":
            if arg is None or not arg.strip().lstrip("-").isdigit():
                result.errors.append(Error(line=line_num, message=f"DELAY requires a numeric value, got: {arg!r}"))
                continue
            if int(arg.strip()) < 0:
                result.errors.append(Error(line=line_num, message=f"DELAY cannot be negative: {arg}"))
                continue
            result.commands.append(Command(type="DELAY", arg=arg.strip(), line=line_num))
            continue

        # REPEAT  - requires numeric argument
        if keyword == "REPEAT":
            if arg is None or not arg.strip().isdigit():
                result.errors.append(Error(line=line_num, message=f"REPEAT requires a positive integer, got: {arg!r}"))
                continue
            result.commands.append(Command(type="REPEAT", arg=arg.strip(), line=line_num))
            continue

        # Single keys (ENTER, TAB, etc.)
        if keyword in SINGLE_KEYS:
            result.commands.append(Command(type=keyword, arg=arg, line=line_num))
            continue

        # Modifier keys (GUI, CTRL, ALT, SHIFT)
        if keyword in MODIFIER_KEYS:
            result.commands.append(Command(type=keyword, arg=arg or "", line=line_num))
            continue

        # Unknown command  - suggest close matches
        suggestions = get_close_matches(keyword, ALL_KEYWORDS, n=1, cutoff=0.6)
        hint = f" Did you mean: {suggestions[0]}?" if suggestions else ""
        result.errors.append(Error(line=line_num, message=f"Unknown command: {keyword}.{hint}"))

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/engine/test_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/engine/parser.py tests/engine/test_parser.py
git commit -m "feat: add DuckyScript parser with validation"
```

---

## Chunk 3: DuckyScript Linter

### Task 3: Safety Linter

**Files:**
- Create: `flipperforge/engine/linter.py`
- Create: `tests/engine/test_linter.py`

- [ ] **Step 1: Write linter tests**

`tests/engine/test_linter.py`:
```python
import pytest
from flipperforge.engine.linter import lint, Warning


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/engine/test_linter.py -v`
Expected: FAIL

- [ ] **Step 3: Implement linter**

`flipperforge/engine/linter.py`:
```python
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
]


def lint(script: str, *, requires_confirmation: bool = False) -> list[Warning]:
    """Run safety lint rules on a DuckyScript string. Returns warnings."""
    result = parse(script)
    commands = result.commands
    warnings: list[Warning] = []

    if not commands:
        return warnings

    # Rule: NO_REM_HEADER  - first non-blank command should be REM
    if commands[0].type != "REM":
        warnings.append(Warning(
            line=commands[0].line,
            code="NO_REM_HEADER",
            message="Script has no REM comment header",
            suggestion="Add a REM line at the top describing this payload",
        ))

    # Rule: NO_INITIAL_DELAY  - first command (or second if REM) should be DELAY
    first_action_idx = 0
    if commands[0].type == "REM":
        first_action_idx = 1 if len(commands) > 1 else 0
    if first_action_idx < len(commands) and commands[first_action_idx].type != "DELAY":
        warnings.append(Warning(
            line=commands[first_action_idx].line,
            code="NO_INITIAL_DELAY",
            message="Script has no initial DELAY before actions",
            suggestion="Add 'DELAY 500' or longer so the target is ready",
        ))

    # Rule: SHORT_DELAY  - DELAY < 100ms after GUI/modifier
    for i, cmd in enumerate(commands):
        if cmd.type in ("GUI", "CTRL", "ALT", "SHIFT") and i + 1 < len(commands):
            next_cmd = commands[i + 1]
            if next_cmd.type == "DELAY" and next_cmd.arg and int(next_cmd.arg) < 100:
                warnings.append(Warning(
                    line=next_cmd.line,
                    code="SHORT_DELAY",
                    message=f"DELAY {next_cmd.arg}ms after {cmd.type} may be too short",
                    suggestion="Use at least DELAY 100 after modifier keys",
                ))

    # Rule: DANGEROUS_COMMAND  - check STRING args for dangerous patterns
    for cmd in commands:
        if cmd.type == "STRING" and cmd.arg:
            for pattern in DANGEROUS_PATTERNS:
                if pattern.search(cmd.arg):
                    warnings.append(Warning(
                        line=cmd.line,
                        code="DANGEROUS_COMMAND",
                        message=f"Potentially dangerous command detected: {cmd.arg[:60]}",
                        suggestion="Verify this is intentional and you have authorization",
                    ))
                    break

    # Rule: MISSING_CONFIRMATION_PAUSE
    if requires_confirmation:
        first_5 = commands[:5]
        has_long_delay = any(
            c.type == "DELAY" and c.arg and int(c.arg) >= 2000
            for c in first_5
        )
        if not has_long_delay:
            warnings.append(Warning(
                line=1,
                code="MISSING_CONFIRMATION_PAUSE",
                message="Template requires confirmation but no DELAY >= 2000ms in first 5 lines",
                suggestion="Add a DELAY 3000 near the start so operator can abort",
            ))

    return warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/engine/test_linter.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/engine/linter.py tests/engine/test_linter.py
git commit -m "feat: add safety-focused DuckyScript linter"
```

---

## Chunk 4: Template Loader

### Task 4: YAML Template Loader

**Files:**
- Create: `flipperforge/templates/loader.py`
- Create: `tests/test_loader.py`
- Create: `tests/fixtures/` (test templates)

- [ ] **Step 1: Create test fixture template**

`tests/fixtures/test-template.yaml`:
```yaml
name: test-payload
description: A test payload for unit tests
author: test
version: "1.0"
mitre:
  tactic: discovery
  technique: T1082
platform: windows
parameters:
  - name: msg
    type: string
    default: "hello"
    description: "Message to type"
  - name: delay_ms
    type: integer
    default: 500
    description: "Delay in ms"
  - name: verbose
    type: boolean
    default: false
    description: "Verbose mode"
  - name: shell
    type: choice
    default: "cmd"
    choices: ["cmd", "powershell", "terminal"]
    description: "Shell to open"
safety:
  requires_confirmation: false
  scope_note: "Test only"
script: |
  REM Test payload
  DELAY {{ delay_ms }}
  GUI r
  DELAY 300
  STRING {{ msg }}
  ENTER
```

- [ ] **Step 2: Write loader tests**

`tests/test_loader.py`:
```python
import pytest
from pathlib import Path
from flipperforge.templates.loader import load_template, discover_templates, TemplateError

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadTemplate:
    def test_load_valid_template(self):
        t = load_template(FIXTURES / "test-template.yaml")
        assert t.name == "test-payload"
        assert t.mitre.tactic == "discovery"
        assert t.mitre.technique == "T1082"
        assert len(t.parameters) == 4
        assert t.script.startswith("REM Test payload")

    def test_parameter_types(self):
        t = load_template(FIXTURES / "test-template.yaml")
        types = {p.name: p.type for p in t.parameters}
        assert types == {"msg": "string", "delay_ms": "integer", "verbose": "boolean", "shell": "choice"}

    def test_choice_parameter_has_choices(self):
        t = load_template(FIXTURES / "test-template.yaml")
        shell_param = [p for p in t.parameters if p.name == "shell"][0]
        assert shell_param.choices == ["cmd", "powershell", "terminal"]

    def test_safety_metadata(self):
        t = load_template(FIXTURES / "test-template.yaml")
        assert t.safety.requires_confirmation is False
        assert t.safety.scope_note == "Test only"

    def test_missing_file_raises(self):
        with pytest.raises(TemplateError, match="not found"):
            load_template(FIXTURES / "nonexistent.yaml")

    def test_invalid_yaml_raises(self):
        bad = FIXTURES / "bad.yaml"
        bad.write_text(": invalid: yaml: [")
        try:
            with pytest.raises(TemplateError):
                load_template(bad)
        finally:
            bad.unlink()


class TestDiscoverTemplates:
    def test_discover_in_fixtures(self):
        templates = discover_templates(FIXTURES)
        names = [t.name for t in templates]
        assert "test-payload" in names
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL

- [ ] **Step 4: Implement loader**

`flipperforge/templates/loader.py`:
```python
"""YAML template loader and discovery for FlipperForge."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class TemplateError(Exception):
    """Raised when a template cannot be loaded or is invalid."""


@dataclass
class Parameter:
    name: str
    type: str
    default: str | int | bool | None = None
    description: str = ""
    choices: list[str] = field(default_factory=list)
    min: int | None = None
    max: int | None = None


@dataclass
class MitreInfo:
    tactic: str = ""
    technique: str = ""
    subtechnique: str = ""


@dataclass
class SafetyInfo:
    requires_confirmation: bool = False
    scope_note: str = ""


@dataclass
class Template:
    name: str
    description: str
    author: str
    version: str
    mitre: MitreInfo
    platform: str
    parameters: list[Parameter]
    safety: SafetyInfo
    script: str
    source_path: Path | None = None


def load_template(path: Path) -> Template:
    """Load a template from a YAML file."""
    if not path.exists():
        raise TemplateError(f"Template not found: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise TemplateError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise TemplateError(f"Template must be a YAML mapping: {path}")

    mitre_data = data.get("mitre", {})
    safety_data = data.get("safety", {})

    parameters = []
    for p in data.get("parameters", []):
        parameters.append(Parameter(
            name=p["name"],
            type=p["type"],
            default=p.get("default"),
            description=p.get("description", ""),
            choices=p.get("choices", []),
            min=p.get("min"),
            max=p.get("max"),
        ))

    return Template(
        name=data.get("name", path.stem),
        description=data.get("description", ""),
        author=data.get("author", ""),
        version=str(data.get("version", "0.1")),
        mitre=MitreInfo(
            tactic=mitre_data.get("tactic", ""),
            technique=mitre_data.get("technique", ""),
            subtechnique=mitre_data.get("subtechnique", ""),
        ),
        platform=data.get("platform", ""),
        parameters=parameters,
        safety=SafetyInfo(
            requires_confirmation=safety_data.get("requires_confirmation", False),
            scope_note=safety_data.get("scope_note", ""),
        ),
        script=data.get("script", ""),
        source_path=path,
    )


def discover_templates(directory: Path) -> list[Template]:
    """Recursively discover and load all .yaml templates in a directory."""
    templates = []
    for yaml_file in sorted(directory.rglob("*.yaml")):
        try:
            templates.append(load_template(yaml_file))
        except TemplateError:
            continue
    return templates
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_loader.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add flipperforge/templates/loader.py tests/test_loader.py tests/fixtures/
git commit -m "feat: add YAML template loader with discovery"
```

---

## Chunk 5: Compiler

### Task 5: Template Compiler (Jinja2 + Validation)

**Files:**
- Create: `flipperforge/engine/compiler.py`
- Create: `tests/engine/test_compiler.py`

- [ ] **Step 1: Write compiler tests**

`tests/engine/test_compiler.py`:
```python
import pytest
from pathlib import Path
from flipperforge.engine.compiler import compile_template, CompileError
from flipperforge.templates.loader import load_template

FIXTURES = Path(__file__).parent.parent / "fixtures"


class TestCompileTemplate:
    def test_compile_with_defaults(self):
        t = load_template(FIXTURES / "test-template.yaml")
        result = compile_template(t)
        assert "DELAY 500" in result.script
        assert "STRING hello" in result.script
        assert result.errors == []

    def test_compile_with_custom_params(self):
        t = load_template(FIXTURES / "test-template.yaml")
        result = compile_template(t, params={"msg": "world", "delay_ms": 1000})
        assert "DELAY 1000" in result.script
        assert "STRING world" in result.script

    def test_compile_validates_integer_type(self):
        t = load_template(FIXTURES / "test-template.yaml")
        with pytest.raises(CompileError, match="integer"):
            compile_template(t, params={"delay_ms": "not_a_number"})

    def test_compile_validates_choice_type(self):
        t = load_template(FIXTURES / "test-template.yaml")
        with pytest.raises(CompileError, match="choice"):
            compile_template(t, params={"shell": "zsh"})

    def test_compile_validates_string_length(self):
        t = load_template(FIXTURES / "test-template.yaml")
        with pytest.raises(CompileError, match="500"):
            compile_template(t, params={"msg": "x" * 501})

    def test_compile_result_has_warnings(self):
        t = load_template(FIXTURES / "test-template.yaml")
        result = compile_template(t)
        # Our test template has a clean script, so no warnings expected
        assert isinstance(result.warnings, list)

    def test_compile_result_has_metadata(self):
        t = load_template(FIXTURES / "test-template.yaml")
        result = compile_template(t)
        assert result.template_name == "test-payload"
        assert result.mitre_tactic == "discovery"
        assert result.mitre_technique == "T1082"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/engine/test_compiler.py -v`
Expected: FAIL

- [ ] **Step 3: Implement compiler**

`flipperforge/engine/compiler.py`:
```python
"""Compile templates into final DuckyScript payloads."""

from __future__ import annotations

from dataclasses import dataclass, field

from jinja2 import Template as Jinja2Template

from flipperforge.engine.linter import Warning, lint
from flipperforge.engine.parser import parse
from flipperforge.templates.loader import Template


class CompileError(Exception):
    """Raised when template compilation fails."""


@dataclass
class CompileResult:
    script: str
    template_name: str
    mitre_tactic: str
    mitre_technique: str
    mitre_subtechnique: str
    params_used: dict
    errors: list = field(default_factory=list)
    warnings: list[Warning] = field(default_factory=list)


def _validate_params(template: Template, params: dict) -> dict:
    """Validate and merge params with defaults. Raises CompileError on invalid."""
    merged = {}
    for p in template.parameters:
        value = params.get(p.name, p.default)

        if p.type == "integer":
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise CompileError(
                    f"Parameter '{p.name}' must be an integer, got: {value!r}"
                )
            if p.min is not None and value < p.min:
                raise CompileError(f"Parameter '{p.name}' minimum is {p.min}, got: {value}")
            if p.max is not None and value > p.max:
                raise CompileError(f"Parameter '{p.name}' maximum is {p.max}, got: {value}")

        elif p.type == "string":
            value = str(value) if value is not None else ""
            if len(value) > 500:
                raise CompileError(
                    f"Parameter '{p.name}' exceeds 500 char limit ({len(value)} chars)"
                )

        elif p.type == "boolean":
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            value = str(bool(value)).lower()

        elif p.type == "choice":
            if value not in p.choices:
                raise CompileError(
                    f"Parameter '{p.name}' must be one of {p.choices} (choice), got: {value!r}"
                )

        merged[p.name] = value

    return merged


def compile_template(template: Template, *, params: dict | None = None) -> CompileResult:
    """Compile a template with parameters into a final DuckyScript payload."""
    merged_params = _validate_params(template, params or {})

    # Render Jinja2
    jinja_tmpl = Jinja2Template(template.script)
    rendered = jinja_tmpl.render(**merged_params)

    # Parse to check for errors
    parse_result = parse(rendered)

    # Lint for warnings
    warnings = lint(
        rendered,
        requires_confirmation=template.safety.requires_confirmation,
    )

    return CompileResult(
        script=rendered.strip(),
        template_name=template.name,
        mitre_tactic=template.mitre.tactic,
        mitre_technique=template.mitre.technique,
        mitre_subtechnique=template.mitre.subtechnique,
        params_used=merged_params,
        errors=[{"line": e.line, "message": e.message} for e in parse_result.errors],
        warnings=warnings,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/engine/test_compiler.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/engine/compiler.py tests/engine/test_compiler.py
git commit -m "feat: add template compiler with param validation"
```

---

## Chunk 6: Build Cache + MITRE Mapper

### Task 6: Build Cache

**Files:**
- Create: `flipperforge/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write cache tests**

`tests/test_cache.py`:
```python
import json
import pytest
from pathlib import Path
from flipperforge.cache import BuildCache


class TestBuildCache:
    def test_save_and_load(self, tmp_path):
        cache = BuildCache(tmp_path / ".flipperforge" / "cache")
        cache.save(
            script="DELAY 500\nGUI r",
            meta={"template_name": "test", "mitre_tactic": "discovery"},
        )
        loaded = cache.load()
        assert loaded["script"] == "DELAY 500\nGUI r"
        assert loaded["meta"]["template_name"] == "test"

    def test_load_empty_returns_none(self, tmp_path):
        cache = BuildCache(tmp_path / ".flipperforge" / "cache")
        assert cache.load() is None

    def test_save_creates_directory(self, tmp_path):
        cache_dir = tmp_path / ".flipperforge" / "cache"
        cache = BuildCache(cache_dir)
        cache.save(script="ENTER", meta={})
        assert cache_dir.exists()

    def test_clear(self, tmp_path):
        cache = BuildCache(tmp_path / ".flipperforge" / "cache")
        cache.save(script="ENTER", meta={})
        cache.clear()
        assert cache.load() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL

- [ ] **Step 3: Implement cache**

`flipperforge/cache.py`:
```python
"""Build cache for persisting compiled payloads between CLI invocations."""

from __future__ import annotations

import json
from pathlib import Path


class BuildCache:
    """File-based cache for the last compiled payload."""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path.cwd() / ".flipperforge" / "cache"
        self.cache_dir = cache_dir
        self._script_path = cache_dir / "last_build.txt"
        self._meta_path = cache_dir / "last_build_meta.json"

    def save(self, script: str, meta: dict) -> None:
        """Save a compiled payload to the cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._script_path.write_text(script, encoding="utf-8")
        self._meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def load(self) -> dict | None:
        """Load the last compiled payload. Returns None if no cache."""
        if not self._script_path.exists():
            return None
        return {
            "script": self._script_path.read_text(encoding="utf-8"),
            "meta": json.loads(self._meta_path.read_text(encoding="utf-8")),
        }

    def clear(self) -> None:
        """Delete cached payload."""
        self._script_path.unlink(missing_ok=True)
        self._meta_path.unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cache.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/cache.py tests/test_cache.py
git commit -m "feat: add build cache for CLI state persistence"
```

### Task 7: MITRE ATT&CK Mapper

**Files:**
- Create: `flipperforge/mitre/mapper.py`
- Create: `flipperforge/mitre/attack_data.json`
- Create: `tests/test_mitre.py`

- [ ] **Step 1: Create ATT&CK data snapshot**

`flipperforge/mitre/attack_data.json`  - a curated subset of techniques used by the built-in templates:

```json
{
  "techniques": {
    "T1082": {
      "name": "System Information Discovery",
      "tactic": "discovery",
      "description": "Adversaries may attempt to get detailed information about the operating system and hardware."
    },
    "T1555": {
      "name": "Credentials from Password Stores",
      "tactic": "credential-access",
      "description": "Adversaries may search for common password storage locations to obtain user credentials."
    },
    "T1555.005": {
      "name": "Password Managers",
      "tactic": "credential-access",
      "parent": "T1555",
      "description": "Adversaries may acquire user credentials from third-party password managers."
    },
    "T1059": {
      "name": "Command and Scripting Interpreter",
      "tactic": "execution",
      "description": "Adversaries may abuse command and script interpreters to execute commands."
    },
    "T1059.001": {
      "name": "PowerShell",
      "tactic": "execution",
      "parent": "T1059",
      "description": "Adversaries may abuse PowerShell commands and scripts for execution."
    },
    "T1053": {
      "name": "Scheduled Task/Job",
      "tactic": "persistence",
      "description": "Adversaries may abuse task scheduling functionality to facilitate execution."
    },
    "T1053.005": {
      "name": "Scheduled Task",
      "tactic": "persistence",
      "parent": "T1053",
      "description": "Adversaries may abuse the Windows Task Scheduler to perform task scheduling for execution."
    },
    "T1005": {
      "name": "Data from Local System",
      "tactic": "exfiltration",
      "description": "Adversaries may search local system sources to find files of interest and sensitive data."
    },
    "T1046": {
      "name": "Network Service Discovery",
      "tactic": "discovery",
      "description": "Adversaries may attempt to get a listing of services running on remote hosts."
    }
  }
}
```

- [ ] **Step 2: Write mapper tests**

`tests/test_mitre.py`:
```python
import pytest
from flipperforge.mitre.mapper import MitreMapper


class TestMitreMapper:
    def setup_method(self):
        self.mapper = MitreMapper()

    def test_lookup_technique(self):
        info = self.mapper.lookup("T1082")
        assert info is not None
        assert info["name"] == "System Information Discovery"
        assert info["tactic"] == "discovery"

    def test_lookup_subtechnique(self):
        info = self.mapper.lookup("T1059.001")
        assert info is not None
        assert info["name"] == "PowerShell"
        assert info["parent"] == "T1059"

    def test_lookup_unknown(self):
        assert self.mapper.lookup("T9999") is None

    def test_get_by_tactic(self):
        techniques = self.mapper.get_by_tactic("discovery")
        ids = [t["id"] for t in techniques]
        assert "T1082" in ids
        assert "T1046" in ids

    def test_get_by_tactic_empty(self):
        assert self.mapper.get_by_tactic("nonexistent") == []

    def test_all_tactics(self):
        tactics = self.mapper.all_tactics()
        assert "discovery" in tactics
        assert "execution" in tactics
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_mitre.py -v`
Expected: FAIL

- [ ] **Step 4: Implement mapper**

`flipperforge/mitre/mapper.py`:
```python
"""MITRE ATT&CK technique lookup and filtering."""

from __future__ import annotations

import json
from pathlib import Path


class MitreMapper:
    """Lookup and filter MITRE ATT&CK techniques from a local data snapshot."""

    def __init__(self, data_path: Path | None = None):
        if data_path is None:
            data_path = Path(__file__).parent / "attack_data.json"
        raw = json.loads(data_path.read_text(encoding="utf-8"))
        self._techniques: dict[str, dict] = raw["techniques"]

    def lookup(self, technique_id: str) -> dict | None:
        """Look up a technique by ID. Returns None if not found."""
        return self._techniques.get(technique_id)

    def get_by_tactic(self, tactic: str) -> list[dict]:
        """Return all techniques for a given tactic."""
        results = []
        for tid, info in self._techniques.items():
            if info.get("tactic") == tactic:
                results.append({**info, "id": tid})
        return results

    def all_tactics(self) -> list[str]:
        """Return all unique tactic names."""
        return sorted({info["tactic"] for info in self._techniques.values()})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_mitre.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add flipperforge/mitre/ tests/test_mitre.py
git commit -m "feat: add MITRE ATT&CK mapper with technique lookup"
```

---

## Chunk 7: Library Manager

### Task 8: Payload Library Manager

**Files:**
- Create: `flipperforge/library/manager.py`
- Create: `tests/test_library.py`

- [ ] **Step 1: Write library tests**

`tests/test_library.py`:
```python
import pytest
from flipperforge.library.manager import PayloadLibrary


class TestPayloadLibrary:
    def test_save_and_list(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        lib.save("recon", script="DELAY 500\nGUI r", meta={"mitre_tactic": "discovery", "mitre_technique": "T1082"})
        items = lib.list_all()
        assert len(items) == 1
        assert items[0]["name"] == "recon"

    def test_load(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        lib.save("test1", script="ENTER", meta={"mitre_tactic": "execution"})
        loaded = lib.load("test1")
        assert loaded["script"] == "ENTER"
        assert loaded["meta"]["mitre_tactic"] == "execution"

    def test_load_not_found(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        assert lib.load("nope") is None

    def test_delete(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        lib.save("deleteme", script="ENTER", meta={})
        assert lib.delete("deleteme") is True
        assert lib.load("deleteme") is None

    def test_delete_not_found(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        assert lib.delete("nope") is False

    def test_search_by_name(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        lib.save("wifi-grab", script="ENTER", meta={"mitre_tactic": "credential-access"})
        lib.save("recon-scan", script="ENTER", meta={"mitre_tactic": "discovery"})
        results = lib.search("wifi")
        assert len(results) == 1
        assert results[0]["name"] == "wifi-grab"

    def test_search_by_tactic(self, tmp_path):
        lib = PayloadLibrary(tmp_path / "payloads")
        lib.save("p1", script="ENTER", meta={"mitre_tactic": "discovery"})
        lib.save("p2", script="ENTER", meta={"mitre_tactic": "execution"})
        results = lib.search("discovery")
        assert len(results) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_library.py -v`
Expected: FAIL

- [ ] **Step 3: Implement library manager**

`flipperforge/library/manager.py`:
```python
"""Payload library  - save, load, search, and delete compiled payloads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PayloadLibrary:
    """Manages saved payloads as flat files in a directory."""

    def __init__(self, payloads_dir: Path | None = None):
        if payloads_dir is None:
            payloads_dir = Path.cwd() / "payloads"
        self.dir = payloads_dir

    def save(self, name: str, *, script: str, meta: dict) -> Path:
        """Save a payload with metadata. Returns path to the .txt file."""
        self.dir.mkdir(parents=True, exist_ok=True)
        script_path = self.dir / f"{name}.txt"
        meta_path = self.dir / f"{name}.meta.json"

        script_path.write_text(script, encoding="utf-8")
        full_meta = {
            **meta,
            "name": name,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        meta_path.write_text(json.dumps(full_meta, indent=2), encoding="utf-8")
        return script_path

    def load(self, name: str) -> dict | None:
        """Load a saved payload by name. Returns None if not found."""
        script_path = self.dir / f"{name}.txt"
        meta_path = self.dir / f"{name}.meta.json"
        if not script_path.exists():
            return None
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return {"script": script_path.read_text(encoding="utf-8"), "meta": meta}

    def delete(self, name: str) -> bool:
        """Delete a saved payload. Returns True if deleted."""
        script_path = self.dir / f"{name}.txt"
        meta_path = self.dir / f"{name}.meta.json"
        if not script_path.exists():
            return False
        script_path.unlink()
        meta_path.unlink(missing_ok=True)
        return True

    def list_all(self) -> list[dict]:
        """List all saved payloads with name and metadata."""
        if not self.dir.exists():
            return []
        results = []
        for txt_file in sorted(self.dir.glob("*.txt")):
            name = txt_file.stem
            meta_path = self.dir / f"{name}.meta.json"
            meta = {}
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            results.append({"name": name, "meta": meta})
        return results

    def search(self, query: str) -> list[dict]:
        """Search payloads by name or metadata values."""
        query_lower = query.lower()
        results = []
        for item in self.list_all():
            searchable = f"{item['name']} {json.dumps(item['meta'])}".lower()
            if query_lower in searchable:
                results.append(item)
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_library.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/library/manager.py tests/test_library.py
git commit -m "feat: add payload library manager"
```

---

## Chunk 8: Serial Deploy

### Task 9: Flipper Serial Communication

**Files:**
- Create: `flipperforge/deploy/serial.py`
- Create: `tests/test_serial.py`

- [ ] **Step 1: Write serial tests (mocked)**

`tests/test_serial.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from flipperforge.deploy.serial import FlipperConnection, FlipperConnectionError


class TestFlipperDetect:
    @patch("flipperforge.deploy.serial.list_ports")
    def test_auto_detect_flipper(self, mock_list_ports):
        port = MagicMock()
        port.vid = 0x0483
        port.pid = 0x5740
        port.device = "COM3"
        mock_list_ports.comports.return_value = [port]

        result = FlipperConnection.detect_port()
        assert result == "COM3"

    @patch("flipperforge.deploy.serial.list_ports")
    def test_no_flipper_found(self, mock_list_ports):
        mock_list_ports.comports.return_value = []
        with pytest.raises(FlipperConnectionError, match="No Flipper Zero"):
            FlipperConnection.detect_port()


class TestFlipperCommands:
    def _make_conn(self):
        conn = FlipperConnection.__new__(FlipperConnection)
        conn._serial = MagicMock()
        return conn

    def test_send_command(self):
        conn = self._make_conn()
        conn._serial.read_until.return_value = b"some output\r\n>: "
        result = conn._send_command("storage list /ext/badusb")
        conn._serial.write.assert_called_once_with(b"storage list /ext/badusb\r\n")
        assert "some output" in result

    def test_list_files(self):
        conn = self._make_conn()
        conn._serial.read_until.return_value = (
            b"[F] payload1.txt 123\r\n[F] payload2.txt 456\r\n>: "
        )
        files = conn.list_badusb_files()
        assert len(files) == 2
        assert files[0]["name"] == "payload1.txt"

    def test_deploy_payload(self):
        conn = self._make_conn()
        # Mock the write_chunk response
        conn._serial.read_until.return_value = b">: "
        conn._serial.read.return_value = b""
        conn.deploy("test.txt", "DELAY 500\nENTER")
        # Verify write was called
        assert conn._serial.write.called

    def test_storage_error_raises(self):
        conn = self._make_conn()
        conn._serial.read_until.return_value = b"Storage error: internal error\r\n>: "
        with pytest.raises(FlipperConnectionError, match="Storage error"):
            conn._send_command("storage list /ext/badusb")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_serial.py -v`
Expected: FAIL

- [ ] **Step 3: Implement serial module**

`flipperforge/deploy/serial.py`:
```python
"""Flipper Zero serial communication for BadUSB deployment."""

from __future__ import annotations

import time

import serial
from serial.tools import list_ports


FLIPPER_VID = 0x0483
FLIPPER_PID = 0x5740
BAUD_RATE = 115200
TIMEOUT = 5


class FlipperConnectionError(Exception):
    """Raised when Flipper communication fails."""


class FlipperConnection:
    """Manages serial communication with a Flipper Zero."""

    def __init__(self, port: str | None = None):
        if port is None:
            port = self.detect_port()
        try:
            self._serial = serial.Serial(port, BAUD_RATE, timeout=TIMEOUT)
            time.sleep(0.5)  # Wait for Flipper to be ready
            self._serial.reset_input_buffer()
        except serial.SerialException as e:
            raise FlipperConnectionError(f"Cannot open {port}: {e}") from e

    @staticmethod
    def detect_port() -> str:
        """Auto-detect the Flipper Zero's COM port by VID/PID."""
        for port in list_ports.comports():
            if port.vid == FLIPPER_VID and port.pid == FLIPPER_PID:
                return port.device
        raise FlipperConnectionError(
            "No Flipper Zero found. Check USB cable, drivers, and that Flipper is in USB mode."
        )

    def _send_command(self, command: str) -> str:
        """Send a CLI command and read until the next prompt."""
        self._serial.write(f"{command}\r\n".encode())
        response = self._serial.read_until(b">: ").decode(errors="replace")

        if "Storage error:" in response:
            error_line = [l for l in response.splitlines() if "Storage error:" in l]
            msg = error_line[0] if error_line else "Unknown storage error"
            raise FlipperConnectionError(msg)

        # Strip the prompt from the end
        return response.replace(">: ", "").strip()

    def list_badusb_files(self) -> list[dict]:
        """List BadUSB payload files on the Flipper."""
        raw = self._send_command("storage list /ext/badusb")
        files = []
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("[F]"):
                parts = line[3:].strip().rsplit(None, 1)
                name = parts[0] if parts else line[3:].strip()
                size = parts[1] if len(parts) > 1 else "0"
                files.append({"name": name, "size": size})
        return files

    def deploy(self, filename: str, script: str) -> None:
        """Write a BadUSB payload to the Flipper's SD card."""
        path = f"/ext/badusb/{filename}"
        data = script.encode("utf-8")

        # Use storage write_chunk for single-chunk write
        self._serial.write(f"storage write_chunk {path} 0\r\n".encode())
        time.sleep(0.2)
        self._serial.write(data + b"\x00")
        self._serial.read_until(b">: ")

    def read_file(self, filename: str) -> str:
        """Read a BadUSB payload from the Flipper."""
        return self._send_command(f"storage read /ext/badusb/{filename}")

    def delete_file(self, filename: str) -> None:
        """Delete a BadUSB payload from the Flipper."""
        self._send_command(f"storage remove /ext/badusb/{filename}")

    def close(self) -> None:
        """Close the serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_serial.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/deploy/serial.py tests/test_serial.py
git commit -m "feat: add Flipper Zero serial communication"
```

---

## Chunk 9: CLI + Built-in Templates

### Task 10: CLI Integration

**Files:**
- Create: `flipperforge/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

`tests/test_cli.py`:
```python
import pytest
from click.testing import CliRunner
from pathlib import Path
from flipperforge.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()

    def test_version(self):
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_list_templates(self):
        result = self.runner.invoke(main, ["list", "--templates-dir", str(FIXTURES)])
        assert result.exit_code == 0
        assert "test-payload" in result.output

    def test_info_template(self):
        result = self.runner.invoke(main, ["info", "test-payload", "--templates-dir", str(FIXTURES)])
        assert result.exit_code == 0
        assert "discovery" in result.output
        assert "T1082" in result.output

    def test_build_template(self, tmp_path):
        result = self.runner.invoke(main, [
            "build", "test-payload",
            "--templates-dir", str(FIXTURES),
            "--cache-dir", str(tmp_path / "cache"),
            "--param", "msg=testing",
        ])
        assert result.exit_code == 0
        assert "Compiled" in result.output or "compiled" in result.output

    def test_preview_no_cache(self, tmp_path):
        result = self.runner.invoke(main, [
            "preview",
            "--cache-dir", str(tmp_path / "empty_cache"),
        ])
        assert result.exit_code != 0 or "No compiled payload" in result.output

    def test_validate_file(self, tmp_path):
        script_file = tmp_path / "test.txt"
        script_file.write_text("REM test\nDELAY 500\nGUI r\nDELAY 300\nSTRING hello\nENTER")
        result = self.runner.invoke(main, ["validate", str(script_file)])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CLI**

`flipperforge/cli.py`:
```python
"""FlipperForge CLI  - BadUSB payload workshop for Flipper Zero."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from flipperforge import __version__
from flipperforge.cache import BuildCache
from flipperforge.engine.compiler import compile_template, CompileError
from flipperforge.engine.linter import lint
from flipperforge.engine.parser import parse
from flipperforge.library.manager import PayloadLibrary
from flipperforge.mitre.mapper import MitreMapper
from flipperforge.templates.loader import discover_templates, load_template, TemplateError

console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _resolve_templates_dir(ctx: click.Context) -> Path:
    return Path(ctx.params.get("templates_dir") or TEMPLATES_DIR)


def _resolve_cache(ctx: click.Context) -> BuildCache:
    cache_dir = ctx.params.get("cache_dir")
    return BuildCache(Path(cache_dir) if cache_dir else None)


@click.group()
@click.version_option(__version__, prog_name="flipperforge")
@click.option("--templates-dir", type=str, default=None, hidden=True, help="Override templates directory")
@click.option("--cache-dir", type=str, default=None, hidden=True, help="Override cache directory")
@click.pass_context
def main(ctx, templates_dir, cache_dir):
    """FlipperForge  - BadUSB payload workshop for Flipper Zero."""
    ctx.ensure_object(dict)
    ctx.obj["templates_dir"] = templates_dir
    ctx.obj["cache_dir"] = cache_dir


@main.command("list")
@click.option("--tactic", default=None, help="Filter by MITRE ATT&CK tactic")
@click.option("--technique", default=None, help="Filter by MITRE ATT&CK technique ID")
@click.option("--templates-dir", type=str, default=None, hidden=True)
@click.pass_context
def list_templates(ctx, tactic, technique, templates_dir):
    """Browse available payload templates."""
    tdir = Path(templates_dir) if templates_dir else _resolve_templates_dir(ctx)
    templates = discover_templates(tdir)

    if tactic:
        templates = [t for t in templates if t.mitre.tactic == tactic]
    if technique:
        templates = [t for t in templates if technique in (t.mitre.technique, t.mitre.subtechnique)]

    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Tactic", style="green")
    table.add_column("Technique", style="yellow")
    table.add_column("Description")

    for t in templates:
        table.add_row(t.name, t.mitre.tactic, t.mitre.technique, t.description[:60])

    console.print(table)


@main.command()
@click.argument("template_name")
@click.option("--templates-dir", type=str, default=None, hidden=True)
@click.pass_context
def info(ctx, template_name, templates_dir):
    """Show detailed info about a template."""
    tdir = Path(templates_dir) if templates_dir else _resolve_templates_dir(ctx)
    templates = discover_templates(tdir)
    match = [t for t in templates if t.name == template_name]

    if not match:
        console.print(f"[red]Template not found: {template_name}[/red]")
        raise SystemExit(1)

    t = match[0]
    mapper = MitreMapper()
    technique_info = mapper.lookup(t.mitre.technique)

    console.print(f"\n[bold cyan]{t.name}[/bold cyan] v{t.version}")
    console.print(f"  {t.description}")
    console.print(f"\n[bold]MITRE ATT&CK:[/bold]")
    console.print(f"  Tactic:    {t.mitre.tactic}")
    console.print(f"  Technique: {t.mitre.technique}  - {technique_info['name'] if technique_info else 'Unknown'}")
    console.print(f"  Platform:  {t.platform}")
    console.print(f"\n[bold]Safety:[/bold]")
    console.print(f"  Confirmation: {'Required' if t.safety.requires_confirmation else 'Not required'}")
    console.print(f"  Scope: {t.safety.scope_note}")
    console.print(f"\n[bold]Parameters:[/bold]")
    for p in t.parameters:
        console.print(f"  {p.name} ({p.type}) = {p.default!r}  - {p.description}")


@main.command()
@click.argument("template_name")
@click.option("--param", "-p", multiple=True, help="Parameter as key=value")
@click.option("--templates-dir", type=str, default=None, hidden=True)
@click.option("--cache-dir", type=str, default=None, hidden=True)
@click.pass_context
def build(ctx, template_name, param, templates_dir, cache_dir):
    """Compile a template into a DuckyScript payload."""
    tdir = Path(templates_dir) if templates_dir else _resolve_templates_dir(ctx)
    cache = BuildCache(Path(cache_dir)) if cache_dir else BuildCache()

    templates = discover_templates(tdir)
    match = [t for t in templates if t.name == template_name]
    if not match:
        console.print(f"[red]Template not found: {template_name}[/red]")
        raise SystemExit(1)

    params = {}
    for p in param:
        if "=" not in p:
            console.print(f"[red]Invalid param format: {p} (use key=value)[/red]")
            raise SystemExit(1)
        key, val = p.split("=", 1)
        params[key] = val

    try:
        result = compile_template(match[0], params=params)
    except CompileError as e:
        console.print(f"[red]Compile error: {e}[/red]")
        raise SystemExit(1)

    if result.errors:
        console.print("[red]DuckyScript errors:[/red]")
        for err in result.errors:
            console.print(f"  Line {err['line']}: {err['message']}")
        raise SystemExit(1)

    cache.save(
        script=result.script,
        meta={
            "template_name": result.template_name,
            "mitre_tactic": result.mitre_tactic,
            "mitre_technique": result.mitre_technique,
            "params_used": result.params_used,
        },
    )

    console.print(f"[green]Compiled '{template_name}' successfully.[/green]")
    if result.warnings:
        console.print(f"[yellow]{len(result.warnings)} warning(s):[/yellow]")
        for w in result.warnings:
            console.print(f"  Line {w.line}: [{w.code}] {w.message}")


@main.command()
@click.option("--cache-dir", type=str, default=None, hidden=True)
@click.pass_context
def preview(ctx, cache_dir):
    """Show the last compiled payload."""
    cache = BuildCache(Path(cache_dir)) if cache_dir else BuildCache()
    cached = cache.load()

    if cached is None:
        console.print("[red]No compiled payload found. Run 'flipperforge build <template>' first.[/red]")
        raise SystemExit(1)

    syntax = Syntax(cached["script"], "text", theme="monokai", line_numbers=True)
    console.print(syntax)


@main.command()
@click.argument("file", type=click.Path(exists=True))
def validate(file):
    """Validate and lint a DuckyScript file."""
    script = Path(file).read_text(encoding="utf-8")
    result = parse(script)
    warnings = lint(script)

    if result.errors:
        console.print("[red]Errors:[/red]")
        for e in result.errors:
            console.print(f"  Line {e.line}: {e.message}")
    else:
        console.print("[green]No syntax errors.[/green]")

    if warnings:
        console.print(f"[yellow]{len(warnings)} warning(s):[/yellow]")
        for w in warnings:
            console.print(f"  Line {w.line}: [{w.code}] {w.message}")
    elif not result.errors:
        console.print("[green]No warnings.[/green]")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add flipperforge/cli.py tests/test_cli.py
git commit -m "feat: add CLI with list, info, build, preview, validate commands"
```

### Task 11: Built-in Templates

**Files:**
- Create: `templates/discovery/system-info.yaml`
- Create: `templates/credential-access/wifi-passwords.yaml`
- Create: `templates/execution/reverse-shell.yaml`
- Create: `templates/persistence/scheduled-task.yaml`
- Create: `templates/exfiltration/file-grab.yaml`
- Create: `templates/discovery/network-scan.yaml`
- Create: `tests/test_builtin_templates.py`

- [ ] **Step 1: Create all 6 templates**

Each template goes in its tactic subdirectory. All include authorization warnings and safety metadata. (Full YAML content for each template provided inline during implementation  - each follows the format defined in the spec.)

- [ ] **Step 2: Write template validation test**

`tests/test_builtin_templates.py`:
```python
import pytest
from pathlib import Path
from flipperforge.templates.loader import discover_templates
from flipperforge.engine.compiler import compile_template

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class TestBuiltinTemplates:
    def test_all_templates_load(self):
        templates = discover_templates(TEMPLATES_DIR)
        assert len(templates) >= 6

    @pytest.mark.parametrize("template", discover_templates(TEMPLATES_DIR), ids=lambda t: t.name)
    def test_template_compiles_with_defaults(self, template):
        result = compile_template(template)
        assert result.errors == [], f"{template.name} has parse errors: {result.errors}"
        assert result.script.strip() != ""

    @pytest.mark.parametrize("template", discover_templates(TEMPLATES_DIR), ids=lambda t: t.name)
    def test_template_has_mitre_mapping(self, template):
        assert template.mitre.tactic, f"{template.name} missing MITRE tactic"
        assert template.mitre.technique, f"{template.name} missing MITRE technique"
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_builtin_templates.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add templates/ tests/test_builtin_templates.py
git commit -m "feat: add 6 built-in BadUSB templates with MITRE mapping"
```

---

## Chunk 10: README + Final

### Task 12: README and License

**Files:**
- Create: `README.md`
- Create: `LICENSE`

- [ ] **Step 1: Create README.md**

Professional README with: project description, features list, installation, quick start, CLI reference, template format docs, MITRE integration explanation, safety disclaimer, contributing section, license.

- [ ] **Step 2: Create MIT LICENSE file**

Standard MIT license with `TiltedLunar123` as copyright holder, year 2026.

- [ ] **Step 3: Run full test suite**

Run: `pytest --tb=short -v`
Expected: All tests PASS

- [ ] **Step 4: Commit and push**

```bash
git add README.md LICENSE
git commit -m "docs: add README and MIT license"
git push origin master
```
