# Spec: Monad

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Monad"

## Summary

Add `Monad(Applicative, Bind)`: a pure composition with no new abstract methods, exactly the relationship `Applicative` already has to `Pointed` + `Apply`. Retrofits `Identity` and `Reader`, both of which already satisfy the full requirement from prior rounds.

## Motivation

`Identity` and `Reader` already have everything `Monad` needs (`Applicative` since that round, `Bind` since last round) — this round is almost entirely bookkeeping: declare the composition, test the two laws that only make sense once both halves exist together, and drop the now-redundant explicit bases on the two concrete types.

## Design

### Shape: pure composition, no re-declared methods

```python
class Monad(Applicative[A_co], Bind[A_co], Generic[A_co]):
    """A type that's both Applicative and Bind. No new abstract methods."""
```

Verified against `mypy --strict`: the MRO resolves cleanly (`Box -> Monad -> Applicative -> Pointed -> Bind -> Apply -> Functor -> Functional -> ABC -> Generic -> object`, no conflict) even though `Applicative` and `Bind` both reach `Apply` independently — this is a genuine diamond, not the "redundant explicit base" problem seen in earlier rounds (that was about listing an ancestor a *already-listed* base already reaches; here `Applicative` and `Bind` are both directly, non-redundantly listed, and Python's C3 linearization handles the diamond underneath them without issue).

**Verified `Monad` does not need to re-declare `fmap`/`ap`/`bind`** the way `Applicative` re-declared `fmap`/`ap` from `Apply`. Every chained call in both new laws (`point(a).bind(f)`, `m.bind(point)`) resolved to the concrete type precisely with no loose `Bind[...]`/`Applicative[...]` anywhere in the chain — because each of `Identity`/`Reader`'s own `point`/`ap`/`bind` already narrows to its own concrete type, and `Monad` itself never needs to hand back a generic `Monad[...]`-typed intermediate value the way `Applicative`'s own four-law chain did.

### The two new laws: left and right identity

Associativity was already fully covered by `Bind`'s own law (`docs/specs/bind.md`) and isn't retested here — anything satisfying `Monad` already satisfies `Bind`, and that law doesn't change by adding `Applicative` on top. The two laws genuinely new to this round are exactly the ones `Bind`'s Cross-Product audit deferred:

```
point(a).bind(f) == f(a)               # left identity
m.bind(point) == m                     # right identity
```

Verified directly: both hold for a correct implementation, and left identity genuinely catches a broken `point` (one that silently adds `1` to its argument) — not a vacuous pass.

### Concrete instances: drop the now-redundant explicit bases

`Identity`/`Reader` both already declare `Applicative[A]` and `Bind[A]` explicitly. Once both inherit `Monad[A]` instead, the explicit `Applicative[A]`/`Bind[A]` become redundant bases producing a contradictory MRO — same lesson `Identity`'s own `T-017`/`Reader`'s `T-019` already established when `Applicative` absorbed `Pointed`+`Apply`. `Identity` additionally keeps its unrelated `Extractable[A]` base (a separate branch of the type hierarchy, no interaction with `Monad`'s diamond).

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: any existing type class sharing a concrete instance with `Monad`'s own instances (`Identity`, `Reader`).

- **Monad × Extractable**: `Identity` is both. No *new* law here beyond what already exists — `Pointed`/`Extractable`'s round-trip (`extract(point(a)) == a`) and `Bind`/`Extractable`'s law (`m.bind(f).extract() == f(m.extract()).extract()`) were already tested in their own rounds and don't change by adding the other half. Checked explicitly rather than silently skipped: `Monad` itself adds no new abstract method, so there's no new surface for a genuinely new cross-class law to attach to.
- **Monad × Semigroup / Monoid**: same as `Pointed`'s and `Bind`'s own audits — `Identity`/`Reader`'s `Semigroup`/`Monoid` support is conditional on their held/produced type, structurally unrelated.

## Concrete instances in scope

- `Identity[A]`, `Reader[R, A]` — each drops its redundant explicit `Applicative[A]`/`Bind[A]` bases in favor of `Monad[A]`, with no new methods (everything already implemented).

## Testing strategy

- `tests/test_monad.py`: ABC-level tests (cannot instantiate directly, `Applicative` and `Bind` both in the MRO) via a local illustrative type — same shape as `test_applicative.py`.
- `tests/monad_laws.py`: `assert_monad_law(point, values, equal=None)` — left/right identity, expressed via `point` alone (mirrors `applicative_laws.py`'s shape, which also needs no separate `make`).
- Each concrete type gets a law test via the helper; no new example-based tests needed since `Identity`/`Reader` gain no new methods.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout, Cumulative Regression (full suite every ticket), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Monad` section (concept, the two laws, a runnable example, and a short note on why associativity isn't retested here).
- Short `Monad` mentions in `Identity`'s and `Reader`'s existing sections (mirroring the short `Applicative` mentions already there).

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Const`'s `Monad` instance — excluded, since it was already excluded from `Bind` on the merits (`docs/specs/bind.md`).
- `Const`'s deferred `Pointed`/`Applicative` instance — a separate, still-unstarted follow-up, unrelated to this round.

## Open questions / risks

- None outstanding — every design decision here (the MRO diamond, the no-re-declaration finding, both new laws' genuine catch of a broken instance) was verified directly against `mypy --strict` and at runtime before being written down.
