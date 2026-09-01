# Ekans

A pure functional experiment in Python.

## Project status

Early stage. The repo currently contains only project scaffolding (README, LICENSE, `.gitignore`) — no source layout, package manager, or tests have been established yet.

## Conventions

- Style: functional — prefer pure functions, immutable data, and composition over classes/mutable state.
- No source, dependency, or test tooling is set up yet. When adding it, prefer standard, low-ceremony choices (e.g. a single `pyproject.toml`, stdlib `unittest`/`pytest`) unless told otherwise.
- Keep the venv (`venv/`) out of version control; it's already in `.gitignore` and `.claudeignore`.

## Working with this repo

- This is a personal experiment, not a team project — favor small, direct changes over heavy process.
- There is no CI configured yet.
