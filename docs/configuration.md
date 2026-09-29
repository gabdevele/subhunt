# Configuration

## Credentials

subhunt talks to the [HackerOne Hacker API](https://api.hackerone.com/getting-started-hacker-api),
which uses **HTTP Basic authentication** with an API token identifier and value.

1. Sign in to HackerOne and generate an API token under **Settings → API Token**.
2. Store it once:

   ```bash
   subhunt auth login
   ```

   You are prompted for your **username** and the **API token**. The token input
   is hidden, so it never appears on screen or in your shell history. subhunt
   verifies the token against the API before saving it.

That is all. `subhunt scan`, `subhunt scope` and the MCP server now use it.

### Non-interactive login

Useful for provisioning or scripts. The token is read from stdin, so it is not
recorded in history:

```bash
printf '%s\n' "$TOKEN" | subhunt auth login --username alice --token-stdin
```

Skip the API check with `--no-verify` if you are offline:

```bash
subhunt auth login --username alice --token-stdin --no-verify
```

### Check and remove credentials

```bash
subhunt auth status    # source, username and validity; never prints the token
subhunt auth logout    # removes the keyring entry and the credentials file
```

## Credential resolution order

1. **Environment variables** `H1_USERNAME` and `H1_API_TOKEN` (both must be set).
2. **OS keyring** (Secret Service on Linux, Keychain on macOS, Credential
   Manager on Windows).
3. **Credentials file** `<config>/credentials.json` with `0600` permissions.

`subhunt auth status` prints which source is in use. Environment variables win,
which is convenient for CI:

```bash
export H1_USERNAME="alice"
export H1_API_TOKEN="..."
subhunt scan shopify
```

## Storage backends

`subhunt auth login` accepts `--store auto|keyring|file`:

- `auto` (default): use the OS keyring when a backend is available, otherwise
  fall back to the file. You are told which backend was used.
- `keyring`: require the OS keyring; fails if none is available.
- `file`: always write `<config>/credentials.json` (no keyring involved).

The keyring entry uses service `subhunt` and account `default`.

### File permissions

The credentials file is created with `0600` inside a `0700` directory. On load,
the permissions are re-tightened automatically (on Unix). If the file is ever
readable by other users, `subhunt auth status` warns you.

> On headless Linux (servers, containers, CI) there may be no Secret Service
> backend. subhunt detects this and falls back to the credentials file with
> `auto`. Use environment variables in CI if you prefer not to write a file.

## File locations

subhunt follows the [platformdirs](https://github.com/platformdirs/platformdirs)
conventions:

| | Configuration (`credentials.json`) | Cache |
| --- | --- | --- |
| **Linux** | `~/.config/subhunt/` (or `$XDG_CONFIG_HOME/subhunt`) | `~/.cache/subhunt/` (or `$XDG_CACHE_HOME/subhunt`) |
| **macOS** | `~/Library/Application Support/subhunt/` | `~/Library/Caches/subhunt/` |
| **Windows** | `%APPDATA%\subhunt\` | `%LOCALAPPDATA%\subhunt\Cache` |

## Cache

HackerOne scope responses are cached locally to respect the API rate limits
(600 requests/min overall, 50/min for structured scopes). The cache is keyed per
program handle and has a default **TTL of one hour**.

- Bypass the cache for a single run with `--no-cache` (on `scan` and `scope`).
- To purge everything, delete the cache directory (see the table above).

## Environment variables

| Variable | Purpose |
| --- | --- |
| `H1_USERNAME` | HackerOne username (takes precedence over stored credentials). |
| `H1_API_TOKEN` | HackerOne API token (takes precedence over stored credentials). |
| `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` | Override config/cache locations on Linux (via platformdirs). |

`H1_USERNAME` and `H1_API_TOKEN` must both be set to be used.

## Uninstall / cleanup

Removing the package does not delete your credentials or cache. To clean up:

```bash
subhunt auth logout
rm -rf ~/.config/subhunt ~/.cache/subhunt        # Linux
# rm -rf ~/Library/Application\ Support/subhunt ~/Library/Caches/subhunt   # macOS
# rmdir /s %APPDATA%\subhunt & rmdir /s %LOCALAPPDATA%\subhunt             # Windows
```

---

See also: [Usage](usage.md) · [MCP server](mcp.md) · [Troubleshooting](troubleshooting.md)
