# subhunt

[![CI](https://github.com/gabdevele/subhunt/actions/workflows/ci.yml/badge.svg)](https://github.com/gabdevele/subhunt/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/subhunt)](https://pypi.org/project/subhunt/)
[![Python](https://img.shields.io/pypi/pyversions/subhunt)](https://pypi.org/project/subhunt/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

`subhunt` turns a HackerOne program handle into a list of live, in-scope
subdomains. It reads the program's structured scope, enumerates the in-scope
wildcards, subtracts out-of-scope hosts, and keeps only the hosts that resolve
and answer over HTTP.

```text
$ subhunt scan hackerone
Enumerating 3 domain(s) via built-in CT sources...
  hackerone-ext-content.com: 41 names
  hackerone-user-content.com: 86 names
132 in-scope candidates, resolving and probing...
  200 b5s.hackerone-ext-content.com
  404 cover-photos.hackerone-user-content.com
  ...

12 live in-scope hosts
```

## Install

```bash
uv tool install subhunt
# or
pipx install subhunt
# or
python -m pip install subhunt
```

From source:

```bash
git clone https://github.com/gabdevele/subhunt
cd subhunt
uv sync
uv run subhunt --help
```

Requires Python 3.11+. [`subfinder`](https://github.com/projectdiscovery/subfinder)
is optional and improves enumeration coverage.

## Credentials

`subhunt` uses the [HackerOne Hacker API](https://api.hackerone.com/getting-started-hacker-api).
Create an API token in your HackerOne settings and store it once:

```bash
subhunt auth login
subhunt auth status
subhunt auth logout
```

The token is kept in your OS secret store (Secret Service on Linux, Keychain on
macOS) and falls back to `~/.config/subhunt/credentials.json` with `0600`
permissions when no keyring backend is available. `H1_USERNAME` and
`H1_API_TOKEN` take precedence over stored credentials, which is useful in CI.

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
| `-sc, --status-code CODES` | Keep only these HTTP status codes (e.g. `200,404`). |
| `--enrich` | Add technology, security headers, TLS info and favicon hash. |
| `--takeover` | Flag dangling CNAMEs / subdomain takeover candidates. |
| `-H, --header "Name: Value"` | Extra header on every request (`{username}` substituted). |
| `--h1-header` | Add `X-HackerOne-Research: <username>` to every request. |
| `--json` / `--csv` / `--md` | Output format (default: table). |
| `-o, --output FILE` | Write results to a file. |
| `--diff FILE` | Compare with a previous JSON result. |
| `--concurrency N` | Requests in flight per source / probe (default 25). |
| `--timeout SECONDS` | Per-request timeout (default 8). |
| `--no-cache` | Bypass the local scope cache. |
| `--no-progress` | Do not stream findings; print the final table instead. |

### Other commands

- `subhunt scope <handle>` prints the parsed in-scope and out-of-scope patterns,
  the apexes to enumerate, and the program's category exclusions.
- `subhunt auth login|status|logout` stores and inspects credentials. `login`
  verifies the token against the API before saving it.
- `subhunt mcp` runs an MCP server over stdio with the tools
  `find_live_subdomains` and `get_scope`.

## How it works

```text
handle -> HackerOne scope -> apexes -> enumerate -> filter -> alive -> output
```

1. **Scope**: fetch structured scopes and exclusions from the HackerOne API
   (cached locally).
2. **Apexes**: derive the registrable domains to enumerate, handling wildcards
   like `*.example.com`, `*ubereats.com` and `status.*.coinbase.com`.
3. **Enumerate**: `subfinder` if available, otherwise built-in Certificate
   Transparency sources (`crt.sh`, `crt.name`, `agniops`, `jsmon`).
4. **Filter**: keep hosts that match an in-scope pattern and no out-of-scope
   pattern.
5. **Alive**: resolve DNS, then probe HTTP/HTTPS and keep reachable hosts.
6. **Output**: table, JSON, CSV or Markdown.

Scope rules:

- **In scope**: `eligible_for_submission` is true and, unless
  `--include-non-bounty` is set, `eligible_for_bounty` is true.
- **Out of scope**: `eligible_for_submission` is false. These are subtracted
  even when they fall under an in-scope wildcard.
- A `*` matches at any depth; a bare host covers itself and its subdomains.
- Non-host assets (CIDR, IP, mobile apps, source code, hardware) are ignored.

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation](docs/installation.md) | Requirements, install, optional `subfinder`, upgrade. |
| [Configuration](docs/configuration.md) | Credentials, environment variables, paths, cache. |
| [Usage](docs/usage.md) | Every command and flag, output formats, monitoring, recipes. |
| [How it works](docs/how-it-works.md) | Scope semantics, enumeration, liveness, output schema. |
| [MCP server](docs/mcp.md) | Add subhunt to opencode, Claude Desktop, Cursor, VS Code. |
| [Troubleshooting](docs/troubleshooting.md) | Credentials, keyring, rate limits, empty results. |
| [FAQ](docs/faq.md) | Scope, safety, and how it compares to other tools. |

## Development

```bash
uv sync --extra dev
uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)

## Disclaimer

Use subhunt only against programs you are authorized to test. Always follow the
program's policy and HackerOne's terms. You are responsible for your own actions.
