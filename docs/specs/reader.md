# Spec: Reader

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Reader"

## Summary

Add `Reader[R, A]` — the function-arrow type `(-> r)` as a first-class value: a frozen dataclass wrapping a function `R -> A`, implementing `Functor[A]` (via composition) and `Pointed[A]` (via a new `const` combinator). Also extends the shared `assert_functor_laws` test helper with an optional custom equality comparator, since `Reader` can't reuse its existing `==`-based law checking.

## Motivation

Every concrete type so far (`Identity`, `Const`) wraps a plain, comparable *value*. `Reader` wraps a *function* — the environment-passing pattern (dependency injection without a framework, essentially). It's the plainest possible "computation," and — not incidentally — it's exactly the shape `Star`'s Kleisli-arrow story (see `docs/HOWTO.md`'s `Star` stub, and CLAUDE.md's "Why Star matters") builds on: `Reader r a` is `Star Identity r a`, or equivalently `a -> r` generalized to `r -> f a` for `f = Identity`. Building `Reader` now is a concrete stepping stone toward that later work, not a detour from it.

## Design

### Shape

```python
R = TypeVar("R")
A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class Reader(Functor[A], Pointed[A], Generic[R, A]):
    run: Callable[[R], A]

    def fmap(self, f: Callable[[A], B]) -> "Reader[R, B]":
        return Reader(run=lambda r: f(self.run(r)))

    @classmethod
    def point(cls, value: A) -> "Reader[R, A]":  # type: ignore[override]
        return Reader(run=const(value))
```

Verified against `mypy --strict`: `add_one.fmap(str)` (where `add_one: Reader[int, int]`) reveals `Reader[int, str]` — same return-type-narrowing pattern as `Identity`/`Const`'s `fmap`, no ignore needed. `point`'s override needs `# type: ignore[override]` on both parameter and return type, same reason as `Identity`/`Const`'s `point`: method-scoped TypeVars, not self-bound, so mypy can't establish substitutability.

`R` doesn't appear in `Reader`'s ABC parameterization (`Functor[A]`, `Pointed[A]`) at all — same asymmetric shape `Const[A, B]` already established (there, `B` was the ABC-relevant parameter and `A` was fixed-but-unrelated-to-the-ABC; here `A` is ABC-relevant and `R` is fixed-but-unrelated). `R` at a `Reader.point(...)` call site is inferred from context (an annotation or an assignment target) exactly the way `Const`'s held type is at `Const.point(...)` — unconstrained by the call itself.

### The `const` combinator

```python
def const(value: A) -> Callable[[C], A]:
    def _ignore(_: C) -> A:
        return value

    return _ignore
```

Haskell's `const :: a -> b -> a`, spelled the way this project already spells "curried-shaped" functions (a function returning a function, not literal currying — see CLAUDE.md's Currying section) since `Reader.point` needs a `Callable[[R], A]` directly. `C` (the ignored parameter's type) appears *only* in the return position — verified this infers correctly from call-site context (`Reader.point("hi")` assigned to a `Reader[int, str]`-annotated target correctly reveals `Reader[int, str]`, with the environment type `int` never appearing anywhere in the call).

Placement: lives in `src/ekans/reader.py` itself, not a new general-purpose combinators module — it's currently only consumed by `Reader.point`. If a broader need for Haskell Prelude-style combinators shows up later, it can move; inventing that module now would be exactly the kind of unrequested convenience infrastructure the Implementation constraints below rule out.

### Equality: deliberately none

`Reader` does **not** get a type-safe `__eq__` like `Identity`/`Const`. Functions in Python don't have structural equality — two closures computing identical results are never `==` unless they're the same object. Giving `Reader` a reference-based `__eq__` (the dataclass default, or Python's own `object.__eq__`) would be actively misleading: `Reader(run=f).fmap(str)` builds a *new* closure every time, so it would never equal anything except itself, making equality effectively useless without ever looking broken. Leaving `__eq__`/`__hash__` untouched (default `eq=True` dataclass behavior, comparing `run` by reference, consistent with how bare functions already compare) is the honest option — it's exactly as expressive as comparing two Python functions with `==` normally is, no more, no less.

### Testing implication: `assert_functor_laws` needs a custom equality hook

Since `Reader` instances can't be compared with `==` in any meaningful way, the existing `assert_functor_laws(make, values)` helper (built for `Identity`/`Const`, which checks laws via `x.fmap(f) == y`) can't test `Reader` as-is. Extend it with an optional `equal` parameter, defaulting to `==`:

```python
def assert_functor_laws(
    make: Callable[[A], Functor[A]],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Functor[A], Functor[A]], bool]] = None,
) -> None:
```

Verified backward-compatible: `Identity`'s existing law tests (which don't pass `equal`) still pass unchanged against the extended signature. `Reader`'s law tests pass a comparator that samples several environment values and compares `.run(env)` outputs — extensional equality (functions are equal if they agree on every input; sampling approximates that, the same principle Hypothesis already applies to values). Verified this genuinely catches breakage, not just passing vacuously, against a deliberately unlawful `Reader` (one that double-applies `f`).

This generalizes the helper for any future computation-wrapping type with the same problem (e.g. a later `State[S, A]`, which wraps `S -> (A, S)`) without duplicating law-checking logic per type.

### `__call__`: bridging to plain Python callables

```python
def __call__(self, r: R) -> A:
    return self.run(r)
```

Verified against `mypy --strict`: `reader(5)` and `reader.run(5)` both reveal the same precise type, no friction, no `type: ignore` needed — `__call__` isn't inherited from any base class `Reader` already has, so there's nothing to narrow or override. Delegates directly to `run`; not part of `Functor`/`Pointed`, just a Python-ergonomics addition so a `Reader` can be passed anywhere a plain `Callable[[R], A]` is expected (e.g. `map()`, or composed with other plain functions) without callers needing to remember `.run(...)`.

## Concrete instances in scope

- **`Reader[R, A]`** — the type itself, both `Functor` and `Pointed` instances, in this round (unlike `Identity`/`Const`, which got `Functor` and `Pointed` as separate rounds — `Reader`'s `Pointed` instance has no `Const`-style blocker, so there's no reason to split it here).

## Testing strategy

- `assert_functor_laws` extended per Design above; existing `Identity`/`Const` law tests continue to pass unmodified.
- `Reader`'s law tests call the extended helper with a comparator sampling several environment values.
- `const`: a small standalone example-based test (a couple of values, a couple of ignored-argument types).
- `Reader`: construction, `fmap` composes correctly (verified via `.run(env)` on both sides, not `==`), `point` constructs correctly, `point(...).fmap(...)` chains, immutability still holds.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Reader` section — concept, the equality wrinkle explained as real theory (not a caveat to apologize for), a runnable example, and the `const` combinator introduced alongside `point`.
- No dedicated `const` subsection — it's documented as part of `Reader`'s `point`, not as its own concept, matching its scoped-to-Reader placement in Design above.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Reader`'s `Apply`/`Bind`/`Monad` instances — later specs, once those type classes exist.
- A general-purpose combinators module for `const` and friends (`identity`, `flip`, etc.) — `const` stays co-located with `Reader` per Design above; revisit only if a second consumer actually shows up.
- Formalizing `Reader`'s relationship to `Star`/`Kleisli` from CLAUDE.md's Design section — mentioned in Motivation as context, not built now; depends on `Category`, which doesn't exist yet.

## Open questions / risks

- `const`'s current placement (inside `reader.py`) is a bet that nothing else needs it soon. If `Apply`/`Applicative` end up needing a similar combinator shortly after, worth revisiting before duplicating logic.
- `assert_functor_laws`'s `equal` parameter is opt-in and untyped-by-default (`Optional[Callable[...]]`) — worth watching whether a *required* comparator (no default) reads better once more computation-wrapping types exist, so the choice is always explicit rather than implicit in whether a type happens to support `==`.
