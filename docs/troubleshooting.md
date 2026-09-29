# Troubleshooting

## Credentials

### `HackerOne credentials required`

No credentials were found. Run:

```bash
subhunt auth login
```

or export `H1_USERNAME` and `H1_API_TOKEN`. See
[Configuration](configuration.md#credentials).

### `token verification failed: GET ... -> 401`

The token is invalid, expired or revoked. Generate a new API token in your
HackerOne settings and run `subhunt auth login` again.

### `HackerOne API error: GET ... -> 404`

The program handle does not exist, is private and your account is not a member,
or the handle is misspelled. Check the exact handle in the program URL:
`https://hackerone.com/<handle>`.

### `HackerOne API error: GET ... -> 429`

You hit a HackerOne rate limit (600 requests/min overall, 50/min for structured
scopes). subhunt retries after the `Retry-After` delay and caches scope
responses for an hour, so this is usually transient. If it persists, wait a
minute or reuse the cache (avoid `--no-cache`).

## Keyring

### The token was stored in a file, not the keyring

On headless Linux (servers, containers, CI) there is often no Secret Service
backend. `--store auto` detects this and falls back to
`<config>/credentials.json` with `0600` permissions. To force a backend use
`--store keyring` or `--store file`.

### `no keyring backend available on this system`

You used `--store keyring` on a machine without one. Use `--store auto` or
`--store file`, or install a Secret Service provider (for example
`gnome-keyring`).

### `warning: credentials file is readable by other users`

The credentials file permissions are too open. subhunt re-tightens them on load
on Unix; if the warning persists, run `subhunt auth logout && subhunt auth login`
or `chmod 600` the file. On Windows, permissions are handled by ACLs.

## Scan results

### `No in-scope domains found for this program`

The program has no host-like assets (or none that pay a bounty). Inspect it:

```bash
subhunt scope <handle>
subhunt scope <handle> --include-non-bounty
```

Private programs and VDPs may list only apps, source code or CIDRs.

### `No live in-scope hosts found`

Enumeration found names, but none resolved and answered. Try:

- Remove `--only-wildcards` to include bare-host scopes.
- Check DNS for a sample host manually (`dig`).
- Some hosts intentionally do not serve HTTP; use `--dns-only`.

### Enumeration returns few or no names

The built-in sources depend on public Certificate Transparency APIs, which are
sometimes slow or rate-limited. Improvements:

- Install [`subfinder`](installation.md#optional-subfinder) for many more
  sources.
- Retry: `--no-cache` does not affect enumeration, but a later run may see more
  names.
- Verify a source works from your network, for example
  `curl -s 'https://crt.sh/?q=%25.example.com&output=json' | head`.

### subfinder is installed but results are limited

subhunt uses `subfinder` whenever it is on the `PATH`, and does not fall back if
subfinder returns nothing. Make sure it works on its own:

```bash
subfinder -d example.com -silent
```

Some subfinder sources need API keys (`~/.config/subfinder/provider-config.yaml`).
To use the built-in CT sources instead, remove `subfinder` from your `PATH` for
the run.

### Scans are slow

- Raise concurrency: `--concurrency 50`.
- Use `--dns-only` to skip HTTP.
- Scope is intentionally narrow; large programs can still have thousands of
  candidates.

## Output and monitoring

### `diff file <path> not found, skipping comparison`

The file passed to `--diff` does not exist. It must be a JSON result previously
produced by `subhunt scan --json -o <file>`.

### stdout is empty / mixed with progress

With `--json`, `--csv`, `--md` or `-o`, the data goes to stdout and all progress
goes to stderr. If you see progress on stdout, you are likely running without a
structured flag (the default streams findings to stdout). Use `--no-progress`
for a clean final table.

## Platforms

### Windows

`chmod` is a no-op; the credentials file relies on inherited ACLs. The keyring
(Credential Manager) is generally available. Paths use `%APPDATA%` and
`%LOCALAPPDATA%`, see [Configuration](configuration.md#file-locations).

### Empty hostnames or `::1`

`localhost`, `127.0.0.1` and `::1` are never part of a program scope; if you see
them in a result, check that you are using a HackerOne handle and not a local
target.

## MCP

### The client cannot start `subhunt mcp`

The client may not share your shell `PATH`. Use an absolute path
(`which subhunt`) or `uvx`:

```json
{ "command": "uvx", "args": ["--from", "subhunt", "subhunt", "mcp"] }
```

See [MCP server](mcp.md).

### opencode does not show the subhunt tools

opencode loads config at startup. Restart opencode after editing `opencode.json`.

---

Still stuck? Open an issue:
<https://github.com/gabdevele/subhunt/issues>
