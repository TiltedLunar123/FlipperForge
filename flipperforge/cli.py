"""FlipperForge CLI - BadUSB payload workshop for Flipper Zero."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from flipperforge import __version__
from flipperforge.cache import BuildCache
from flipperforge.engine.compiler import CompileError, compile_template
from flipperforge.engine.linter import lint
from flipperforge.engine.parser import parse
from flipperforge.library.manager import PayloadLibrary
from flipperforge.mitre.mapper import MitreMapper
from flipperforge.templates.loader import discover_templates

console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@click.group()
@click.version_option(__version__, prog_name="flipperforge")
def main():
    """FlipperForge - BadUSB payload workshop for Flipper Zero."""


# -- list -------------------------------------------------------------------


@main.command("list")
@click.option("--tactic", default=None, help="Filter by MITRE ATT&CK tactic")
@click.option("--technique", default=None, help="Filter by technique ID")
@click.option("--templates-dir", type=click.Path(exists=True), default=None, hidden=True)
def list_templates(tactic, technique, templates_dir):
    """Browse available payload templates."""
    tdir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
    templates = discover_templates(tdir)

    if tactic:
        templates = [t for t in templates if t.mitre.tactic.lower() == tactic.lower()]
    if technique:
        templates = [t for t in templates if technique in (t.mitre.technique, t.mitre.subtechnique)]

    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Tactic", style="green")
    table.add_column("Technique", style="yellow")
    table.add_column("Platform")
    table.add_column("Description")

    for t in templates:
        tech = t.mitre.technique
        table.add_row(t.name, t.mitre.tactic, tech, t.platform, t.description[:50])

    console.print(table)


# -- info -------------------------------------------------------------------


@main.command()
@click.argument("template_name")
@click.option("--templates-dir", type=click.Path(exists=True), default=None, hidden=True)
def info(template_name, templates_dir):
    """Show detailed info about a template."""
    tdir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
    templates = discover_templates(tdir)
    match = [t for t in templates if t.name == template_name]

    if not match:
        console.print(f"[red]Template not found: {template_name}[/red]")
        raise SystemExit(1)

    t = match[0]
    mapper = MitreMapper()
    technique_id = t.mitre.technique
    technique_info = mapper.lookup(technique_id)
    # Try parent technique if subtechnique lookup fails
    if technique_info is None and "." in technique_id:
        technique_info = mapper.lookup(technique_id.split(".")[0])

    console.print(f"\n[bold cyan]{t.name}[/bold cyan] v{t.version}")
    console.print(f"  {t.description}")
    console.print("\n[bold]MITRE ATT&CK:[/bold]")
    console.print(f"  Tactic:    {t.mitre.tactic}")
    tech_name = technique_info["name"] if technique_info else "Unknown"
    console.print(f"  Technique: {technique_id} - {tech_name}")
    console.print(f"  Platform:  {t.platform}")
    console.print("\n[bold]Safety:[/bold]")
    console.print(
        f"  Confirmation: {'Required' if t.safety.requires_confirmation else 'Not required'}"
    )
    console.print(f"  Scope: {t.safety.scope_note}")
    console.print("\n[bold]Parameters:[/bold]")
    for p in t.parameters:
        extra = ""
        if p.choices:
            extra = f" choices={p.choices}"
        console.print(f"  {p.name} ({p.type}) = {p.default!r}{extra} -- {p.description}")


# -- build ------------------------------------------------------------------


@main.command()
@click.argument("template_name")
@click.option("--param", "-p", multiple=True, help="Parameter as key=value")
@click.option("--templates-dir", type=click.Path(exists=True), default=None, hidden=True)
@click.option("--cache-dir", type=str, default=None, hidden=True)
def build(template_name, param, templates_dir, cache_dir):
    """Compile a template into a DuckyScript payload."""
    tdir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
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
        raise SystemExit(1) from None

    if result.errors:
        console.print("[red]DuckyScript errors:[/red]")
        for err in result.errors:
            console.print(f"  {err}")
        raise SystemExit(1)

    cache.save(
        script=result.script,
        meta={
            "template_name": result.template_name,
            "mitre_tactic": result.mitre_tactic,
            "mitre_technique": result.mitre_technique,
            "mitre_subtechnique": result.mitre_subtechnique,
            "params_used": result.params_used,
        },
    )

    console.print(f"[green]Compiled '{template_name}' successfully.[/green]")
    if result.warnings:
        console.print(f"[yellow]{len(result.warnings)} warning(s):[/yellow]")
        for w in result.warnings:
            console.print(f"  Line {w.line}: [{w.code}] {w.message}")


# -- preview ----------------------------------------------------------------


@main.command()
@click.option("--cache-dir", type=str, default=None, hidden=True)
def preview(cache_dir):
    """Show the last compiled payload with syntax highlighting."""
    cache = BuildCache(Path(cache_dir)) if cache_dir else BuildCache()
    cached = cache.load()

    if cached is None:
        console.print(
            "[red]No compiled payload found. Run 'flipperforge build <template>' first.[/red]"
        )
        raise SystemExit(1)

    meta = cached["meta"]
    console.print(f"[bold]Template:[/bold] {meta.get('template_name', 'unknown')}")
    console.print(
        f"[bold]MITRE:[/bold] {meta.get('mitre_tactic', '')} / {meta.get('mitre_technique', '')}\n"
    )
    syntax = Syntax(cached["script"], "text", theme="monokai", line_numbers=True)
    console.print(syntax)


# -- validate ---------------------------------------------------------------


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
            console.print(f"  Line {e.line_number}: {e.message}")
            if e.suggestion:
                console.print(f"    Suggestion: {e.suggestion}")
    else:
        console.print("[green]No syntax errors.[/green]")

    if warnings:
        console.print(f"\n[yellow]{len(warnings)} warning(s):[/yellow]")
        for w in warnings:
            console.print(f"  Line {w.line}: [{w.code}] {w.message}")
            if w.suggestion:
                console.print(f"    {w.suggestion}")
    elif not result.errors:
        console.print("[green]No warnings.[/green]")


# -- deploy -----------------------------------------------------------------


@main.command()
@click.option("--port", default=None, help="Serial port (auto-detects if omitted)")
@click.option(
    "--name", "filename", default=None, help="Filename on Flipper (default: template name)"
)
@click.option("--cache-dir", type=str, default=None, hidden=True)
def deploy(port, filename, cache_dir):
    """Push the last compiled payload to Flipper Zero."""
    cache = BuildCache(Path(cache_dir)) if cache_dir else BuildCache()
    cached = cache.load()

    if cached is None:
        console.print(
            "[red]No compiled payload found. Run 'flipperforge build <template>' first.[/red]"
        )
        raise SystemExit(1)

    if filename is None:
        filename = cached["meta"].get("template_name", "payload") + ".txt"
    if not filename.endswith(".txt"):
        filename += ".txt"

    from flipperforge.deploy.serial import FlipperConnection, FlipperConnectionError

    try:
        with FlipperConnection(port) as conn:
            conn.deploy(filename, cached["script"])
            console.print(f"[green]Deployed '{filename}' to Flipper Zero.[/green]")
    except FlipperConnectionError as e:
        console.print(f"[red]Flipper error: {e}[/red]")
        raise SystemExit(1) from None


# -- device subcommand group ------------------------------------------------


@main.group()
def device():
    """Manage payloads on the Flipper Zero."""


@device.command("ls")
@click.option("--port", default=None, help="Serial port")
def device_ls(port):
    """List BadUSB payloads on the Flipper."""
    from flipperforge.deploy.serial import FlipperConnection, FlipperConnectionError

    try:
        with FlipperConnection(port) as conn:
            files = conn.list_badusb_files()
    except FlipperConnectionError as e:
        console.print(f"[red]Flipper error: {e}[/red]")
        raise SystemExit(1) from None

    if not files:
        console.print("[yellow]No BadUSB payloads found on Flipper.[/yellow]")
        return

    table = Table(title="Payloads on Flipper")
    table.add_column("Name", style="cyan")
    table.add_column("Size", style="green")
    for f in files:
        table.add_row(f["name"], f.get("size", ""))
    console.print(table)


@device.command("pull")
@click.argument("filename")
@click.option("--port", default=None, help="Serial port")
def device_pull(filename, port):
    """Copy a payload from Flipper to local payloads/ directory."""
    from flipperforge.deploy.serial import FlipperConnection, FlipperConnectionError

    try:
        with FlipperConnection(port) as conn:
            content = conn.read_file(filename)
    except FlipperConnectionError as e:
        console.print(f"[red]Flipper error: {e}[/red]")
        raise SystemExit(1) from None

    lib = PayloadLibrary()
    name = Path(filename).stem
    lib.save(name, script=content, meta={"source": "flipper", "original_filename": filename})
    console.print(f"[green]Pulled '{filename}' to payloads/{name}.txt[/green]")


@device.command("rm")
@click.argument("filename")
@click.option("--port", default=None, help="Serial port")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def device_rm(filename, port, yes):
    """Delete a payload from the Flipper."""
    if not yes:
        click.confirm(f"Delete '{filename}' from Flipper?", abort=True)

    from flipperforge.deploy.serial import FlipperConnection, FlipperConnectionError

    try:
        with FlipperConnection(port) as conn:
            conn.delete_file(filename)
            console.print(f"[green]Deleted '{filename}' from Flipper.[/green]")
    except FlipperConnectionError as e:
        console.print(f"[red]Flipper error: {e}[/red]")
        raise SystemExit(1) from None


# -- library subcommand group -----------------------------------------------


@main.group()
def library():
    """Manage saved payloads."""


@library.command("ls")
def library_ls():
    """List all saved payloads."""
    lib = PayloadLibrary()
    items = lib.list_all()

    if not items:
        console.print("[yellow]No saved payloads.[/yellow]")
        return

    table = Table(title="Saved Payloads")
    table.add_column("Name", style="cyan")
    table.add_column("Tactic", style="green")
    table.add_column("Technique", style="yellow")
    table.add_column("Created")

    for item in items:
        meta = item["meta"]
        table.add_row(
            item["name"],
            meta.get("mitre_tactic", ""),
            meta.get("mitre_technique", ""),
            meta.get("created_at", "")[:10],
        )
    console.print(table)


@library.command("search")
@click.argument("query")
def library_search(query):
    """Search saved payloads by name or tactic."""
    lib = PayloadLibrary()
    results = lib.search(query)

    if not results:
        console.print(f"[yellow]No payloads matching '{query}'.[/yellow]")
        return

    for item in results:
        console.print(f"  [cyan]{item['name']}[/cyan] - {item['meta'].get('mitre_tactic', '')}")


@library.command("load")
@click.argument("name")
@click.option("--cache-dir", type=str, default=None, hidden=True)
def library_load(name, cache_dir):
    """Load a saved payload into the build cache for preview/deploy."""
    lib = PayloadLibrary()
    loaded = lib.load(name)

    if loaded is None:
        console.print(f"[red]Payload not found: {name}[/red]")
        raise SystemExit(1)

    cache = BuildCache(Path(cache_dir)) if cache_dir else BuildCache()
    cache.save(script=loaded["script"], meta=loaded["meta"])
    console.print(f"[green]Loaded '{name}' into build cache. Use 'preview' or 'deploy'.[/green]")


@library.command("rm")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def library_rm(name, yes):
    """Delete a saved payload."""
    if not yes:
        click.confirm(f"Delete saved payload '{name}'?", abort=True)

    lib = PayloadLibrary()
    if lib.delete(name):
        console.print(f"[green]Deleted '{name}'.[/green]")
    else:
        console.print(f"[red]Payload not found: {name}[/red]")
        raise SystemExit(1)


# -- save -------------------------------------------------------------------


@main.command()
@click.argument("name")
@click.option("--cache-dir", type=str, default=None, hidden=True)
def save(name, cache_dir):
    """Save the last compiled payload to the library."""
    cache = BuildCache(Path(cache_dir)) if cache_dir else BuildCache()
    cached = cache.load()

    if cached is None:
        console.print(
            "[red]No compiled payload found. Run 'flipperforge build <template>' first.[/red]"
        )
        raise SystemExit(1) from None

    lib = PayloadLibrary()
    lib.save(name, script=cached["script"], meta=cached["meta"])
    console.print(f"[green]Saved payload as '{name}'.[/green]")
