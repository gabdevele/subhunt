# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Live progress: `subhunt scan` streams each live host as it is discovered, plus
  per-domain enumeration counts. Structured output stays clean on stdout while
  progress goes to stderr. Disable with `--no-progress`.
- Comprehensive documentation in [`docs/`](docs/README.md): installation,
  configuration, usage, how it works, MCP server setup and troubleshooting.
- `subhunt scan --status-code` (`-sc`): keep only hosts responding with the given
  HTTP status codes (comma-separated, e.g. `200,404`).
- `subhunt scan --enrich`: technology fingerprint, missing security headers, TLS
  certificate (issuer, expiry, SANs) and favicon hash.
- `subhunt scan --takeover`: flag dangling CNAMEs pointing to unclaimed services.
- Enrichment data is emitted under the `enrichment` object (JSON/CSV/Markdown/table)
  and exposed to the MCP tool via `find_live_subdomains(..., enrich=true)`.
- `subhunt scan -H/--header "Name: Value"`: add custom headers to every request
  (repeatable; `{username}` is substituted), and `--h1-header` to send
  `X-HackerOne-Research: <username>`.

### Changed

- Dropped the redundant `url` field from results (JSON, CSV, Markdown, table); the
  reachable URL is always `https://<host>`.

## [0.2.0] - 2026-09-29

### Added

- `subhunt auth login|status|logout`: store HackerOne credentials in the OS keyring,
  with a `0600` file fallback, instead of exporting environment variables.
- `login` verifies the token against the API before saving it.
- Credentials now resolve env → keyring → file and are shared by the CLI and the MCP server.

## [0.1.0] - 2026-09-29

### Added

- `subhunt scan`: enumerate live, in-scope subdomains for a HackerOne program.
- `subhunt scope`: show parsed in-scope, out-of-scope and apex patterns.
- `subhunt mcp`: MCP server exposing `find_live_subdomains` and `get_scope`.
- Scope-aware filtering with wildcard matching and out-of-scope subtraction.
- Hybrid enumeration: `subfinder` when present, built-in CT sources otherwise.
- DNS resolution and HTTP probing of candidates.
- Table, JSON, CSV and Markdown output, plus `--diff` monitoring.
