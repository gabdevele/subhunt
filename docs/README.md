# subhunt documentation

**subhunt** turns a HackerOne program handle into a list of *live, in-scope*
subdomains. It reads the program's structured scope, enumerates every in-scope
wildcard, removes out-of-scope hosts, and keeps only the ones that resolve and
answer over HTTP.

## Contents

| Guide | What it covers |
| --- | --- |
| [Installation](installation.md) | Requirements, install with `uv`/`pipx`/`pip`, optional `subfinder`, upgrade and uninstall. |
| [Configuration](configuration.md) | Credentials (`auth login`), environment variables, storage backends, file paths, cache. |
| [Usage](usage.md) | Every command and flag, output formats, progress, monitoring, exit codes, recipes. |
| [How it works](how-it-works.md) | The pipeline, scope semantics, enumeration backends, liveness checks, output schema. |
| [MCP server](mcp.md) | Expose subhunt to opencode, Claude Desktop, Cursor, VS Code and any MCP client. |
| [Troubleshooting](troubleshooting.md) | Credentials, keyring, rate limits, empty results, platform quirks. |
| [FAQ](faq.md) | Short answers about scope, safety and how it compares to other tools. |

## Quick reference

```bash
subhunt auth login                       # store HackerOne credentials once
subhunt scope shopify                    # inspect parsed scope
subhunt scan shopify                     # live, in-scope subdomains
subhunt scan shopify --json -o out.json  # machine-readable, streamed progress on stderr
subhunt mcp                              # run as an MCP server (stdio)
```

New here? Start with [Installation](installation.md) then
[Configuration](configuration.md).

> Use subhunt only against programs you are authorized to test.
