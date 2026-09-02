# Spec: Either

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Either"

## Summary

Add `Either[L, R]` as a sealed `Left[L, R]` / `Right[L, R]` pair, biased to `Right` — `Monad[R]`, with `L` threaded through as an invariant second type parameter both variants carry but only one actually holds. The second short-circuiting `Monad` in Ekans, after `Maybe`, and the first sealed type where *both* variants hold real, non-phantom data (`Maybe`'s `Nothing` holds nothing at all).

## Motivation

`docs/specs/maybe.md`'s Open questions section flagged this directly: "`Either`'s upcoming round will need its own Phase 1 pass on the same `Union`-vs-abstract-return-type question... that should be verified fresh for `Either`'s own specifics... rather than assumed." This spec is that follow-up.

## Design

### Shape: `Either[L, R]`, biased `Monad[R]`, matching `Maybe`'s sealed pattern

```python
class Either(Monad[R], Generic[L, R]):
    ...  # abstract

@dataclass(frozen=True, eq=False)
class Left(Either[L, R], Generic[L, R]):
    value: L

@dataclass(frozen=True, eq=False)
class Right(Either[L, R], Generic[L, R]):
    value: R
```

Matches Haskell's `data Either a b = Left a | Right b`, with the conventional `Functor`/`Monad` bias to `Right` (the "success" side): `fmap`/`ap`/`bind` all operate on `R`, leaving `L` untouched — `Left`'s own `fmap`/`ap`/`bind` are no-op re-tags of `L`, structurally identical to `Const.fmap`'s re-tagging of its own untouched parameter. Per review: `L`/`R` naming (not `A`/`B` or `E`/`A`) — reads directly off `Left`/`Right`, and the Functor bias is stated in terms of the names themselves rather than needing a separate mnemonic.

Verified against `mypy --strict`: `class Either(Monad[R], Generic[L, R])` — mixing `Monad[R]`'s own covariant type parameter with `Either`'s two, independently-declared `Generic[L, R]` parameters — compiles cleanly, no variance conflict.

### The `Maybe` finding transfers directly: abstract methods return the `Union`

Verified fresh, not assumed: `Either`'s own `fmap`/`ap`/`bind`/`point` return `Union[Left[L, R2], Right[L, R2]]`, not the abstract `Either[L, R2]`. Same exhaustiveness/narrowing benefit confirmed directly with a `match`/`case` function typed against the `Union` (both branches narrow precisely, `L`/`R` included) versus the abstract handle (same `Missing return statement` failure `Maybe` hit).

### The genuinely new finding: `Left` gets real, nominal `Bind`/`Monad` — unlike `Const`

This needed direct verification, not an assumption from `Maybe`'s precedent: `Const` was excluded from `Bind` (`docs/specs/bind.md`) because its phantom parameter gave a `bind` with "zero new capability" and a genuine precision failure (`Const.bind(...)` resolving to `Const[int, Never]`). `Left` looks superficially similar — `Left.bind` also ignores its argument and re-tags a phantom-for-this-branch parameter (`R`, not `L`) — but verified directly: `Left(value="boom").bind(lambda r: Right(value=str(r)))` reveals a precise `Left[str, str] | Right[str, str]`, not `Never` anywhere. The difference: `Const` has no sibling variant that ever holds a real value of the phantom type, so nothing in the whole type ever gives `mypy` a real `B` to reason about. `Left` does have one — `Right`, the other half of the same sealed `Either` — so `R` is a real, inferable type across the pair even on the branch that doesn't hold it, the same way `Nothing[A]`'s `A` stays real and inferable because `Just[A]` exists. `Left`/`Right` together form one genuine `Monad` instance; `Const` never had a partner type to complete one with.

### A real, better-behaved variant of `Maybe`'s bare-construction gap

Verified directly, and worth contrasting with `Maybe`'s: `Nothing()` alone (no fields at all) silently decays to `Nothing[Never]`, no error. `Left(value="boom")`/`Right(value=5)` are different — each has one real field pinning *one* of the two type parameters concretely (`L=str` for `Left`, `R=int` for `Right`), and the *other*, phantom-for-that-branch parameter is what's left unconstrained. Assigning either to an **unannotated** variable produces a real, loud `mypy --strict` error (`Need type annotation for "..."  [var-annotated]`) rather than a silent decay — `mypy` refuses to guess, instead of guessing `Never` the way it does for `Nothing`'s fully-fieldless case. Passed directly to `reveal_type()` (no assignment), the phantom side still shows `Never`, same underlying gap — so the mitigation is the same as `Maybe`'s (bracket explicitly, e.g. `Left[str, int](value="boom")`, or supply an annotated target), just enforced more often since most real code assigns to a variable rather than passing a bare expression to `reveal_type`.

### `Extractable`: excluded, same reasoning as `Maybe`

Neither `Left` nor `Right` can give a total `extract() -> R` — `Left` has no `R` at all, mirroring exactly why `Maybe`'s `Nothing` excluded `Extractable`. (A hypothetical `extract() -> L` on `Left` isn't part of `Extractable`'s existing single-total-value shape either, and isn't added here — same Proof Burden reasoning `Maybe` already established for not inventing new API surface beyond the current type-class shape.)

### `Semigroup`/`Monoid`: excluded structurally, not deferred

Per review: unlike `Maybe`, Haskell's own base library defines no `Semigroup`/`Monoid` instance for `Either` at all — there's no canonical `mappend`/`mempty` shape to port the way `Maybe`'s `Nothing <> x = x` is a direct transcription of a real instance. Building one for Ekans would mean inventing a specific policy (first-`Right`-wins? accumulate `Left`s? something else?) rather than porting an established one, and no such policy was requested. Recorded as a structural exclusion, matching the Proof Burden convention — not a "later round" deferral the way `Maybe`'s round-vs-round split for `Semigroup` support after `Const` was.

### `@do`'s short-circuit guarantee: a second real regression test

Per review, included this round: `tests/test_do.py` gets one more test, using real `Left`/`Right`, alongside the existing `Maybe`-based one from `docs/specs/maybe.md`'s own round — `docs/specs/do.md`'s original follow-up note named both `Maybe` and `Either` explicitly, and this closes it out completely.

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: `Functor`, `Pointed`, `Apply`, `Applicative`, `Bind`, `Monad` (all nominal, same as `Maybe`), `Extractable` (compatible in principle, excluded per Design above), `Semigroup`/`Monoid` (compatible in principle via `Maybe`'s precedent, excluded per Design above — no natural instance).

- **`Functor`/`Pointed`/`Apply`/`Applicative`/`Bind`/`Monad` laws**: reused via the existing law helpers, called with `make = Right` (the value-carrying, non-short-circuiting side — same role `Just` played for `Maybe`).
- **`Left`'s short-circuit behavior is not meaningfully exercised by the laws above**, for the identical reason `Maybe`'s `Nothing` wasn't: every law involving a `Left` collapses both sides of its equation to the same re-tagged `Left`, a vacuous pass. Explicit, separate tests are required (not optional), matching `Maybe`'s own testing strategy.
- **`Extractable`**: excluded, per Design above — not a silent omission.
- **`Semigroup`/`Monoid`**: excluded, per Design above — not a silent omission, and not the same kind of exclusion as `Extractable`'s (structural impossibility) — this one is "no canonical instance exists to port," recorded as its own distinct reasoning.

## Concrete instances in scope

- `Left[L, R]`, `Right[L, R]` — the two variants of `Either[L, R]`.

## Testing strategy

- `tests/test_either.py`: construction, equality/hash (per-variant, both type parameters checked independently — same two-parameter Equality convention `Const` already established — and confirming `Left(...) != Right(...)` even when the held values happen to compare equal), immutability, `match`/`case` exhaustiveness demonstrated directly (mirroring `test_maybe.py`'s `_describe` helper).
- Law tests via the existing helpers (`assert_functor_laws`, `assert_apply_law`, `assert_applicative_law`, `assert_bind_law`, `assert_monad_law`) called against `Right`.
- Explicit `Left` short-circuit tests: `Left(...).fmap`/`.ap`/`.bind` never call their argument function (call-log check, same technique as `Maybe`'s), always return a re-tagged `Left` holding the same `L` value.
- The `case _: raise AssertionError` fallbacks in `Right.ap`/`.bind` (needed for the same reason `Just`'s were — `mypy` can't prove a `match` over the abstract `Either` parameter type is exhaustive) verified as real safety nets via a test-only third `Either` subclass, mirroring `test_maybe.py`'s `_RogueMaybe`.
- `tests/test_do.py`: one additional real-`Either`-based short-circuit regression test, per Design above.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression against the full existing suite.

## Documentation requirements

- `docs/HOWTO.md`: new `Either` section — the sealed shape and `Right`-bias, a runnable `match`/`case` example, the `Union[Left[L,R2], Right[L,R2]]`-vs-`Either[L,R2]` finding (can reference `Maybe`'s section rather than re-deriving the whole argument, since it's the same underlying reason), the *better-behaved* bare-construction gap (a real `mypy` error rather than `Maybe`'s silent decay) contrasted directly against `Maybe`'s own section, and a short note on why `Semigroup`/`Monoid` don't appear here the way they did for `Maybe`.
- Short addition to `@do`'s existing section noting the second real short-circuit example.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Semigroup`/`Monoid` for `Either` — excluded structurally, per Design above, not deferred.
- `Extractable` for `Either` — excluded structurally, per Design above.
- `Tuple2` — a separate, subsequent round.
- Any `Left`-biased alternative or a way to flip which side `Functor`/`Monad` operate on — not requested; `Right`-bias matches Haskell's own convention directly.

## Open questions / risks

- None outstanding beyond what's already flagged as excluded-not-deferred above — every design decision here was verified directly (the `Union`-return finding, `Left`'s real `Bind`/`Monad` capability, and the bare-construction `var-annotated` behavior) before being written down.
