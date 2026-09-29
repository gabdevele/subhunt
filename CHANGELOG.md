# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-29

### Added

- `subhunt scan`: enumerate live, in-scope subdomains for a HackerOne program.
- `subhunt scope`: show parsed in-scope, out-of-scope and apex patterns.
- `subhunt mcp`: MCP server exposing `find_live_subdomains` and `get_scope`.
- Scope-aware filtering with wildcard matching and out-of-scope subtraction.
- Hybrid enumeration: `subfinder` when present, built-in CT sources otherwise.
- DNS resolution and HTTP probing of candidates.
- Table, JSON, CSV and Markdown output, plus `--diff` monitoring.
