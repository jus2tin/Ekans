# Spec: `ekans.do`

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "do"

## Summary

Add `@do`, a decorator that turns a generator function yielding `Monad[A]` values into a single monadic computation, built on a `bind`-based trampoline. Eliminates manually nested `.bind(lambda a: ...)` chains in favor of linear, procedural-looking code, using only Python's native generator protocol (`yield`/`.send()`) — no AST rewriting, no `__future__` hacks.

## Motivation

Chaining `bind` calls by hand nests one callback inside the next — readable for two steps, a pyramid by four. `@do` lets a user write:

```python
@do
def computation() -> Generator[Monad[int], Any, Monad[int]]:
    a: int = yield container
    b: int = yield another_container(a)
    return Identity(value=a + b)
```

instead of the equivalent manually-nested form, while staying strictly bound to `Monad`'s own `bind` — the decorator adds no new semantics beyond what `bind` already does.

## Design

### Shape: ParamSpec-forwarding decorator over a generator/trampoline

```python
P = ParamSpec("P")
T = TypeVar("T")
U = TypeVar("U")

def do(fn: Callable[P, Generator[Monad[T], Any, Monad[U]]]) -> Callable[P, Monad[U]]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Monad[U]:
        gen = fn(*args, **kwargs)

        def step(val: Any = None) -> Monad[U]:
            try:
                m = gen.send(val)
            except StopIteration as e:
                return e.value  # type: ignore[no-any-return]
            return m.bind(step)

        try:
            initial_m = next(gen)
        except StopIteration as e:
            return e.value  # type: ignore[no-any-return]

        return initial_m.bind(step)

    return wrapper
```

Verified against `mypy --strict`: the decorator's own mechanics — `ParamSpec` argument forwarding, the `Callable[P, Generator[Monad[T], Any, Monad[U]]]` parameter, the `Callable[P, Monad[U]]` return — all type-check cleanly with no errors beyond the two documented `[no-any-return]` ignores below. `reveal_type` on a correctly-annotated `@do`-decorated function's call site resolves precisely to `Monad[U]` for the concrete `U` that function's return annotation names — the *outer* return type is genuinely preserved, not `Any` or bare `Generator`.

**`# type: ignore[no-any-return]`, both occurrences.** `StopIteration.value` is typed `Any` by typeshed. Returning it from a function declared `-> Monad[U]` triggers `mypy --strict`'s `--warn-return-any` check. Verified directly: removing the ignore reproduces the exact error `Returning Any from function declared to return "Monad[U]"  [no-any-return]`. There's no way to narrow `e.value` further — it's the runtime return value of an arbitrary user generator, genuinely untyped at the `StopIteration` boundary — so the ignore is a deliberate, justified escape hatch, not a workaround for a fixable gap.

### The `Any` wall: a real, unavoidable limitation, documented rather than hidden

Python's `Generator[YieldType, SendType, ReturnType]` has exactly one `SendType` for the entire generator. A do-block's `yield` statements each hand back a *different* unwrapped value across steps (an `int` from one container, a `str` from the next) — but the generator's static type can only declare one `SendType` for all of them. Three things were verified directly, not assumed:

1. **Leaving `T` free (as in the shape above) makes `SendType` structurally `Any`.** Every value bound via `yield` inside a do-block (`a = yield container`) is unconditionally typed `Any` — confirmed with `reveal_type`. `mypy --strict` raises **no error** here; the loss is silent.
2. **Pinning `T` to a concrete type does *not* fix this — it trades one problem for another.** Annotating a do-block as `Generator[Monad[int], Any, Monad[str]]` forces every `yield` in that block to wrap exactly `int` — verified directly: yielding a `Monad[str]` partway through a block annotated this way is a genuine `mypy --strict` error (`Argument "value" to "Identity" has incompatible type "str"; expected "int"  [arg-type]`). A block that legitimately yields differently-wrapped monads across steps (the common case — see the Motivation example) cannot be given a precise single `T` without widening it to a common supertype (e.g. `object`), which is the same imprecision as `Any` in different clothes.
3. **A real, verified mitigation exists: annotate the local variable at each `yield` site.** `a: int = yield container` recovers genuine downstream type-checking for `a` from that line onward — confirmed with `reveal_type` (`int`, not `Any`) and confirmed mypy actually enforces it afterward (misusing `a` as a `str` raises a real `[assignment]` error). This works regardless of how `T`/`U` are declared on the surrounding `Generator[...]` annotation, since `Any` is always assignable to an explicitly-annotated target. The cost: that one line becomes an *unverified trust boundary* — nothing checks that the annotation actually matches what the yielded `Monad` wraps at runtime, the same category of trust as any other `Any`-typed boundary crossing (e.g. `json.load()`'s result).

**Decision (per review):** ship `@do` with this limitation documented plainly, not hidden. Two requirements follow directly from the two rounds of clarifying questions:

- Every `@do`-decorated function **must** carry an explicit `Generator[Monad[T], Any, Monad[U]]` return annotation. Without it, `mypy` infers `Monad[Any]` for the whole computation — confirmed directly (`reveal_type` on an undecorated-return-type do-block resolves to `def () -> Monad[Any]`). This is checked only by convention/code review, not enforced by the decorator itself — Python's type system has no mechanism to *require* a caller annotate a parameter's inner generic.
- Every `yield` assignment inside a do-block **must** carry an explicit local type annotation (`a: int = yield container`), documented in `docs/HOWTO.md` as the standard, only-correct way to write a do-block in this codebase — not an optional tip. This is the practical mitigation that makes `@do`'s body genuinely type-checked, at the cost of one unverified annotation per bound name.

### Short-circuiting: correct for free, verified at runtime

`step` unconditionally calls `m.bind(step)` on whatever the generator yields — it never inspects `m` itself. Whether the computation halts is entirely up to the concrete `Monad`'s own `bind`: a short-circuiting instance (a hypothetical `Maybe`'s `Nothing`, an `Either`'s `Left`) that skips calling its argument function naturally prevents `step` — and therefore `gen.send()` — from ever running again. Verified directly with a local `_Just`/`_Nothing` test double: a do-block that yields `_Nothing()` partway through never reaches the code after that `yield`, and the trampoline correctly returns `_Nothing()` without a second `.send()` call. No special-casing needed in `@do` itself — this is a direct, free consequence of the trampoline calling `bind` rather than driving the generator itself.

### Naming and placement

- Module: `src/ekans/do.py`, exporting the single decorator `do`.
- No method-form equivalent — `@do` is a decorator over a generator function, not an operation on an existing `Monad` instance, so the project's "method delegates to free function" API-shape convention doesn't apply here (same as `Star`/`Category`-style constructs that build from a function rather than acting on a value).

### Correction: `Monad[R, A]` in the originating request was a typo

The originating engineering-spec message's reference docstring mentions `Monad[R, A]` in a comment. `Monad` in this codebase is single-parameter (`Monad[A_co]`, per `docs/specs/monad.md`); the two-parameter shape belongs to `Reader[R, A]`. Confirmed with the requester: a loose illustrative slip, not an intentional request for a two-parameter `Monad`. This spec uses `Monad[A]` throughout, matching the rest of the originating reference code (which is itself single-parameter).

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

`@do` introduces neither a new type class nor a new concrete type — it's a free function (a decorator) built entirely on top of the existing `Monad` type class, adding no new capability of its own. The Cross-Product Rule audits interactions between a *new capability* and existing *compatible* type classes; there is no new capability here for another type class to interact with, so there is no new cross-product surface to test. Recorded explicitly per the Invocation rule ("say so explicitly... rather than silently omitting it"), not silently skipped.

The Proof Burden (justifying excluded concrete types) doesn't apply in the usual sense either: `@do` isn't scoped to specific concrete types — it works uniformly for *any* `Monad` instance, by construction (it only ever calls `.bind` and `.point`-shaped construction inside user code, both of which every `Monad` instance already provides). `Const` remains excluded from `Monad` itself, per `docs/specs/monad.md`'s own already-recorded justification — not a new decision made here.

## Concrete instances in scope

- `Identity[A]`, `Reader[R, A]` — both existing `Monad` instances get do-block tests exercising real chained computation.
- A local, test-file-only short-circuiting double (`_Just`/`_Nothing`, matching `tests/test_monad.py`'s illustrative-type convention) — exercises the short-circuit guarantee, since Ekans has no shipped `Maybe`/`Either` yet. Not exported; lives only in `tests/test_do.py`.

## Testing strategy

- `tests/test_do.py`:
  - Equivalence tests: a `@do`-decorated computation over `Identity` and over `Reader` produces the same result as the same computation written as manual, explicit `.bind()` chains — the only property that actually matters here (the decorator is a mechanical rewrite of `bind` chains, not a new semantic).
  - Hypothesis-driven: vary the initial wrapped value(s) via `@given`, rather than a single hardcoded example, consistent with the rest of the project's testing style — though this is not a reusable cross-type law helper the way `assert_monad_law` is, since each do-block is its own distinct function rather than a uniform operation over an arbitrary `Monad`.
  - Short-circuit test: using the local `_Just`/`_Nothing` double, assert a do-block halts at the first `Nothing` and never executes code written after that `yield` (mirrors the Phase 1 probe).
  - `mypy tests --strict` (already mandatory project-wide) is what actually guards `@do`'s typing claims long-term — every do-block written in the test file must carry the required outer `Generator[...]` and per-`yield` local annotations, so a future regression in the decorator's own signature gets caught the same way any other typed test does, without a bespoke typing-only test suite.
- 100% coverage, TDD, Cumulative Regression (full suite every ticket) — no change from existing Code Requirements.

## Documentation requirements

- `docs/HOWTO.md`: new section introducing `@do`, written to the required style (explicit outer `Generator[Monad[T], Any, Monad[U]]` annotation, explicit per-`yield` local annotations) — with the `Any`-wall limitation and its mitigation stated plainly, the same honest treatment given to the Monoid erasure wall and the `Bind` free-function precision gap elsewhere in this doc. Runnable examples using `Identity` (and `Reader`, since it threads an environment through the trampoline in a way worth showing). A short paragraph on short-circuiting, stated conceptually (no shipped `Maybe`/`Either` to demo it against yet, but the reasoning is evergreen and worth having in place before one exists).

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- A real, shipped `Maybe`/`Either` type — deferred; short-circuit coverage this round uses a local test-only double instead (per review).
- AST rewriting, `__future__` hacks, or any codegen-based do-notation approach — explicitly rejected by the originating request; this spec relies solely on native generator mechanics.
- Arity-specific fully-precise helpers (e.g. `do2`/`do3` with independently-typed positional arguments instead of a single generic `T`) — considered during Phase 1 as a hypothetical way to dodge the `Any` wall entirely; rejected because it abandons the actual ask (linear, `yield`-based procedural syntax) in favor of a differently-shaped nested-call API that isn't meaningfully better than today's manual `.bind()` chains.
- A method-form equivalent — doesn't apply; see Naming and placement above.

## Open questions / risks

- The per-`yield` local-annotation idiom is a genuinely unverified trust boundary: nothing checks at type-check time *or* runtime that the annotated type actually matches what the yielded `Monad` wraps. A wrong annotation doesn't raise a type error — it silently produces whatever runtime behavior falls out of treating a mismatched value as the annotated type (e.g. a confusing `AttributeError` several lines later, not at the `yield` site itself). Documented as an accepted, known risk rather than solved.
- Once a real short-circuiting `Monad` instance (`Maybe`/`Either`) exists in a future round, the short-circuit guarantee tested here against a local double should get a real regression test against the shipped type — flagged as a natural follow-up, not required for this round.
