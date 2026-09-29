import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__, credentials, output
from .alive import iter_live
from .enrich import EnrichOptions, make_enricher
from .enumerate import enumerate_domain, make_client, subfinder_available
from .h1 import CredentialsMissing, H1Client, H1Error, load_scope
from .models import LiveHost

app = typer.Typer(add_completion=False, no_args_is_help=True)
auth = typer.Typer(no_args_is_help=True, help="Manage HackerOne credentials.")
app.add_typer(auth, name="auth")
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
    with H1Client.from_credentials() as client:
        return load_scope(
            client,
            handle,
            include_non_bounty=include_non_bounty,
            use_cache=not no_cache,
        )


def _load_scope(handle: str, include_non_bounty: bool, no_cache: bool):
    try:
        return _scope_for(handle, include_non_bounty, no_cache)
    except CredentialsMissing as error:
        err.print(f"[red]HackerOne credentials required:[/red] {error}")
        raise typer.Exit(1) from error
    except H1Error as error:
        err.print(f"[red]HackerOne API error:[/red] {error}")
        raise typer.Exit(1) from error


async def _scan_stream(
    scope,
    apexes: list[str],
    *,
    only_wildcards: bool,
    dns_only: bool,
    concurrency: int,
    timeout: float,
    on_host,
    status_codes: set[int] | None = None,
    enricher=None,
    headers: dict[str, str] | None = None,
) -> list[LiveHost]:
    hosts: set[str] = set()
    async with make_client(headers=headers) as client:
        for apex in apexes:
            found = await enumerate_domain(apex, client=client, concurrency=concurrency)
            hosts |= set(found)
            err.print(f"  [dim]{apex}: {len(found)} names[/dim]")

    candidates = scope.keep(sorted(hosts), only_wildcards)
    err.print(f"{len(candidates)} in-scope candidates, resolving and probing...")

    live: list[LiveHost] = []
    async for host in iter_live(
        candidates, dns_only=dns_only, timeout=timeout, enricher=enricher, headers=headers
    ):
        if status_codes is not None and host.status not in status_codes:
            continue
        live.append(host)
        on_host(host)
    return live


def _parse_status_codes(value: str | None) -> set[int] | None:
    if not value:
        return None
    codes: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part.isdigit():
            raise typer.BadParameter(f"invalid status code: {part!r}")
        codes.add(int(part))
    return codes


def _build_headers(raw: list[str], h1_header: bool) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in raw:
        name, separator, value = item.partition(":")
        if not separator or not name.strip():
            raise typer.BadParameter(f"invalid header {item!r}, expected 'Name: Value'")
        headers[name.strip()] = value.strip()
    if h1_header:
        headers.setdefault("X-HackerOne-Research", "{username}")
    if any("{username}" in value for value in headers.values()):
        found = credentials.resolve()
        if found is None:
            raise typer.BadParameter("{username} in a header requires stored HackerOne credentials")
        headers = {
            key: value.replace("{username}", found.username) for key, value in headers.items()
        }
    return headers


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
    status_code: str = typer.Option(
        None,
        "--status-code",
        "-sc",
        help="Comma-separated HTTP status codes to keep (e.g. 200,404).",
    ),
    enrich: bool = typer.Option(
        False, "--enrich", help="Add technology, security headers, TLS and favicon info."
    ),
    takeover: bool = typer.Option(
        False, "--takeover", help="Flag dangling CNAMEs / subdomain takeover candidates."
    ),
    header: list[str] = typer.Option(
        None,
        "--header",
        "-H",
        help="Extra request header 'Name: Value' (repeatable); {username} is substituted.",
    ),
    h1_header: bool = typer.Option(
        False, "--h1-header", help="Add 'X-HackerOne-Research: <username>' to every request."
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
    no_progress: bool = typer.Option(
        False, "--no-progress", help="Do not stream findings as they are found."
    ),
) -> None:
    """Enumerate live, in-scope subdomains for a HackerOne program."""
    scope = _load_scope(handle, include_non_bounty, no_cache)

    status_codes = _parse_status_codes(status_code)
    if status_codes and dns_only:
        raise typer.BadParameter("--status-code cannot be combined with --dns-only")

    enrich_options = EnrichOptions(enrich=enrich, takeover=takeover)
    if enrich_options.active and dns_only:
        raise typer.BadParameter("--enrich/--takeover cannot be combined with --dns-only")
    enricher = make_enricher(enrich_options) if enrich_options.active else None

    headers = _build_headers(header or [], h1_header)

    apexes = scope.apexes(only_wildcards)
    if not apexes:
        err.print("[yellow]No in-scope domains found for this program.[/yellow]")
        raise typer.Exit(1)

    structured = as_json or as_csv or as_md or output_file is not None
    fmt = "json" if as_json else "csv" if as_csv else "md" if as_md else None
    target = err if structured else console

    def on_host(host: LiveHost) -> None:
        if no_progress:
            return
        if host.status is not None:
            line = f"  [green]{host.status}[/green] {host.host}"
            if host.title:
                line += f" [dim]{host.title}[/dim]"
        else:
            line = f"  [green]up[/green] {host.host}"
        summary = output.finding_summary(host.enrichment)
        if summary:
            line += f" [cyan]{summary}[/cyan]"
        target.print(line)

    source = "subfinder" if subfinder_available() else "built-in CT sources"
    err.print(f"Enumerating {len(apexes)} domain(s) via {source}...")
    live = asyncio.run(
        _scan_stream(
            scope,
            apexes,
            only_wildcards=only_wildcards,
            dns_only=dns_only,
            concurrency=concurrency,
            timeout=timeout,
            on_host=on_host,
            status_codes=status_codes,
            enricher=enricher,
            headers=headers,
        )
    )

    if not live:
        err.print("[yellow]No live in-scope hosts found.[/yellow]")
        raise typer.Exit(1)

    if structured:
        _emit(live, fmt, output_file)
        err.print(f"{len(live)} live hosts")
    elif no_progress:
        output.render_table(live, console)
    else:
        console.print(f"\n[green]{len(live)}[/green] live in-scope hosts")

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
    loaded = _load_scope(handle, include_non_bounty, no_cache)

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


@auth.command("login")
def auth_login(
    username: str = typer.Option(None, "--username", "-u", help="HackerOne username."),
    token_stdin: bool = typer.Option(False, "--token-stdin", help="Read the API token from stdin."),
    store: str = typer.Option("auto", "--store", help="Storage backend: auto, keyring or file."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip verifying the token."),
) -> None:
    """Store HackerOne credentials securely."""
    if store not in ("auto", "keyring", "file"):
        raise typer.BadParameter("store must be one of: auto, keyring, file")

    existing = credentials.resolve()
    if username is None:
        username = typer.prompt("HackerOne username", default=existing.username if existing else "")
    token = sys.stdin.read().strip() if token_stdin else typer.prompt("API token", hide_input=True)
    if not username.strip() or not token:
        err.print("[red]username and token are required[/red]")
        raise typer.Exit(1)

    if not no_verify:
        try:
            with H1Client(username, token) as client:
                client.verify()
        except H1Error as error:
            err.print(f"[red]token verification failed:[/red] {error}")
            raise typer.Exit(1) from error

    try:
        backend = credentials.save(username, token, backend=store)
    except credentials.CredentialsError as error:
        err.print(f"[red]{error}[/red]")
        raise typer.Exit(1) from error

    console.print(f"stored credentials for [bold]{username}[/bold] using {backend}")
    if credentials.source() == "env":
        err.print(
            "note: H1_USERNAME/H1_API_TOKEN are set and take precedence over stored credentials"
        )


@auth.command("status")
def auth_status(
    verify: bool = typer.Option(
        True, "--verify/--no-verify", help="Validate the token against the API."
    ),
) -> None:
    """Show the credentials in use and whether they are valid."""
    found = credentials.resolve()
    origin = credentials.source()
    if found is None:
        err.print("no credentials found; run 'subhunt auth login'")
        raise typer.Exit(1)

    console.print(f"source: {origin}")
    console.print(f"username: {found.username}")
    if origin == "file" and credentials.insecure_permissions():
        err.print("[yellow]warning: credentials file is readable by other users[/yellow]")

    if verify:
        try:
            with H1Client(found.username, found.token) as client:
                client.verify()
        except H1Error as error:
            err.print(f"[red]verification failed:[/red] {error}")
            raise typer.Exit(1) from error
        console.print("[green]token verified[/green]")


@auth.command("logout")
def auth_logout() -> None:
    """Remove stored credentials."""
    removed = credentials.delete()
    if not removed:
        err.print("no stored credentials to remove")
        raise typer.Exit(1)
    console.print(f"removed credentials from: {', '.join(removed)}")


@app.command()
def mcp() -> None:
    """Run subhunt as an MCP server over stdio."""
    from .mcp import run

    run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
