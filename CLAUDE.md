# Ekans

A pure functional experiment in Python.

## Project status

Early stage. Package layout: `src/ekans/`, tests in `tests/` (not yet created), built with hatchling via `pyproject.toml`.

## Getting Started

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest
mypy src --strict
```

## Goals

This package implements primitives for functional coding in Python. In particular it contains a set of abstract base classes for adding functional behaviors to immutable datatypes.

## Design

- The root of the tree of abstract classes will be an abstract class called Functional.
- This class does nothing but override __setattr__ and __delattr__ to immediately raise an AttributeError.
- From this root capabilities are added on by classes which inherit from it in as small steps as possible. For instance instead of directly creating an Applicative class that requires both `pure` and `ap` there will be a Pointed class which requires `point` and an Apply class which requires `ap`. For convenience there will be an Applicative class that inherits from both.
- We will follow the standard family tree of type classes from Haskell as closely as possible.
- This package will inherit from toolz and use it's primitives as much as possible.
- The vast majority of exported functions will be curried.
- The primitives this package exports will be extremely opinionated and they will not feel very pythonic. We will try to get as close to pure typed functional code as we can within Python.
- However at the same time we will also make sure we stay as close to Python's design philosophy as these design choices allow.
- We will make it as easy as possible for the user of this package to use structural pattern matching on it's exported types.

## Type hierarchy

- Functional
    - Endofunctor based structures
        - Functor
        - Applicative
        - Monad
    - Algebraic structures
        - Semigroup
        - Monoid
    - Categorical structures
        - Category
        - Profunctor
            - Strong

## Conventions

- Style: pure functional — This package only exports pure functions, immutable data classes and abstract base classes.
- Tests: pytest (declared under `[project.optional-dependencies].dev`).
- Keep the venv (`venv/`) out of version control; it's already in `.gitignore` and `.claudeignore`.

## Working with this repo

- This is a personal experiment, not a team project — favor small, direct changes over heavy process.
- There is no CI configured yet.

## Code Requirements

- 100% test coverage (use pytest)
- All exported names must be fully typed (mypy strict mode)
- Use structural pattern matching (match/case) for control flow instead of if/elif chains
- No unhandled exceptions—document or raise intentionally
- No print() statements, use logging instead
- Docstrings on all public functions

### Type Checking

Run mypy with: `mypy src --strict`
All public API must pass strict mode.

### Python Version
Requires Python 3.10+ (for structural pattern matching)