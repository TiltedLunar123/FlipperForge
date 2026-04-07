# Contributing to FlipperForge

Thanks for your interest in contributing to FlipperForge! This guide will help you get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/TiltedLunar123/FlipperForge.git
cd FlipperForge

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in dev mode with test dependencies
pip install -e ".[dev]"

# Install linting tools
pip install ruff
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=flipperforge --cov-report=term-missing

# Run a specific test file
pytest tests/test_cli.py

# Run a specific test
pytest tests/engine/test_parser.py::TestString::test_basic_string
```

## Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
# Check formatting
ruff format --check .

# Auto-format
ruff format .

# Check linting rules
ruff check .

# Auto-fix linting issues
ruff check --fix .
```

## Pull Request Guidelines

1. **Fork and branch** - Create a feature branch from `main`
2. **Write tests** - All new features and bug fixes should include tests
3. **Run the full suite** - Make sure `pytest` passes before submitting
4. **Run the linter** - Make sure `ruff check .` and `ruff format --check .` pass
5. **Keep it focused** - One feature or fix per PR
6. **Describe your changes** - Explain what you changed and why in the PR description

## Project Structure

```
flipperforge/
  cli.py              # Click CLI entry point
  cache.py            # Build cache (last compiled payload)
  engine/
    parser.py          # DuckyScript tokenizer/validator
    linter.py          # Safety lint rules
    compiler.py        # Template compiler (Jinja2 + parser + linter)
  templates/
    loader.py          # YAML template loader and discovery
  deploy/
    serial.py          # Flipper Zero USB serial communication
  library/
    manager.py         # Payload library CRUD
  mitre/
    mapper.py          # MITRE ATT&CK lookup
    attack_data.json   # Technique dataset
templates/             # Built-in YAML payload templates
tests/                 # Test suite
```

## Adding Templates

Templates live in `templates/<tactic>/` as YAML files. See the [README](README.md#template-format) for the full format spec. Every template must include:

- MITRE ATT&CK mapping (`tactic` and `technique`)
- Safety metadata (`requires_confirmation` and `scope_note`)
- A `REM` header in the script body
- An initial `DELAY` for target readiness

## Reporting Issues

Use [GitHub Issues](https://github.com/TiltedLunar123/FlipperForge/issues) to report bugs or request features. Include:

- FlipperForge version (`flipperforge --version`)
- Python version (`python --version`)
- Steps to reproduce
- Expected vs actual behavior
