# Ekans

A pure functional experiment in Python.

## Project status

Early stage. Package layout: `src/ekans/`, tests in `tests/`, built with hatchling via `pyproject.toml`. Current types: `Functional`, `Functor`, `Identity`, `Const`.

## Getting Started

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest
mypy src tests --strict
```

## Goals

- This package implements primitives for functional coding in Python. In particular it contains a set of abstract base classes for adding functional behaviors to immutable datatypes.
- Partially the goal of this project is to learn about using Claude. Because of this we'll be using a workflow that is overkill for small personal projects.
- Exploratory for now, but the intent is for this to become usable in a real personal project eventually — so treat the public API as something worth keeping clean and reasonably stable once it exists, not throwaway code.

## Design

- The root of the tree of abstract classes will be an abstract class called Functional.
- This class does nothing but override __setattr__ and __delattr__ to immediately raise an AttributeError.
- From this root capabilities are added on by classes which inherit from it in as small steps as possible. For instance instead of directly creating an Applicative class that requires both `pure` and `ap` there will be a Pointed class which requires `point` and an Apply class which requires `ap`. For convenience there will be an Applicative class that inherits from both.
- The same pattern applies to Monad: rather than requiring `bind` directly on Applicative, there will be a Bind class which requires `bind`, and Monad will inherit from both Applicative and Bind for convenience.
- We will follow the standard family tree of type classes from Haskell as closely as possible.
- This package will inherit from toolz and use its primitives as much as possible.
- The primitives this package exports will be extremely opinionated and they will not feel very pythonic. We will try to get as close to pure typed functional code as we can within Python.
- However at the same time we will also make sure we stay as close to Python's design philosophy as these design choices allow.
- We will make it as easy as possible for the user of this package to use structural pattern matching on it's exported types.

### Immutability

- Concrete types are `@dataclass(frozen=True)`. A frozen dataclass's generated `__init__` assigns fields via `object.__setattr__` internally, so it composes cleanly with `Functional`'s `__setattr__`/`__delattr__` override — construction works, and any mutation attempted afterward raises.

### Equality

- Every generic concrete type overrides `__eq__` (and `__hash__`, since defining `__eq__` clears the dataclass-generated `__hash__`) typed against its own class-scoped TypeVar(s) instead of `object` — e.g. `def __eq__(self, other: "Identity[A]") -> bool:` on `Identity[A]`, with `@dataclass(frozen=True, eq=False)` so the dataclass doesn't also try to generate one. This makes comparisons between mismatched type parameters (`Identity[int](...) == Identity[str](...)`) a hard mypy `[operator]` error instead of a silent runtime `False`, mirroring how Haskell's `Eq` instances are parametrically typed.
- Requires a `# type: ignore[override]` on the definition — mypy considers narrowing `__eq__`'s parameter away from `object` an LSP violation. That's the whole point here, so the ignore is intentional, not a workaround.
- Comparisons against genuinely unrelated types (e.g. `Identity(value=1) == 5`) stay permitted and just evaluate to `False`, same as ordinary Python — only same-class-different-type-parameter comparisons get rejected.
- Worth knowing: mypy's `--strict-equality` (bundled into `--strict`) already flags mismatched dataclass-generated equality on its own, via internal dataclass-plugin typing — it does *not* do this for a hand-written class typed `other: object`. We override explicitly anyway rather than lean on that: it's self-documenting in the code itself, and it doesn't depend on an internal, version-specific mypy behavior that wouldn't apply to a future non-dataclass Functional type.

### Type classes: ABC, not Protocol

- `Functional` and every type class in the hierarchy (`Functor`, `Monad`, `Semigroup`, ...) are `abc.ABC` with `@abstractmethod` — nominal typing. A concrete type must explicitly inherit from the type classes it implements, rather than structurally satisfying them.

### Currying

- Not a hard requirement. `toolz.curry` isn't well-typed enough to survive `mypy --strict` cleanly, so exported functions are not required to be curried. Use plain, fully-typed functions; reach for `functools.partial` locally where it's genuinely ergonomic, but don't build a generic curry utility just to force the point.

### Error handling

- Prefer values over exceptions for expected failure cases: model them with an Either/Result-style type once one exists, rather than raising. Exceptions are reserved for programmer errors and broken invariants — genuine bugs, not expected control flow.

### Laziness

- Support both eager and lazy evaluation where it makes sense for a given type, rather than committing to eager-only or lazy-by-default across the board.

### API shape

- Provide both free functions and methods: a method like `obj.map(f)` should delegate to an underlying free function. Free functions are data-last where that reads naturally, but — per the currying decision above — are not required to support partial application via currying.

### Why Star matters

- `Star[F, A, B]` (wraps `A -> F[B]`) is a priority `Profunctor` instance, not just a rounding-out-the-set addition. When `F` is a `Monad`, composing two `Star`s is Kleisli composition — chaining effectful functions end to end. Giving `Star` its own `Category` instance built on that composition reproduces Haskell's `Kleisli` arrow exactly — the `Arrow` instance used for monadic effects. (Not every `Arrow` is Kleisli-shaped — plain functions form an `Arrow` too, with no box involved at all — but the Kleisli case, the one people actually reach for, is precisely `Star` plus `Category`.) Comes essentially free once `Category`, `Strong`, and `Monad` already exist, rather than needing its own bespoke machinery.

## Type hierarchy

- Functional
    - Endofunctor based structures
        - Pointed — provides `point`; needs only Functional
        - Functor
            - Apply — provides `ap`; needs Functor
                - Applicative — Pointed + Apply
                - Bind — provides `bind`; needs Apply
                    - Monad — Applicative + Bind
    - Algebraic structures
        - Semigroup
        - Monoid
    - Categorical structures
        - Category
        - Profunctor
            - Strong

### First concrete types

- `Identity[A]` (the identity functor) — the first concrete type to implement, to exercise the abstract hierarchy end-to-end before building anything more elaborate like `Maybe` or `Either`.
- `Proxy[A]` (`data Proxy a = Proxy`) — a nullary/phantom type: it carries no runtime field, `A` exists only at the type level, and every value of `Proxy[A]` is interchangeable. Named after Haskell's `Data.Proxy`, deliberately *not* called `Forget` — the `profunctors` package's `Forget r a b = Forget (a -> r)` is a different, non-nullary profunctor (it holds a real function producing `r`; only `b` is phantom). If we ever want that one too, it gets its own name so the two don't collide.
- `Const[A, B]` (`data Const a b = Const a`) — related but distinct from `Proxy`: it holds a real runtime value of type `A` and ignores `B` entirely. This is the type that actually exercises `Functor` over its second parameter (mapping over `B` is a no-op since nothing of that type exists to touch) — worth adding alongside `Proxy`.
- `Star[F, A, B]` (`data Star f a b = Star (a -> f b)`) — wraps a function that returns a value inside a functor `F` instead of a plain one. Gets `Profunctor`/`Strong` once `F: Functor`, and — see "Why Star matters" above — a `Category` instance once `F: Monad`, which is Kleisli composition. A concrete type, not an abstract class, so it lives here rather than in the Type hierarchy above.

## File organization

- One file per class: e.g. `functional.py`, `functor.py`, `monad.py`, `identity.py`, `proxy.py`. Mirrors the Type hierarchy above rather than grouping multiple classes into category modules.

## Conventions

- Style: pure functional — This package only exports pure functions, immutable data classes and abstract base classes.
- Tests: pytest (declared under `[project.optional-dependencies].dev`), plus Hypothesis for property-based testing (see Testing below).
- Keep the venv (`venv/`) out of version control; it's already in `.gitignore` and `.claudeignore`.

## Testing

- 100% test coverage, enforced via pytest.
- Strict TDD: red-green-refactor. Write the failing test before the implementation, for every function and class — no exceptions.
- The red step must be shown, not just asserted. After writing a failing test, actually run it and show the real pytest output (a genuine failure, or a collection/import error if the code under test doesn't exist yet) *before* writing a single line of implementation. Never claim or assume a test is red without having actually run it.
- Every Functor/Applicative/Monad (etc.) instance must additionally pass property-based law tests written with Hypothesis — identity, composition, associativity, and any other laws that type class requires. Example-based pytest tests alone aren't sufficient for type class instances.

## Tooling

- Formatting/linting: black + flake8 + isort.
- Docstrings: Google style (`Args:`/`Returns:`/`Raises:`), required on all public functions.
- Type checking: `mypy src tests --strict`. All public API must pass strict mode, and so must the test suite — no more, no less than what `src` already commits to.
- `src/ekans/py.typed` is the PEP 561 marker declaring the package's inline types are meant to be read by consumers (mypy, editors, downstream projects). Without it, mypy treats any `ekans.*` import from *outside* `src` (test files, downstream code) as untyped `Any`, which silently swallows real errors in code that imports the package rather than living inside it. Confirmed included in the built wheel automatically (hatchling ships every file under a package directory, no extra config needed) and confirmed it's what actually fixes `mypy tests --strict`, not just a symbolic gesture.

### Dependencies

- `toolz` is a runtime dependency (not dev-only) — the design leans on its primitives directly, so it belongs in `pyproject.toml`'s `[project.dependencies]`, not just assumed.

### Python Version

- Requires Python 3.11+ (matches `requires-python` in `pyproject.toml`).

### CI

- GitHub Actions should run lint (black/flake8/isort), `mypy src tests --strict`, and pytest-with-coverage on push. Not yet set up — next concrete infra step.

## Workflow

- This is a personal experiment, not a team project, but part of the point is practicing a heavier, more deliberate workflow with Claude — so don't default to "small project, skip the ceremony."
- Branching: feature branches + PRs, even though it's solo — practicing that flow is part of the goal. PRs get created and merged through `gh` (installed at `~/AppData/Local/Programs/gh`, on PATH); no unmerged feature branches should sit around across sessions.
- Commits: one commit per type/class. Each type class or concrete type (e.g. `Identity`, `Proxy`) lands as its own reviewed commit rather than being batched with others.
- No print()/logging requirement — dropped. A pure functional library shouldn't be reaching for logging as a matter of course; if a genuine need comes up later, decide then rather than enforcing a blanket rule now.

### Spec-driven: spec → tickets → implementation

For any new type class or concrete type (not just Functor — this is the standing process now):

1. **Spec first.** Claude drafts a spec at `docs/specs/<name>.md` (see `docs/specs/functor.md` for the template shape: Status, Summary, Motivation, Design, Concrete instances in scope, Testing strategy, Documentation requirements, Implementation constraints, Out of scope, Open questions/risks). Include law statements or other formal behavior contracts explicitly, not just prose. Every spec's Implementation constraints section includes, at minimum: "Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified." You review and edit it — nothing gets built against an unreviewed spec.
2. **Tickets derive from the spec, not the other way around.** Once the spec is stable, Claude breaks it into tickets in `TICKETS.md` (see that file's own header for format/lifecycle) — one ticket per deliverable, each naming which spec it came from.
3. **Signature review before implementation.** Before writing any code for a ticket, Claude posts just the Python signature(s) and docstring(s) it plans to use — no bodies, no tests yet. Wait for an explicit "approved" before writing anything else. This is per ticket, not per spec — a code sketch already shown in the spec doesn't count as pre-approval for the ticket's actual signature.
4. **Implementation follows the existing Code Requirements and TDD** (see Testing above) per ticket, once its signature is approved.
5. **Claude closes each ticket itself** once its Definition of Done is verifiably met — no separate sign-off step. `docs/HOWTO.md` gets updated as part of the ticket that introduces the documented concept, not as an afterthought.
6. The spec+ticket artifacts themselves go through the normal branch+PR workflow like any other change.

## Code Requirements

- 100% test coverage (use pytest; see Testing above for the TDD and Hypothesis requirements)
- All exported names must be fully typed (mypy strict mode)
- Use structural pattern matching (match/case) for control flow instead of if/elif chains
- No unhandled exceptions — document or raise intentionally; prefer value-based error handling per the Error handling section above
- Docstrings on all public functions (Google style)
- No `# type: ignore` comments unless they name the exact error code (e.g. `# type: ignore[override]`) and carry a one-sentence comment explaining why Python's type system forced it. A bare `# type: ignore` is never acceptable — it silences everything, not the one specific thing that's actually intentional.

## Documentation

- Every concept, type class, and function gets covered in the how-to guide at `docs/HOWTO.md` — docstrings are for API reference, this is for actually explaining things.
- Format: it starts as a single Markdown "article" — one `##` section per concept, self-contained enough (explains that one concept without leaning on later sections) that it can later be split into separate pages (e.g. `docs/wiki/<concept>.md`, linked from an index) Wikipedia-style, without a rewrite. One file until there's enough content to justify splitting it.
- Tone: fun and light, not a dry reference — concrete, playful examples over exhaustive prose. Explain the underlying theory (category theory / Haskell terms) but keep it approachable; assume a curious reader, not an FP expert.
- Update it in the same commit that introduces the concept/type/function it documents — keeps it honest alongside the one-commit-per-type workflow.
- Concepts from the Type hierarchy that aren't implemented yet still get a short stub entry (what it'll do, one or two sentences) rather than being omitted, so the article's shape matches the full planned hierarchy from day one.
