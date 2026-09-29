# MCP server

subhunt can run as a [Model Context Protocol](https://modelcontextprotocol.io)
server, so AI agents and editors can enumerate a HackerOne program's live,
in-scope subdomains on your behalf.

## Run the server

```bash
subhunt mcp
```

This starts a **stdio** MCP server. The client launches the process and speaks
the protocol over stdin/stdout, so you normally do not run it by hand.

## Tools

### `find_live_subdomains`

Enumerate live, in-scope subdomains for a program handle.

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `handle` | string | - | HackerOne program handle. |
| `include_non_bounty` | bool | `false` | Include submittable assets without a bounty. |
| `only_wildcards` | bool | `false` | Enumerate only wildcard scopes. |
| `dns_only` | bool | `false` | Keep hosts that resolve, skip HTTP probing. |
| `enrich` | bool | `false` | Also collect technology, headers, TLS and takeover candidates. |

Returns a JSON array of results (same fields as `subhunt scan --json`), with an
`enrichment` object per host when `enrich` is true:

```json
[
  {
    "host": "accounts.shopify.com",
    "ips": ["23.227.38.65"],
    "status": 200,
    "title": "Login - Shopify",
    "server": "cloudflare"
  }
]
```

### `get_scope`

Return the parsed scope without scanning.

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `handle` | string | - | HackerOne program handle. |
| `include_non_bounty` | bool | `false` | Include submittable assets without a bounty. |
| `only_wildcards` | bool | `false` | Only wildcard scopes. |

Returns:

```json
{
  "program": "shopify",
  "in_scope": ["*.shopify.com", "shopify.com", "..."],
  "out_of_scope": ["cdn.shopify.com", "..."],
  "apexes": ["shopify.com", "..."],
  "exclusions": ["Subdomain takeover without takeover POC"]
}
```

## Credentials for the MCP process

The server resolves credentials exactly like the CLI: environment variables →
OS keyring → credentials file. Because it runs as your user, credentials stored
with `subhunt auth login` are picked up automatically, with no extra configuration.

If you prefer to pass them explicitly (for example in a shared config), use the
client's environment field. See the examples below.

## opencode

Add to `opencode.json` (project) or `~/.config/opencode/opencode.json` (global):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "subhunt": {
      "type": "local",
      "command": ["subhunt", "mcp"],
      "enabled": true
    }
  }
}
```

To pass credentials explicitly:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "subhunt": {
      "type": "local",
      "command": ["subhunt", "mcp"],
      "environment": {
        "H1_USERNAME": "{env:H1_USERNAME}",
        "H1_API_TOKEN": "{env:H1_API_TOKEN}"
      }
    }
  }
}
```

opencode reads config at startup and does not hot-reload: **restart opencode**
after editing.

## Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "subhunt": {
      "command": "subhunt",
      "args": ["mcp"]
    }
  }
}
```

## Cursor

Edit `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "subhunt": {
      "command": "subhunt",
      "args": ["mcp"]
    }
  }
}
```

## VS Code (GitHub Copilot)

Edit `.vscode/mcp.json`:

```json
{
  "servers": {
    "subhunt": {
      "type": "stdio",
      "command": "subhunt",
      "args": ["mcp"]
    }
  }
}
```

## Generic stdio client

Any MCP client that supports stdio servers can use:

- **Command:** `subhunt`
- **Arguments:** `mcp`

If subhunt is not on the client's `PATH`, use an absolute path (find it with
`which subhunt`), or run it through `uvx` without installing:

```json
{
  "command": "uvx",
  "args": ["--from", "subhunt", "subhunt", "mcp"]
}
```

## Notes

- The MCP server performs the same network activity as `subhunt scan`: DNS
  resolution and HTTP probing of in-scope hosts only.
- Scans via MCP can be slow for large programs; prefer `dns_only` for quick
  lookups and reserve full scans for deeper sessions.
- The program handle is the only required argument. Out-of-scope hosts and
  `scope_exclusions` are handled exactly as in the CLI.

---

See also: [Configuration](configuration.md) · [Usage](usage.md)
