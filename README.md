# subhunt

[![CI](https://github.com/gabdevele/subhunt/actions/workflows/ci.yml/badge.svg)](https://github.com/gabdevele/subhunt/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/subhunt)](https://pypi.org/project/subhunt/)
[![Python](https://img.shields.io/pypi/pyversions/subhunt)](https://pypi.org/project/subhunt/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Lint](https://img.shields.io/badge/lint-ruff-261230)](https://github.com/astral-sh/ruff)
[![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet)](https://modelcontextprotocol.io)

<img src="https://raw.githubusercontent.com/gabdevele/subhunt/main/docs/banner.svg" alt="subhunt" width="100%">

**subhunt** turns a HackerOne program handle into a list of *live, in-scope* subdomains.
It reads the program's structured scope, enumerates every in-scope wildcard, removes
out-of-scope hosts, and keeps only the ones that actually resolve and answer over HTTP.

<img src="https://raw.githubusercontent.com/gabdevele/subhunt/main/docs/demo.svg" alt="subhunt demo" width="100%">

## Why

Generic subdomain enumerators do not know your program's scope. You end up probing
hosts that are explicitly out of scope, and you still have to filter dead entries by
hand. subhunt is scope-aware from the start:

- **Scope-driven** - wildcards and out-of-scope entries are read straight from the
  HackerOne program, so the output is exactly what you are allowed to test.
- **Alive by default** - every candidate is resolved (DNS) and probed (HTTP); only
  reachable hosts are reported.
- **Hybrid enumeration** - uses `subfinder` when installed, otherwise falls back to
  free Certificate Transparency sources, with no mandatory Go toolchain.
- **Automation ready** - clean JSON/CSV/Markdown output, `--diff` for monitoring, and
  an MCP server for agents.

## Install

```bash
uv tool install subhunt
# or
pipx install subhunt
# or
pip install subhunt
```

From source:

```bash
git clone https://github.com/gabdevele/subhunt
cd subhunt
uv sync
uv run subhunt --help
```

Requires Python 3.11+. For better coverage, install
[subfinder](https://github.com/projectdiscovery/subfinder) (optional).

## Credentials

subhunt uses the [HackerOne Hacker API](https://api.hackerone.com/getting-started-hacker-api).
Create an API token in your HackerOne settings and export:

```bash
export H1_USERNAME="your-username"
export H1_API_TOKEN="your-token"
```

Without credentials the scope commands cannot run.

## Usage

```bash
# Live, in-scope subdomains for a program
subhunt scan shopify

# Inspect how the scope was parsed
subhunt scope uber

# Machine-readable output
subhunt scan gitlab --json
subhunt scan yelp --csv --output yelp.csv

# Monitoring: compare against a previous run
subhunt scan shopify --json --output today.json
subhunt scan shopify --diff today.json
```

### `subhunt scan`

| Option | Description |
| --- | --- |
| `--include-non-bounty` | Include submittable assets without a bounty. |
| `--only-wildcards` | Enumerate only wildcard scopes. |
| `--dns-only` | Keep hosts that resolve, skip HTTP probing. |
| `--json` / `--csv` / `--md` | Output format (default: table). |
| `-o, --output FILE` | Write results to a file. |
| `--diff FILE` | Compare with a previous JSON result. |
| `--concurrency N` | Requests in flight per source / probe (default 25). |
| `--timeout SECONDS` | Per-request timeout (default 8). |
| `--no-cache` | Bypass the local scope cache. |

### `subhunt scope`

Prints the parsed in-scope patterns, out-of-scope patterns, apexes to enumerate, and
the program's category exclusions. Useful to sanity-check before a full run.

### `subhunt mcp`

Runs subhunt as an MCP server over stdio, exposing two tools:
`find_live_subdomains(handle, ...)` and `get_scope(handle, ...)`.

## How it works

```
handle -> HackerOne scope -> apexes -> enumerate -> filter -> alive -> output
```

1. **Scope** - fetch structured scopes and exclusions from the HackerOne API (cached
   locally). Assets are split into in-scope and out-of-scope patterns.
2. **Apexes** - derive the registrable domains to enumerate from each in-scope pattern,
   handling wildcards like `*.example.com`, `*ubereats.com`, and
   `status.*.coinbase.com`.
3. **Enumerate** - `subfinder` if available, otherwise built-in Certificate
   Transparency sources (`crt.sh`, `crt.name`, `agniops`, `jsmon`).
4. **Filter** - keep hosts matching an in-scope pattern and not matching any
   out-of-scope pattern.
5. **Alive** - resolve DNS, then probe HTTP/HTTPS; keep only reachable hosts.
6. **Output** - table, JSON, CSV, Markdown, or bug-bounty-friendly report.

## Scope semantics

- **In scope** - assets where `eligible_for_submission` is true and, unless
  `--include-non-bounty` is set, `eligible_for_bounty` is true.
- **Out of scope** - assets where `eligible_for_submission` is false. These are
  subtracted from the results even when they fall under an in-scope wildcard.
- Wildcards (`*`) are matched at any depth; a bare host like `example.com` covers
  itself and its subdomains.
- Non-host assets (CIDR, IP, mobile apps, source code, hardware, ...) and label-only
  `OTHER` entries are ignored.
- `scope_exclusions` are report *categories*, not hosts, so they are shown by
  `subhunt scope` as notes rather than used for filtering.

## Development

```bash
uv sync --extra dev
uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)

## Disclaimer

Use subhunt only against programs you are authorized to test. Always follow the
program's policy and HackerOne's terms. You are responsible for your own actions.
