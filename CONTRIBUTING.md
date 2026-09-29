# Contributing

Thanks for taking the time to contribute.

## Setup

```bash
git clone https://github.com/gabdevele/subhunt
cd subhunt
uv sync --extra dev
```

## Before opening a pull request

```bash
uv run ruff format src tests
uv run ruff check src tests
uv run mypy src
uv run pytest
```

All four must pass. Keep changes focused, add tests for new behavior, and avoid
introducing new dependencies unless they clearly pay for themselves.

## Guidelines

- Keep the code modular, readable and lightly typed. Prefer clear names over comments.
- Do not add network calls to tests; mock HTTP with `respx`.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.

## Commit messages

Short imperative subject lines, e.g. `filter: drop out-of-scope wildcards`.
