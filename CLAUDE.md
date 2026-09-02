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

- `Functional` and every type class in the hierarchy (`Functor`, `Monad`, `Semigroup`, ...) are `abc.ABC` with `@abstractmethod` — nominal typing. A concrete type must explicitly inherit from the type classes it implements, rather than structurally satisfying them. Deliberate exception: `Foldable` — see "Why Foldable is a Protocol" below.

### Currying

- Not a hard requirement. `toolz.curry` isn't well-typed enough to survive `mypy --strict` cleanly, so exported functions are not required to be curried. Use plain, fully-typed functions; reach for `functools.partial` locally where it's genuinely ergonomic, but don't build a generic curry utility just to force the point.

### Error handling

- Prefer values over exceptions for expected failure cases: model them with an Either/Result-style type once one exists, rather than raising. Exceptions are reserved for programmer errors and broken invariants — genuine bugs, not expected control flow.

### Laziness

- Support both eager and lazy evaluation where it makes sense for a given type, rather than committing to eager-only or lazy-by-default across the board.

### API shape

- Free functions are the primary, central API surface — not methods. In practice, when a type nominally implements a type class, the method holds the real implementation and the free function delegates to it (e.g. `ap(f, x)` returns `x.ap(f)`); methods exist for ergonomics ("for funsies" — `obj.map(f)` reads nicer than `map(f, obj)`) but are never the only way to do something, and are not load-bearing for the library's actual capability.
- This matters most for constrained/conditional instances, where a concrete type can't nominally inherit a type class at all (e.g. `Identity[A]` is only a `Semigroup` when `A` is — see `Semigroup`'s design) but can still satisfy the free function via a bound `TypeVar`. In that case there is no method — the free function is the *only* interface, not just the preferred one. Design new type-class support free-function-first; add a method alongside it only when a type genuinely, nominally implements the class.
- Free functions are data-last where that reads naturally, but — per the currying decision above — are not required to support partial application via currying.

### Why Star matters

- `Star[F, A, B]` (wraps `A -> F[B]`) is a priority `Profunctor` instance, not just a rounding-out-the-set addition. When `F` is a `Monad`, composing two `Star`s is Kleisli composition — chaining effectful functions end to end. Giving `Star` its own `Category` instance built on that composition reproduces Haskell's `Kleisli` arrow exactly — the `Arrow` instance used for monadic effects. (Not every `Arrow` is Kleisli-shaped — plain functions form an `Arrow` too, with no box involved at all — but the Kleisli case, the one people actually reach for, is precisely `Star` plus `Category`.) Comes essentially free once `Category`, `Strong`, and `Monad` already exist, rather than needing its own bespoke machinery.

### Why Foldable is a Protocol

- `Foldable` deliberately breaks the "ABC, not Protocol" rule above. It's a `typing.Protocol` requiring only `__iter__` — structural, not nominal — so any existing iterable (`list`, `tuple`, `dict`, a generator, a custom type that already defines `__iter__` for unrelated reasons) satisfies it automatically, with no explicit inheritance needed. That's the opposite situation from every other type class here: `ap`, `point`, `fmap`, etc. aren't standard Python protocols, so nothing already implements them by accident, which is exactly why ABC's nominal-inheritance requirement isn't a cost there. `__iter__` is different — tons of types already have it for reasons that have nothing to do with `Foldable` — so this is the one place Protocol earns its keep instead of just being a different way to spell the same thing.
- All of `Foldable`'s actual operations (fold, `toList`, length, sum, whatever else lands) are free functions taking anything satisfying the protocol, not methods declared on it — the protocol itself declares nothing but `__iter__`. Every one of those functions is built on top of `__iter__` alone.
- Implementation detail worth recording now, before it's built: those free functions hide a trampoline internally. A naively recursive fold blows Python's default recursion limit on any moderately large iterable; a trampoline (bounce a thunk through an explicit loop instead of actually recursing) keeps the public function's behavior looking like ordinary recursive-style folding while staying stack-safe underneath.
- Alongside the Protocol, there's also an optional ABC (working name `FoldableABC` — the name may get refined when this is actually spec'd) that a concrete type can inherit from to override individual operations like `foldr` with something more efficient than the generic `__iter__`-driven default (e.g. a type with O(1) access to its length shouldn't have to fold to compute one). Free functions check for that override first — `isinstance(x, FoldableABC)` and the specific method actually being overridden — and fall back to the generic trampoline-based implementation otherwise. This mirrors Haskell's own `Foldable`: a minimal-complete-definition method (`foldr`) with default implementations for everything else, where individual instances are free to override any of them. The point of keeping both: a plain `list` (which will never inherit anything) still gets every operation for free through the Protocol + defaults, while a type that legitimately benefits from a custom implementation isn't stuck with the generic one.

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
- Foldable — not a `Functional` subclass; a `typing.Protocol` requiring only `__iter__`. See "Why Foldable is a Protocol" above.

### First concrete types

- `Identity[A]` (the identity functor) — the first concrete type to implement, to exercise the abstract hierarchy end-to-end before building anything more elaborate like `Maybe` or `Either`.
- `Proxy[A]` (`data Proxy a = Proxy`) — a nullary/phantom type: it carries no runtime field, `A` exists only at the type level, and every value of `Proxy[A]` is interchangeable. Named after Haskell's `Data.Proxy`, deliberately *not* called `Forget` — the `profunctors` package's `Forget r a b = Forget (a -> r)` is a different, non-nullary profunctor (it holds a real function producing `r`; only `b` is phantom). If we ever want that one too, it gets its own name so the two don't collide.
- `Const[A, B]` (`data Const a b = Const a`) — related but distinct from `Proxy`: it holds a real runtime value of type `A` and ignores `B` entirely. This is the type that actually exercises `Functor` over its second parameter (mapping over `B` is a no-op since nothing of that type exists to touch) — worth adding alongside `Proxy`.
- `Star[F, A, B]` (`data Star f a b = Star (a -> f b)`) — wraps a function that returns a value inside a functor `F` instead of a plain one. Gets `Profunctor`/`Strong` once `F: Functor`, and — see "Why Star matters" above — a `Category` instance once `F: Monad`, which is Kleisli composition. A concrete type, not an abstract class, so it lives here rather than in the Type hierarchy above.
- `Reader[R, A]` (`newtype Reader r a = Reader (r -> a)`) — the function arrow `(-> r)` as a first-class value; `Functor`/`Pointed` over `A`, `R` fixed. Special case: wraps a function, so it deliberately gets no type-safe `__eq__` the way `Identity`/`Const` do — functions aren't structurally comparable in Python. See `docs/specs/reader.md`.

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

### Implementation Protocol (spec → tickets → implementation)

**Invocation:** "let's follow the implementation protocol for: `<Name>`" means run every phase below, in order, for that type class or concrete type. Don't skip a phase or collapse two together, even if a phase looks trivial for this particular `<Name>` — say so explicitly and move on, rather than silently omitting it. This is the standing process for any new type class or concrete type, not a Functor-specific one-off.

**Phase 0 — Clarifying questions (at most 30, batched via `AskUserQuestion`, ~4 per batch).**
Ask only about genuine, unresolved forks for this specific `<Name>` — don't re-litigate patterns already settled elsewhere in this file (equality convention, ABC-vs-Protocol default, currying, etc.). Recurring categories worth checking every time:
- Method and free-function naming, and free-function argument order.
- Which concrete types get retrofitted in this round vs. deferred, and why if there's a known blocker (e.g. `Const` needing `Semigroup`/`Monoid`).
- Typing-precision approach for any new abstract method — instance methods and classmethods behave differently here (see Phase 1).
- Law-testing scope: which laws, and whether an existing law-helper should be extended rather than duplicated.
- Anything the user themselves flagged as conditional ("if scoped", "if needed") — resolve it explicitly rather than assuming either way.

**Phase 1 — Technical verification, before writing anything down.**
Every factual claim that goes into the spec must be checked, not asserted — this project has hit real, non-obvious mypy behavior on nearly every round so far. For each new piece of design, build it in a throwaway scratch file and run `mypy --strict` on it (delete the scratch file once done):
- If composing multiple existing ABCs, confirm the MRO actually resolves — and check whether a base already reachable through another listed base is now redundant (drop it; a redundant explicit base produces a contradictory MRO, not a harmless duplicate).
- If overriding an inherited abstract method, check exactly which error code(s) mypy raises. Instance methods with a `self`-bound TypeVar usually only complain about narrowed parameters; classmethods (method-scoped TypeVars, no `self` to bind them) often complain about both parameter and return.
- If adding a free function with per-type `@overload`s, verify actual precision with `reveal_type` — a bare class reference (not yet a constructed value) is the known failure mode, silently degrading to `Any` with no error; values that already carry their own type parameter are usually fine.
- If adding a law, work out the exact formula by hand, then verify it holds for a correct implementation *and* gets caught by a deliberately broken one. Watch for "vacuous pass" gotchas — a law can be trivially satisfied by a bug that just short-circuits (e.g. "ignore the argument, return `self` unchanged" satisfied `Apply`'s associativity law even though it's obviously wrong).

**Phase 2 — Draft the spec, wait for approval.**
`docs/specs/<name>.md` (see `docs/specs/functor.md` for the template shape: Status, Tickets link, Summary, Motivation, Design, Concrete instances in scope, Testing strategy, Documentation requirements, Implementation constraints, Out of scope, Open questions/risks). Every Design claim states what Phase 1 actually verified — "Verified against `mypy --strict`: ..." — not just what's intended. Every spec's Implementation constraints section includes, at minimum: "Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified." `Status: Draft — awaiting review` until approved, then flip to `Approved` in the same PR that gets merged. Nothing gets built against an unreviewed spec.

**Phase 3 — Tickets derive from the spec, not the other way around.**
Once the spec is approved, break it into tickets in `TICKETS.md` (see that file's own header for format/lifecycle) — one ticket per deliverable, each naming which spec it came from. No spec, no ticket.

**Phase 4 — Per ticket: signature review, then TDD, then close.**
1. **Signature review before implementation.** Post just the Python signature(s) and docstring(s) planned — no bodies, no tests yet. Wait for an explicit "approved" before writing anything else. This is per ticket, not per spec — a code sketch already shown in the spec doesn't count as pre-approval for the ticket's actual signature.
2. **Show the red step.** Write the failing test(s) first, run them, and show the actual pytest output (a real failure or a collection/import error) before writing any implementation code. Never claim or assume a test is red without having run it.
3. **Implement exactly what was approved.** No unrequested convenience functions, helper utilities, or alternative syntax sugar.
4. **Run the full check suite:** `pytest` (100% coverage), `mypy src tests --strict`, `black --check`, `isort --check`, `flake8`.
5. **Every `# type: ignore` names its exact error code and carries a one-sentence explanation** of why Python's type system forced it. A bare `type: ignore` is never acceptable.
6. **If real friction surfaces — a design gap, not just a typing nit — fix it at the source, don't paper over it with ignores.** Document the correction plainly in both the spec (a "Correction found during T-XXX, applied to T-YYY's file" note) and the ticket's own text, even when it means editing an earlier, already-committed ticket's file on the same branch.
7. **Verify free-function precision with a throwaway probe** (`src/ekans/_probe.py` + `reveal_type`), then delete it.
8. **Update `docs/HOWTO.md` with a real section or addition, not a stub.** If no concrete type implements the new class yet, use a small local illustrative type (matching the existing `Box` pattern) rather than one that doesn't actually support it yet. Verify every example in the doc actually runs before committing it — don't assume.
9. **Close the ticket** (`**Status:** Closed` in `TICKETS.md`) once its Definition of Done is verifiably met — no separate sign-off step required.
10. **Commit with a message that explains what shipped and any corrections/gotchas found along the way**, not just "implements X."

**Phase 5 — PR and merge.**
Push the branch, open a PR summarizing every ticket closed and any notable findings from Phase 1/4, merge it via `gh` (installed at `~/AppData/Local/Programs/gh`, on PATH), sync local `main`, and prune stale remote-tracking branches (`git fetch origin --prune`) so unmerged feature branches don't pile up across sessions.

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
