# Spec: Tuple2

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Tuple2"

## Summary

Add `Tuple2[A, B]` — Haskell's `(,) a b` pair — as a single concrete type: nominal `Functor[B]` (unconditional), plus the conditional, free-function/classmethod-based `Applicative`/`Bind`-shaped operations `Const` already established the pattern for (`point`, `ap`, `liftA2`, `bind`, `mappend`, `mempty`), all bounded on `A: Semigroup`/`A: Monoid`. Also gives `Tuple2` its own pointwise `Semigroup`/`Monoid` instance — a genuinely new pattern requiring *two* independent bounds (`A: Semigroup` *and* `B: Semigroup`), not yet built anywhere in this codebase.

## Motivation

The third and final type requested alongside `Maybe`/`Either`. Unlike those two, `Tuple2` is a genuine product type (one class, two real fields, no sealed-variant complexity) — structurally, its closest sibling in this codebase turns out to be `Const`, not `Maybe`/`Either`, once Phase 1 verification is done.

## Design

### Shape: one class, nominal `Functor[B]` only

```python
@dataclass(frozen=True, eq=False)
class Tuple2(Functor[B], Generic[A, B]):
    first: A
    second: B

    def fmap(self, f: Callable[[B], C]) -> "Tuple2[A, C]":
        return Tuple2(first=self.first, second=f(self.second))
```

`A`/`B` naming, `first`/`second` fields — per review, matching `Const`'s own `A`/`B` convention directly (`A` = the untouched-by-`fmap` slot, `B` = `Functor`'s operand), since `Tuple2` turns out to be `Const`'s closest sibling here, not `Either`'s. `first`/`second` chosen over Haskell's `fst`/`snd` for readability without requiring Haskell familiarity. `fmap` is nominal and unconditional — mapping over `B` never touches `A` at all, so there's no constraint-expressibility problem here, same as `Const.fmap`.

### Nominal `Apply`/`Applicative`/`Bind` is impossible — same wall as `Const`, verified fresh

A naive nominal `Apply[B]` attempt (`ap` combining both sides' `A` values via `self.first.mappend(f.first)`) hits the identical error `Const`'s own attempt did: `"A" has no attribute "mappend"  [attr-defined]`. `Tuple2` is a single class shared by every instantiation, including ones where `A` isn't a `Semigroup` — Python's ordinary nominal inheritance has no way to make `Apply[B]` conditional on `A`'s own constraint, the same structural reason `Const`'s conditional instance exists in the first place (`docs/specs/const-applicative.md`'s Design section).

### The interesting contrast with `Const`: real capability, not a degenerate case

`Const`'s conditional `ap`/`point` never touch a real function or a real second value — `B` is permanently phantom for `Const`, so `ap` only ever combines the two sides' `A` values via `mappend` and `point` only ever discards its argument. `Tuple2` is different: `B` is a *real* field here, so the conditional operations do genuine work, matching Haskell's actual instance:

```python
@classmethod
def point(cls, value_type: Type[S_MON], value: B) -> "Tuple2[S_MON, B]":
    return Tuple2(first=value_type.mempty(), second=value)
```
`pure x = (mempty, x)` — unlike `Const.point`, `value` is genuinely used, not discarded, since it becomes the real `second` field.

```python
def ap(f: "Tuple2[S_SEMI, Callable[[B], C]]", x: "Tuple2[S_SEMI, B]") -> "Tuple2[S_SEMI, C]":
    return Tuple2(first=x.first.mappend(f.first), second=f.second(x.second))
```
`(u, f) <*> (v, x) = (u <> v, f x)` — the function in `f.second` genuinely gets applied to `x.second`, verified directly at runtime (not just type-checked): combining `Tuple2(first=_SemiBox(1), second=5)` and `Tuple2(first=_SemiBox(2), second=str)` via this `ap` produces `Tuple2(first=_SemiBox(3), second='5')` — both the `mappend` *and* the function application actually happened.

`bind` is the same story — genuinely useful, not degenerate, but *still* structurally blocked from being nominal for the identical constraint-expressibility reason `ap`/`point` are:

```python
def bind(x: "Tuple2[S_SEMI, B]", f: "Callable[[B], Tuple2[S_SEMI, C]]") -> "Tuple2[S_SEMI, C]":
    result = f(x.second)
    return Tuple2(first=x.first.mappend(result.first), second=result.second)
```
`(u, x) >>= f = let (v, y) = f x in (u <> v, y)`. Worth stating plainly since it could be misread otherwise: `Const` was excluded from `Bind` for *two* independent reasons (`docs/specs/bind.md`) — zero new capability beyond `fmap`, *and* a genuine precision failure. `Tuple2`'s `bind` fails neither of those tests (it does real, useful work, and stays precisely typed, verified with `reveal_type`) — it's excluded from *nominal* `Bind` purely on the constraint-expressibility ground alone, a structurally different (and narrower) reason than `Const`'s.

`liftA2` gets the same `Semigroup`-bound overload treatment `ap` does, added to the existing shared free function, mirroring `Const`'s own `liftA2` addition.

### `Extractable`: a real instance, and the standard laws hold directly — unlike `Const`'s

`extract() -> B`, matching `Functor`'s own bias (the slot actually being computed), per review. Verified directly, all three standard cross-class laws hold for `Tuple2` in their *original*, undiluted form — not the weaker mappend-only variants `Const` needed:

- **`Pointed`/`Extractable` round-trip**: `extract(point(a)) == a`. Holds directly — `point`'s `second` field literally *is* the passed value, unlike `Const.point`, which discards it (breaking this law there entirely, per `docs/specs/const-applicative.md`).
- **`Apply`/`Extractable` commutation**: `x.ap(f).extract() == f.extract()(x.extract())`. Holds directly, the same shape as `Identity`'s own law — because `Tuple2`'s `ap` genuinely applies the function, this is the real commutation law, not `Const`'s degenerate `mappend`-only substitute.
- **`Bind`/`Extractable`**: `m.bind(f).extract() == f(m.extract()).extract()`. Holds directly, same shape as `Identity`'s.

### `Tuple2`'s own `Semigroup`/`Monoid`: a genuinely new two-bound pattern

Per review, included this round. Every prior conditional instance in this codebase (`Identity`/`Const`/`Reader`/`Maybe`) needed exactly one bound. `Tuple2`'s own instance — distinct from the `A`-only bound its `Applicative`-shaped operations need — needs *two independent* bounds simultaneously, since it combines both fields pointwise:

```python
def mappend(a: "Tuple2[SA, SB]", b: "Tuple2[SA, SB]") -> "Tuple2[SA, SB]":
    return Tuple2(first=a.first.mappend(b.first), second=a.second.mappend(b.second))

def mempty(a_type: Type[MA], b_type: Type[MB]) -> "Tuple2[MA, MB]":
    return Tuple2(first=a_type.mempty(), second=b_type.mempty())
```
where `SA`/`SB` are independently bound to `Semigroup` and `MA`/`MB` independently bound to `Monoid`. Verified directly: this compiles cleanly, and — the concrete proof the two bounds are independently enforced, not just nominally declared — calling `mempty` with one argument that's only a `Semigroup` (not a full `Monoid`) while the other is a real `Monoid` is a genuine `mypy --strict` `[type-var]` error, not a silent pass.

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: `Functor` (nominal), `Pointed`/`Apply`/`Applicative`/`Bind` (conditional, non-nominal — same shape as `Const`'s), `Extractable` (nominal), `Semigroup`/`Monoid` (conditional, two independent flavors — `Tuple2`'s own pointwise instance, and the single-`A`-bound instance the `Applicative`-shaped operations use).

- **`Pointed`/`Apply`/`Bind` × `Extractable`**: all three standard laws hold directly, per Design above — the headline finding of this round, genuinely different from `Const`'s weaker substitutes.
- **`Tuple2`'s own `Semigroup`/`Monoid` × `Extractable`**: `mappend(x, y).extract() == x.extract().mappend(y.extract())`, same shape as `Identity`/`Const`'s existing law, holds directly since `extract` returns `second` and `mappend` combines `second` fields pointwise.
- **The two `Semigroup`/`Monoid` flavors don't interact with each other** — `Tuple2`'s own instance (`A`+`B` both bounded) and the `Applicative`-shaped operations' instance (`A` alone bounded) are independent uses of the same underlying type classes on different slots; no shared law connects them beyond what's already covered above.

## Concrete instances in scope

- `Tuple2[A, B]` only.

## Testing strategy

- `tests/test_tuple2.py`: construction, equality/hash (both type parameters checked independently, `Const`'s established two-parameter Equality convention), immutability.
- `assert_functor_laws` applies directly (nominal `Functor`).
- No `assert_apply_law`/`assert_applicative_law`/`assert_bind_law` usage — same reasoning as `Const`'s testing strategy (these assume a real nominal instance).
- Direct Hypothesis property tests for the `Applicative` laws (identity, homomorphism, interchange, composition) against the free `point`/`ap` functions — per review, followed through on rather than left as `docs/specs/const-applicative.md`'s own flagged "worth a second look" open question, since `Tuple2`'s `ap` does real work where `Const`'s didn't, making these genuinely meaningful checks rather than vacuous ones.
- The three `Extractable` cross-product laws from the Design section above, as direct property tests.
- `Tuple2`'s own `mappend`/`mempty` example and property tests (associativity, left/right identity), plus a genuine `[type-var]` rejection test for a partial-`Monoid` pair, mirroring the Design section's verification.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression against the full existing suite.

## Documentation requirements

- `docs/HOWTO.md`: new `Tuple2` section — the nominal-`Functor`-but-conditional-everything-else shape, contrasted directly against `Const` (real capability vs. `Const`'s degenerate case), the three `Extractable` laws holding in their full form, and the two-independent-bound `Semigroup`/`Monoid` pattern.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- Any N-ary tuple generalization (`Tuple3`, etc.) — not requested.
- A `Bifunctor`-style instance mapping over both `A` and `B` simultaneously — `Bifunctor` isn't in this codebase's planned type hierarchy; `Tuple2` stays `Functor[B]`-biased only, matching `Const`'s and `Either`'s own single-slot bias.

## Open questions / risks

- None outstanding — every design decision here (the nominal-inheritance wall, the real-vs-degenerate capability contrast, all three `Extractable` laws, and the two-independent-bound `Semigroup`/`Monoid` pattern) was verified directly against `mypy --strict` and at runtime before being written down.
