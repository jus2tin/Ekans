# Ekans

A pure functional experiment in Python.

## Project status

Early stage. Package layout: `src/ekans/`, tests in `tests/` (not yet created), built with hatchling via `pyproject.toml`.

## Conventions

- Style: functional — prefer pure functions, immutable data, and composition over classes/mutable state.
- Tests: pytest (declared under `[project.optional-dependencies].dev`).
- Keep the venv (`venv/`) out of version control; it's already in `.gitignore` and `.claudeignore`.

## Working with this repo

- This is a personal experiment, not a team project — favor small, direct changes over heavy process.
- There is no CI configured yet.
