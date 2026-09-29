# Usage

```
subhunt [--version] <command> [options]
```

| Command | Description |
| --- | --- |
| `subhunt scan <handle>` | Enumerate live, in-scope subdomains for a program. |
| `subhunt scope <handle>` | Show how subhunt parsed the program's scope. |
| `subhunt auth <login\|status\|logout>` | Manage HackerOne credentials. |
| `subhunt mcp` | Run subhunt as an MCP server over stdio. |

Run `subhunt <command> --help` for the full option list.

## Global options

| Option | Description |
| --- | --- |
| `--version` | Print the version and exit. |
| `--help` | Show help for a command and exit. |

## `subhunt scan`

Enumerates the registrable domains derived from the program's in-scope patterns,
filters out-of-scope hosts, then keeps only the ones that resolve and answer over
HTTP.

```bash
subhunt scan shopify
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `<handle>` | - | HackerOne program handle (required). |
| `--include-non-bounty` | off | Include assets that are submittable but pay no bounty. |
| `--only-wildcards` | off | Enumerate only wildcard scopes (`*.example.com`). |
| `--dns-only` | off | Keep hosts that resolve in DNS; skip HTTP probing. |
| `-sc, --status-code CODES` | - | Keep only hosts responding with these HTTP status codes (comma-separated, e.g. `200,404`). |
| `--enrich` | off | Add technology, security headers, TLS info and favicon hash. |
| `--takeover` | off | Flag dangling CNAMEs pointing to unclaimed services. |
| `-H, --header "Name: Value"` | - | Extra header on every request (repeatable); `{username}` is substituted. |
| `--h1-header` | off | Add `X-HackerOne-Research: <username>` to every request. |
| `--json` | off | Output JSON. |
| `--csv` | off | Output CSV. |
| `--md` | off | Output Markdown. |
| `-o, --output FILE` | - | Write results to a file instead of stdout. |
| `--diff FILE` | - | Compare results with a previous JSON result. |
| `--concurrency N` | `25` | Requests in flight per source / probe. |
| `--timeout SECONDS` | `8.0` | Per-request timeout. |
| `--no-cache` | off | Bypass the local H1 scope cache. |
| `--no-progress` | off | Do not stream findings; print the final table. |

### Live progress

While scanning, subhunt reports progress and streams each finding as soon as it
is discovered:

```
Enumerating 3 domain(s) via built-in CT sources...
  hackerone-ext-content.com: 41 names
  hackerone-user-content.com: 86 names
132 in-scope candidates, resolving and probing...
  200 b5s.hackerone-ext-content.com
  404 cover-photos.hackerone-user-content.com
  ...

12 live in-scope hosts
```

- Without `--json/--csv/--md/-o`, findings and the summary go to **stdout**.
- With a structured output, findings and progress go to **stderr** so stdout
  stays clean for pipes:

  ```bash
  subhunt scan shopify --json | jq -r '.[].host'
  ```

- `--no-progress` suppresses the live lines and prints a table at the end
  instead.

### `--dns-only`

Faster, since it skips HTTP. Useful for a first pass or for hosts that serve
non-HTTP protocols:

```bash
subhunt scan shopify --dns-only
```

In this mode `status`, `title` and `server` are empty; only `host` and `ips`
are reported.

### Filtering by status code

Keep only hosts that answer with specific HTTP status codes (comma-separated).
Filtering happens while streaming, so non-matching hosts never appear:

```bash
# only OK pages
subhunt scan shopify --status-code 200

# interesting statuses
subhunt scan shopify --status-code 200,301,401,403

# short flag
subhunt scan shopify -sc 200,404 --json
```

`--status-code` cannot be combined with `--dns-only` (there is no HTTP status in
that mode).

### Enrichment and probes

These stages run on live hosts after liveness and fill the `enrichment` object in
the output:

```bash
subhunt scan shopify --enrich
subhunt scan shopify --takeover
subhunt scan shopify --enrich --takeover --json -o report.json
```

| Flag | Adds |
| --- | --- |
| `--enrich` | `tech` (detected technologies), `missing_headers` (absent security headers), `tls_issuer`, `tls_expires`, `tls_sans` (certificate SANs, often reveal more subdomains), `favicon` (hash for clustering). |
| `--takeover` | `takeover` (service name) when a host's CNAME points to an unclaimed service (GitHub Pages, Heroku, S3, Azure, ...). |

These flags require HTTP probing and cannot be combined with `--dns-only`.

Example JSON result:

```json
{
  "host": "shop.example.com",
  "status": 200,
  "title": "Admin - Shop",
  "server": "nginx",
  "enrichment": {
    "tech": ["Drupal", "Cloudflare"],
    "missing_headers": ["content-security-policy"],
    "tls_issuer": "CN=R3,O=Let's Encrypt,C=US",
    "tls_expires": "2026-12-01",
    "tls_sans": ["shop.example.com", "www.shop.example.com"],
    "favicon": "994047927006b286"
  }
}
```

### Monitoring with `--diff`

Compare the current run against a saved JSON result to see what appeared or
disappeared:

```bash
subhunt scan shopify --json -o today.json
subhunt scan shopify --diff today.json
```

The diff is printed to stderr:

```
+2 new  -1 gone
  + new-api.shopify.com
  + staging.shopify.com
  - old.shopify.com
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (at least one live host found). |
| `1` | Missing/invalid credentials, API error, no in-scope domains, or no live hosts. |

## `subhunt scope`

Shows the parsed scope without scanning, which is handy to sanity-check before a run.

```bash
subhunt scope uber
```

```
╭─ in scope (8) ─────────────────╮
│ *.uber.com                     │
│ uber.com                       │
│ ...                            │
╰────────────────────────────────╯
╭─ out of scope (7) ─────────────╮
│ bizblog.uber.com               │
│ newsroom.uber.com              │
│ ...                            │
╰────────────────────────────────╯
╭─ apexes to enumerate (3) ──────╮
│ ...                            │
╰────────────────────────────────╯
```

| Option | Default | Description |
| --- | --- | --- |
| `<handle>` | - | HackerOne program handle (required). |
| `--include-non-bounty` | off | Include submittable assets without a bounty. |
| `--only-wildcards` | off | Show only wildcard scopes. |
| `--no-cache` | off | Bypass the local H1 scope cache. |

When the program defines category exclusions (for example "Subdomain takeover
without takeover POC"), they are listed as notes.

## `subhunt auth`

See [Configuration](configuration.md#credentials) for details.

| Command | Options |
| --- | --- |
| `auth login` | `--username, -u` · `--token-stdin` · `--store auto\|keyring\|file` · `--no-verify` |
| `auth status` | `--verify / --no-verify` (default: verify) |
| `auth logout` | - |

## `subhunt mcp`

Starts an MCP server over stdio. See [MCP server](mcp.md).

## Output formats

### JSON

```json
[
  {
    "host": "accounts.shopify.com",
    "ips": ["23.227.38.65", "2606:4700::6812:3b"],
    "status": 200,
    "title": "Login - Shopify",
    "server": "cloudflare"
  }
]
```

### CSV

```csv
host,status,title,server,ips
accounts.shopify.com,200,Login - Shopify,cloudflare,"23.227.38.65,2606:4700::6812:3b"
```

### Markdown

```markdown
| Host | Status | Title |
| --- | --- | --- |
| accounts.shopify.com | 200 | Login - Shopify |
```

## Attribution headers

Many programs ask you to identify your traffic. Add the HackerOne attribution
header (using your stored username) to every request with `--h1-header`:

```bash
subhunt scan shopify --h1-header
# sends: X-HackerOne-Research: <your-username>
```

Add any custom header with `-H/--header 'Name: Value'`, repeatable. The
placeholder `{username}` is replaced with your HackerOne username:

```bash
subhunt scan shopify -H 'X-Bug-Bounty: HackerOne-{username}'
subhunt scan shopify -H 'X-HackerOne-Research: {username}' -H 'X-Custom: value'
```

Headers are sent on enumeration requests and on every request to target hosts
(probing and enrichment). They are **not** added to HackerOne API calls.

## Recipes

**First pass, fast, hosts only:**

```bash
subhunt scan shopify --dns-only --json | jq -r '.[].host'
```

**Full report to a file:**

```bash
subhunt scan gitlab --md -o gitlab.md
```

**Weekly monitoring:**

```bash
subhunt scan yelp --json -o yelp-$(date +%F).json
subhunt scan yelp --diff yelp-$(date -d yesterday +%F).json
```

**CI (no keyring, no stored files):**

```bash
H1_USERNAME="$H1_USERNAME" H1_API_TOKEN="$H1_API_TOKEN" \
  subhunt scan shopify --json --no-progress -o shopify.json
```

**Only assets that pay a bounty, wildcards only:**

```bash
subhunt scan coinbase --only-wildcards
```

---

See also: [How it works](how-it-works.md) · [MCP server](mcp.md)
