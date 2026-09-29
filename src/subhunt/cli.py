import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__, output
from .alive import check_hosts
from .enumerate import enumerate_domain, make_client, subfinder_available
from .h1 import CredentialsMissing, H1Client, H1Error, load_scope
from .models import LiveHost

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()
err = Console(stderr=True)


def _version(value: bool) -> None:
    if value:
        console.print(f"subhunt {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False, "--version", callback=_version, is_eager=True, help="Show version."
    ),
) -> None:
    """Live, in-scope subdomains for bug bounty programs."""


def _scope_for(handle: str, include_non_bounty: bool, no_cache: bool):
    with H1Client.from_env() as client:
        return load_scope(
            client,
            handle,
            include_non_bounty=include_non_bounty,
            use_cache=not no_cache,
        )


async def _enumerate(apexes: list[str], concurrency: int) -> list[str]:
    hosts: set[str] = set()
    async with make_client() as client:
        for apex in apexes:
            hosts |= set(await enumerate_domain(apex, client=client, concurrency=concurrency))
    return sorted(hosts)


def _emit(hosts: list[LiveHost], fmt: str | None, output_file: Path | None) -> None:
    if fmt is None and output_file is None:
        output.render_table(hosts, console)
        return
    fmt = fmt or "json"
    text = {"json": output.to_json, "csv": output.to_csv, "md": output.to_markdown}[fmt](hosts)
    if output_file:
        output_file.write_text(text, encoding="utf-8")
        err.print(f"wrote {len(hosts)} live hosts to {output_file}")
    else:
        typer.echo(text)


def _report_diff(live: list[LiveHost], path: Path) -> None:
    if not path.exists():
        err.print(f"diff file {path} not found, skipping comparison")
        return
    previous = output.load_hosts(path)
    current = {item.host for item in live}
    added = sorted(current - previous)
    removed = sorted(previous - current)
    err.print(f"\n[green]+{len(added)} new[/green]  [red]-{len(removed)} gone[/red]")
    for host in added:
        err.print(f"  [green]+ {host}[/green]")
    for host in removed:
        err.print(f"  [red]- {host}[/red]")


@app.command()
def scan(
    handle: str,
    include_non_bounty: bool = typer.Option(
        False, "--include-non-bounty", help="Include submittable assets without a bounty."
    ),
    only_wildcards: bool = typer.Option(
        False, "--only-wildcards", help="Enumerate only wildcard scopes."
    ),
    dns_only: bool = typer.Option(
        False, "--dns-only", help="Keep hosts that resolve, skip HTTP probing."
    ),
    as_json: bool = typer.Option(False, "--json", help="Output JSON."),
    as_csv: bool = typer.Option(False, "--csv", help="Output CSV."),
    as_md: bool = typer.Option(False, "--md", help="Output Markdown."),
    output_file: Path = typer.Option(None, "--output", "-o", help="Write results to a file."),
    diff: Path = typer.Option(None, "--diff", help="Compare against a previous JSON result."),
    concurrency: int = typer.Option(
        25, "--concurrency", min=1, help="Requests per source/probe in flight."
    ),
    timeout: float = typer.Option(
        8.0, "--timeout", min=1.0, help="Per-request timeout in seconds."
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the local H1 scope cache."),
) -> None:
    """Enumerate live, in-scope subdomains for a HackerOne program."""
    try:
        scope = _scope_for(handle, include_non_bounty, no_cache)
    except CredentialsMissing as error:
        err.print(f"[red]HackerOne credentials required:[/red] {error}")
        raise typer.Exit(1) from error
    except H1Error as error:
        err.print(f"[red]HackerOne API error:[/red] {error}")
        raise typer.Exit(1) from error

    apexes = scope.apexes(only_wildcards)
    if not apexes:
        err.print("[yellow]No in-scope domains found for this program.[/yellow]")
        raise typer.Exit(1)

    source = "subfinder" if subfinder_available() else "built-in CT sources"
    err.print(f"Enumerating {len(apexes)} domain(s) via {source}...")
    raw = asyncio.run(_enumerate(apexes, concurrency))
    candidates = scope.keep(raw, only_wildcards)
    live = asyncio.run(check_hosts(candidates, dns_only=dns_only, timeout=timeout))

    if not live:
        console.print("[yellow]No live in-scope hosts found.[/yellow]")
        raise typer.Exit(1)

    fmt = "json" if as_json else "csv" if as_csv else "md" if as_md else None
    _emit(live, fmt, output_file)

    if diff:
        _report_diff(live, diff)


@app.command()
def scope(
    handle: str,
    include_non_bounty: bool = typer.Option(
        False, "--include-non-bounty", help="Include submittable assets without a bounty."
    ),
    only_wildcards: bool = typer.Option(
        False, "--only-wildcards", help="Show only wildcard scopes."
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the local H1 scope cache."),
) -> None:
    """Show the parsed in-scope and out-of-scope patterns of a program."""
    try:
        loaded = _scope_for(handle, include_non_bounty, no_cache)
    except CredentialsMissing as error:
        err.print(f"[red]HackerOne credentials required:[/red] {error}")
        raise typer.Exit(1) from error
    except H1Error as error:
        err.print(f"[red]HackerOne API error:[/red] {error}")
        raise typer.Exit(1) from error

    in_scope = loaded.in_scope_patterns(only_wildcards)
    out_scope = loaded.out_of_scope_patterns()
    apexes = loaded.apexes(only_wildcards)
    exclusions = [item.category for item in loaded.exclusions]

    def panel(title: str, items: list[str], style: str) -> None:
        body = "\n".join(items) if items else "[dim]none[/dim]"
        console.print(Panel(body, title=title, border_style=style, expand=False))

    panel(f"in scope ({len(in_scope)})", in_scope, "green")
    panel(f"out of scope ({len(out_scope)})", out_scope, "red")
    panel(f"apexes to enumerate ({len(apexes)})", apexes, "cyan")
    if exclusions:
        panel(f"category exclusions ({len(exclusions)})", exclusions, "yellow")


@app.command()
def mcp() -> None:
    """Run subhunt as an MCP server over stdio."""
    from .mcp import run

    run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
