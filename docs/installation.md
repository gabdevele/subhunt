# Installation

## Requirements

- **Python 3.11 or newer** (3.11, 3.12 and 3.13 are tested in CI).
- **Linux, macOS or Windows.**
- A **HackerOne account with an API token**, see
  [Configuration](configuration.md#credentials).
- **Optional:** [`subfinder`](https://github.com/projectdiscovery/subfinder) for
  wider enumeration coverage. Without it, subhunt uses built-in Certificate
  Transparency sources. No Go toolchain is required for the built-in path.

DNS resolution and HTTP probing are built into subhunt (via `dnspython` and
`httpx`); you do **not** need `dnsx`, `httpx` or `massdns`.

## Install

Pick one method. `uv` and `pipx` install the `subhunt` command in an isolated
environment and are recommended.

### uv (recommended)

```bash
uv tool install subhunt
```

### pipx

```bash
pipx install subhunt
```

### pip

```bash
python -m pip install --user subhunt
```

### Run without installing (uvx)

```bash
uvx subhunt --help
```

## From source

```bash
git clone https://github.com/gabdevele/subhunt
cd subhunt
uv sync
uv run subhunt --help
```

For development (tests, linting, type checking):

```bash
uv sync --extra dev
uv run pytest
```

## Optional: subfinder

`subfinder` aggregates many passive sources and improves coverage. If it is on
your `PATH`, subhunt uses it automatically; otherwise it falls back to the
built-in sources.

```bash
# Any one of these
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
brew install subfinder
# ProjectDiscovery package manager
go install github.com/projectdiscovery/pdtm/cmd/pdtm@latest && pdtm -install subfinder
```

Verify:

```bash
subfinder -version
```

## Verify the installation

```bash
subhunt --version
subhunt --help
```

Expected output includes a version string and the `scan`, `scope`, `auth` and
`mcp` commands.

## Upgrade

```bash
uv tool upgrade subhunt      # uv
pipx upgrade subhunt         # pipx
python -m pip install -U subhunt
```

## Uninstall

```bash
uv tool uninstall subhunt    # uv
pipx uninstall subhunt       # pipx
python -m pip uninstall subhunt
```

To also remove stored credentials and cache, see
[Uninstall / cleanup](configuration.md#uninstall--cleanup).

---

See also: [Configuration](configuration.md) · [Usage](usage.md)
