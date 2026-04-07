# Changelog

All notable changes to FlipperForge will be documented in this file.

## [0.2.0] - 2026-04-07

### Fixed
- `device ls` crash caused by return type mismatch in serial file listing
- `deploy` and `device` commands crash when `--port` is omitted (now auto-detects Flipper Zero)
- `library ls` showing empty creation dates due to metadata key mismatch (`created_at` vs `created`)
- `list --tactic` filter now works case-insensitively
- `read_file` now strips serial protocol overhead from returned content

### Added
- `STRINGLN` command support in DuckyScript parser (types string + Enter)
- `DEFAULTDELAY` / `DEFAULT_DELAY` command support in parser
- `NO_CLEANUP` lint rule warns when scripts open a shell but never close it
- Expanded dangerous command detection: `reg delete`, `bcdedit`, `cipher /w`, `Remove-Item -Recurse -Force`
- MITRE ATT&CK technique descriptions and reference URLs in attack data
- Deploy verification via `storage stat` after writing payloads
- Serial command retry logic (retries once on timeout)
- Unknown parameter detection in template compiler
- Path traversal prevention in payload library names
- Corrupted JSON graceful handling in cache and library
- Platform validation in template loader (`windows`, `macos`, `linux`, `cross-platform`)
- Warning logs when invalid templates are skipped during discovery
- CI/CD pipeline with GitHub Actions (pytest + ruff, Python 3.11-3.13, Ubuntu + Windows)
- `CONTRIBUTING.md` with development setup and guidelines
- `ruff` linting and formatting configuration
- `py.typed` marker for PEP 561 type checking support
- Comprehensive test coverage for device CLI commands, library CLI commands, new parser features, and all bug fixes

### Changed
- Version bumped to 0.2.0
- `list_badusb_files()` now returns `list[dict]` with `name` and `size` keys
- `FlipperConnection` constructor accepts `port=None` for auto-detection

## [0.1.0] - 2026-04-04

### Added
- Initial release
- Template engine with Jinja2 rendering and YAML-based payload templates
- DuckyScript parser with typo suggestions
- Safety linter with 5 lint rules
- MITRE ATT&CK tagging for all templates
- USB deployment over serial
- Payload library with save/search/manage
- Build cache system
- 6 built-in templates covering Discovery, Credential Access, Execution, Persistence, and Exfiltration
- CLI with `list`, `info`, `build`, `preview`, `validate`, `save`, `deploy`, `device`, and `library` commands
