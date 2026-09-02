# Spec: Maybe

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Maybe"

## Summary

Add `Maybe[A]` as a sealed `Just[A]` / `Nothing[A]` pair: the first concrete type in Ekans that genuinely, nominally implements the full `Functor → Pointed/Apply → Applicative → Bind → Monad` chain in one round (`Identity`/`Reader` built it up incrementally across many prior rounds). Also the first real short-circuiting `Monad` — every prior short-circuit test in this project (`Bind`'s, `do`'s) leaned on a local, test-file-only double because nothing real existed yet.

## Motivation

`docs/specs/monad.md` and `docs/specs/do.md` both explicitly flagged `Maybe`/`Either` as deferred: "Ekans doesn't ship a `Maybe`/`Either` yet, so there's nothing to demo this against directly today." This spec is that follow-up for `Maybe`. `Either` and `Tuple2` follow as their own separate rounds after this one.

## Design

### Shape: a sealed two-class hierarchy, not an `Optional`-wrapping single class

```python
class Maybe(Monad[A], Generic[A]):
    ...  # abstract

@dataclass(frozen=True, eq=False)
class Just(Maybe[A], Generic[A]):
    value: A

@dataclass(frozen=True, eq=False)
class Nothing(Maybe[A], Generic[A]):
    pass  # no fields
```

Matches Haskell's `data Maybe a = Nothing | Just a` directly, and — per review — chosen specifically over a single class wrapping `Optional[A]` internally because of the project's stated goal of making structural pattern matching easy on exported types: `match m: case Just(value=v): ... case Nothing(): ...` needs two real, distinct dataclasses to work at all. `Nothing` is Ekans' first genuinely zero-field concrete type (`Proxy` was planned for this role but never built).

### The key finding: abstract methods return `Union[Just[B], Nothing[B]]`, not `Maybe[B]`

This is the one design decision the rest of the spec hinges on, and it was **not** the obvious first attempt — verified directly, in this order:

1. **First attempt, matching every prior type's convention**: `Maybe`'s abstract `fmap`/`ap`/`bind`/`point` narrow their return type to `Maybe[B]` (the same pattern `Monad.bind` itself already uses to narrow from `Bind[B]`). This type-checks fine on its own, but breaks structural pattern matching in exactly the way this type exists to support: a function typed to receive/return the abstract `Maybe[int]` and pattern-match on it produces a genuine `mypy --strict` error, **`Missing return statement`**, because mypy cannot prove a `match` over an ABC handle is exhaustive (it has no way to know only two subclasses exist — unlike a `Union`, which is a closed, enumerable type to the checker). Worse: inside the `case Just(value=v):` branch, `v` itself revealed as `Any`, not `int` — the whole point of pattern-matching Just's held value was lost.
2. **Fix, verified**: change every one of `Maybe`'s own abstract signatures (`fmap`, `ap`, `bind`, `point` — not `Monad`'s, `Maybe`'s own re-declarations of them) to return `Union[Just[B], Nothing[B]]` instead of `Maybe[B]`. `Union[Just[B], Nothing[B]]` is a subtype of `Maybe[B]` (both members inherit it), so this is a valid, sound covariant narrowing, same category as every other override-narrowing in this codebase. Verified directly: the same `match`/`case` code now type-checks with **no missing-return error**, `v` narrows to `int` precisely, and — the more surprising part — calling `.bind()` on a *concrete* `Just(value=5)` instance now reveals the precise `Just[int] | Nothing[int]`, not the loose `Maybe[int]` the first attempt gave even for concrete calls. `Nothing`'s own `bind`/`ap`/`fmap` narrow even further, to bare `Nothing[B]` (always correct, since `Nothing` never produces a `Just`) — also verified clean.

This is worth stating plainly: every `Callable[[A], Maybe[B]]`-typed parameter elsewhere in the codebase (e.g. `Bind.bind`'s own inherited signature) still says `Maybe[B]`, which is fine — a caller-supplied function has no reason to promise more than the interface requires. It's specifically `Maybe`'s own declarations of the methods it produces values *from* that get the `Union` treatment, because those are the return positions a pattern-matching caller actually depends on.

### `point`: the one method that isn't abstract on `Maybe`

`fmap`/`ap`/`bind` must stay abstract on `Maybe` and get separately implemented on `Just`/`Nothing`, since their behavior genuinely differs per variant. `point` doesn't — `Maybe.point(value)` is always `Just(value=value)`, matching Haskell's `pure = Just`, with no variant-specific behavior at all. So `point` is defined once, concretely, directly on `Maybe` itself (not abstract, not re-implemented on `Just`/`Nothing`) — the one method in this hierarchy where a single shared implementation is correct rather than a structural cop-out.

### Bare `Nothing()` decays to `Nothing[Never]` without context — a real, documented gap

Verified directly: `Nothing()` with no surrounding context reveals `Nothing[Never]`. `Nothing[int]()` (an explicit bracket) or any context that supplies an expected type (a `Union[Just[int], Nothing[int]]`-annotated target, a parameter expecting `Nothing[int]`) both resolve precisely to `Nothing[int]`. This is the same category of gap `Sum`/`Product`/`Ap`'s bare `mempty()` already required an explicit `Type[X]` argument to avoid — except `Nothing` has no argument slot to put one in (it's genuinely nullary, matching Haskell's `Nothing` constructor exactly), so the mitigation here is different: always construct `Nothing` either with an explicit bracket or in a context that provides one, documented plainly in `docs/HOWTO.md` rather than silently risking a `Nothing[Never]` no one notices.

### `Extractable`: excluded, not deferred

A total `extract() -> A` cannot be defined for `Nothing` — there is no value, and no default to fall back on within `Extractable`'s existing contract (`extract() -> A`, no parameter). Per review: excluded outright, matching `Reader`/`Star`'s existing exclusion style (`docs/specs/extractable.md`) rather than adding new, `Maybe`-specific API surface (e.g. an `extract`-with-default) that isn't part of the currently-speced `Extractable` shape.

### `Semigroup`/`Monoid`: conditional, and genuinely weaker than `Identity`'s

Per review, included this round rather than deferred, because Phase 1 surfaced a real asymmetry worth building and documenting now rather than losing track of later:

```python
def mappend(a: "Maybe[S]", b: "Maybe[S]") -> "Maybe[S]":  # new overload on the existing shared mappend
    match (a, b):
        case (Nothing(), _):
            return b
        case (_, Nothing()):
            return a
        case (Just(value=x), Just(value=y)):
            return Just(value=x.mappend(y))

def mempty(value_type: Type[S]) -> "Maybe[S]":  # new classmethod on Maybe, alongside point
    return Nothing()
```

where `S = TypeVar("S", bound=Semigroup)` — **not** `bound=Monoid`. Verified directly, using a type that's a `Semigroup` but deliberately *not* a `Monoid`: `Maybe.mempty` type-checks and runs cleanly with it. This is a genuine difference from every prior conditional instance (`Identity`/`Const`/`Reader`'s `mempty`, which all need `A: Monoid` because they must produce a real `A` value from `value_type.mempty()`). `Maybe.mempty` never calls `value_type.mempty()` at all — `Nothing()` is unconditionally a valid identity element regardless of what `A` is, so `value_type: Type[S]` exists purely to pin `S` statically (the same erasure-driven reason every other `Type[X]`-taking classmethod in this codebase needs the argument), never touched at runtime. The *overall* instance still needs `S: Semigroup` (not looser than that) because the `Just`/`Just` case of `mappend` genuinely needs to combine two real `A` values — but that's strictly weaker than `Monoid`, and worth having verified rather than assumed by analogy to `Identity`.

### `@do`'s short-circuit guarantee: retrofit with a real regression test

`docs/specs/do.md`'s Open questions section flagged this directly: "Once a real short-circuiting `Monad` instance (`Maybe`/`Either`) exists in a future round, the short-circuit guarantee tested here against a local double should get a real regression test against the shipped type." Per review, done as part of this round: `tests/test_do.py` gets one additional test using real `Just`/`Nothing` (the existing local `_Just`/`_Nothing` double stays — it's still needed to keep `test_do.py` independent of `ekans.maybe`'s existence for the parts of that file predating this round, and the do-notation guarantee is generic over *any* `Monad`, not `Maybe`-specific).

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: `Functor`, `Pointed`, `Apply`, `Applicative`, `Bind`, `Monad` (`Maybe` nominally implements all of them at once, for the first time in one round), `Semigroup`/`Monoid` (new, conditional, per Design above), `Extractable` (compatible in principle — `Identity` implements both — but excluded here, per Design above).

- **`Functor`/`Pointed`/`Apply`/`Applicative`/`Bind`/`Monad` laws**: all directly reusable via the existing law helpers (`assert_functor_laws`, `assert_apply_law`, `assert_applicative_law`, `assert_bind_law`, `assert_monad_law`), called with `make = Just` (mirroring `Identity`'s own precedent — `Just` is the "carries a real value" case these helpers are shaped around). No new law-testing infrastructure needed; `Maybe` is a genuinely nominal instance of everything, unlike `Const`.
- **Nothing's short-circuit behavior is *not* meaningfully exercised by the laws above.** Every one of `Bind`/`Monad`'s associativity/identity laws holds *trivially* for `Nothing` (both sides of every equation collapse to the same constant `Nothing`, regardless of what `f`/`g` do) — a textbook "vacuous pass," the same category flagged in this project's own Phase 1 methodology. Explicit, separate example-based tests are required (not optional) to verify `Nothing.bind`/`.ap`/`.fmap` never call their argument function at all — the actual behavioral guarantee that matters, which an equality-only law can't distinguish from "correctly short-circuits" vs. "coincidentally produces the same result."
- **`Semigroup`/`Monoid` × `Maybe`**: covered fully in the Design section above — this pairing's laws (`mappend` associativity, `mempty` identity, both via the free-function pattern) get direct property tests, same shape as `Identity`/`Const`/`Reader`'s own.
- **`Extractable`**: excluded, per Design above — not a silent omission.

## Concrete instances in scope

- `Just[A]`, `Nothing[A]` — the two variants of `Maybe[A]`.

## Testing strategy

- `tests/test_maybe.py`: construction, equality/hash (per-variant, and confirming `Just(...) != Nothing()` and vice versa), immutability, `match`/`case` exhaustiveness demonstrated directly (a small function using `match` with no fallback `case _:`, verified it type-checks under the project's mandatory `mypy tests --strict`).
- Law tests via the existing helpers (`assert_functor_laws`, `assert_apply_law`, `assert_applicative_law`, `assert_bind_law`, `assert_monad_law`) called against `Just`.
- Explicit `Nothing` short-circuit tests: `Nothing().fmap(f)`/`.ap(...)`/`.bind(f)` never call `f` (asserted via a call-log/side-effect check, same technique already used for `@do`'s short-circuit test) and always return `Nothing`.
- `mappend`/`mempty` example + property tests (associativity, left/right identity), same shape as `Identity`/`Const`/`Reader`'s.
- `tests/test_do.py`: one additional real-`Maybe`-based short-circuit regression test, per Design above.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression against the full existing suite.

## Documentation requirements

- `docs/HOWTO.md`: new `Maybe` section — the sealed `Just`/`Nothing` shape, a runnable `match`/`case` example, the `Union[Just[B], Nothing[B]]`-vs-`Maybe[B]` finding stated plainly (same honest-limitation treatment as the `Any` wall in `@do`'s section), the bare-`Nothing()`-decays-to-`Never` gap and its mitigation, and the `Semigroup`/`Monoid` conditional-instance section explaining why `mempty` only needs `Semigroup`, not `Monoid`.
- Short addition to `@do`'s existing section noting the real short-circuit example now exists.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Either`, `Tuple2` — separate, subsequent rounds.
- An `extract`-with-default method or any other new `Maybe`-specific API surface beyond the standard type-class hierarchy — see the `Extractable` exclusion in Design above.
- Any AST-level or runtime "exhaustiveness enforcement" mechanism beyond what `mypy --strict` already gives via the `Union[Just[B], Nothing[B]]` return-type design — Python has no native sealed-class enforcement, and building one is out of scope.

## Open questions / risks

- The bare-`Nothing()`-decays-to-`Nothing[Never]` gap (Design section) has no code-level fix, only a documentation-level mitigation (always provide context). Worth revisiting if it turns out to bite in practice once real usage accumulates.
- `Either`'s upcoming round will need its own Phase 1 pass on the same `Union`-vs-abstract-return-type question — the finding here is expected to transfer directly (Left/Right is structurally the same "sealed two-variant" shape as Just/Nothing), but that should be verified fresh for `Either`'s own specifics (e.g. which side `fmap` is biased toward) rather than assumed.
