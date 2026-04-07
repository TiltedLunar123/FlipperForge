# FlipperForge

BadUSB payload workshop for Flipper Zero. Build, validate, and deploy DuckyScript payloads from templates with MITRE ATT&CK mapping, safety linting, and one-command deployment over USB.

> **Authorized use only.** FlipperForge is designed for legitimate security testing, red team engagements, and educational purposes. Only use on systems you own or have explicit written authorization to test.

[![CI](https://github.com/TiltedLunar123/FlipperForge/actions/workflows/ci.yml/badge.svg)](https://github.com/TiltedLunar123/FlipperForge/actions/workflows/ci.yml)

## Features

- **Template engine** - YAML-based payload templates with configurable parameters and Jinja2 rendering
- **DuckyScript parser** - Validates Flipper-flavored DuckyScript with typo suggestions, `STRINGLN`, and `DEFAULTDELAY` support
- **Safety linter** - Warns about missing delays, dangerous commands, missing confirmation pauses, and unclosed shells
- **MITRE ATT&CK tagging** - Every template and payload mapped to ATT&CK techniques and tactics with descriptions and reference URLs
- **USB deployment** - Auto-detect Flipper Zero and push payloads over serial with deploy verification
- **Payload library** - Save, search, and manage your compiled payloads with path traversal protection
- **Build cache** - Build once, preview and deploy without recompiling

## Installation

```bash
git clone https://github.com/TiltedLunar123/FlipperForge.git
cd FlipperForge
pip install -e ".[dev]"
```

Requires Python 3.11+.

## Quick Start

```bash
# List available templates
flipperforge list

# See details about a template
flipperforge info system-info

# Build a payload with default parameters
flipperforge build system-info

# Build with custom parameters
flipperforge build reverse-shell -p lhost=192.168.1.100 -p lport=9001

# Preview the compiled payload
flipperforge preview

# Deploy to Flipper Zero (auto-detects USB)
flipperforge deploy

# Validate any DuckyScript file
flipperforge validate my-payload.txt
```

## CLI Reference

### Core Commands

| Command | Description |
|---------|-------------|
| `flipperforge list [--tactic NAME] [--technique ID]` | Browse templates, optionally filtered |
| `flipperforge info <template>` | Show template details, params, MITRE mapping |
| `flipperforge build <template> [-p key=value ...]` | Compile a template with parameters |
| `flipperforge preview` | Show last compiled payload with highlighting |
| `flipperforge validate <file>` | Parse and lint any DuckyScript file |
| `flipperforge save <name>` | Save last compiled payload to library |

### Device Commands

| Command | Description |
|---------|-------------|
| `flipperforge deploy [--port PORT] [--name FILE]` | Push payload to Flipper Zero |
| `flipperforge device ls [--port PORT]` | List payloads on Flipper |
| `flipperforge device pull <file> [--port PORT]` | Copy payload from Flipper |
| `flipperforge device rm <file> [--port PORT]` | Delete payload from Flipper |

### Library Commands

| Command | Description |
|---------|-------------|
| `flipperforge library ls` | List all saved payloads |
| `flipperforge library search <query>` | Search by name or tactic |
| `flipperforge library load <name>` | Load saved payload into build cache |
| `flipperforge library rm <name>` | Delete a saved payload |

## Built-in Templates

| Template | MITRE Technique | Tactic | Description |
|----------|----------------|--------|-------------|
| system-info | T1082 | Discovery | Collect OS, hostname, IP, user info |
| wifi-passwords | T1555.005 | Credential Access | Extract saved WiFi credentials |
| reverse-shell | T1059.001 | Execution | PowerShell reverse shell |
| scheduled-task | T1053.005 | Persistence | Create a scheduled task at login |
| file-grab | T1005 | Exfiltration | Copy files to staging directory |
| network-scan | T1046 | Discovery | Quick network discovery via PowerShell |

## Template Format

Templates are YAML files with metadata, parameters, safety info, and a DuckyScript body:

```yaml
name: my-payload
description: What this payload does
author: YourName
version: "1.0"
mitre:
  tactic: discovery
  technique: T1082
platform: windows
parameters:
  - name: delay_ms
    type: integer
    default: 500
    description: "Delay between keystrokes (ms)"
  - name: output_file
    type: string
    default: "output.txt"
    description: "Output filename"
safety:
  requires_confirmation: false
  scope_note: "Only use on authorized systems"
script: |
  REM My custom payload
  DELAY {{ delay_ms }}
  GUI r
  DELAY 300
  STRING cmd
  ENTER
```

### Parameter Types

| Type | Description |
|------|-------------|
| `string` | Free text (max 500 chars) |
| `integer` | Whole number, optional min/max constraints |
| `boolean` | true/false |
| `choice` | One of a predefined set of values |

## Safety Features

FlipperForge includes several safety mechanisms:

- **Authorization warnings** - Every template includes scope notes and authorization reminders
- **Confirmation pauses** - Templates flagged as dangerous require a DELAY >= 2000ms at the start for physical abort
- **Dangerous command detection** - Linter flags format, rm -rf, del /f, diskpart, reg delete, bcdedit, cipher /w, Remove-Item -Recurse -Force, and disk wipe patterns
- **Unclosed shell detection** - Warns when scripts open a shell but never exit
- **Delay validation** - Warns when delays after modifier keys are too short for reliable execution
- **Script headers** - Encourages REM comment headers describing each payload

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Install linting tools
pip install ruff

# Run tests
pytest

# Run tests with coverage
pytest --cov=flipperforge --cov-report=term-missing

# Lint and format
ruff check .
ruff format .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full development guidelines.

## License

MIT License. See [LICENSE](LICENSE) for details.
