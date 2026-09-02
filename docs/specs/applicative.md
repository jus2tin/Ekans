# Spec: Applicative

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Applicative"

## Summary

Add `Applicative[A_co]`, the type class that unites `Pointed` and `Apply` — per CLAUDE.md's Design section: "there will be an Applicative class that inherits from both." Adds no new abstract methods of its own. Implement it for `Identity[A]` (retrofit) and `Reader[R, A]` (which also needs a new `Apply` instance first — it only has `Functor`/`Pointed` so far). `Const[A, B]`'s instance stays deferred — it needs both `Pointed` and `Apply` first, and both are already blocked on `Semigroup`/`Monoid` (documented in `docs/specs/pointed.md` and `docs/specs/apply.md`).

`liftA2` and other derived combinators are explicitly out of scope for this spec — see Out of scope.

## Motivation

`Pointed` (construct from a value) and `Apply` (apply a wrapped function) are useful independently, but together they let you lift an ordinary multi-argument function into wrapped values entirely — `f(a, b)` becomes `point(f).ap(point(a))`-shaped composition without ever leaving the wrapped world. `Applicative` is the name for "has both," and its four laws (identity, homomorphism, interchange, composition) are what guarantee `point` and `ap` actually cohere with each other and with `fmap`, not just separately with themselves.

## Design

### Shape

```python
class Applicative(Pointed[A_co], Apply[A_co], Generic[A_co]):
    pass
```

No new abstract methods — this is a pure composition, matching CLAUDE.md's own description of it as "a convenience class." Verified against `mypy --strict` and at runtime: `Applicative`'s own MRO resolves cleanly (`Pointed` and `Apply` are siblings — `Apply` reaches `Functor`/`Functional`, `Pointed` reaches `Functional` directly — same diamond shape `Identity` already proved works for `Functor`+`Pointed` back in `docs/specs/pointed.md`).

### Concrete types: drop the now-redundant explicit bases

```python
class Identity(Applicative[A], Generic[A]):
    ...
```

**Repeats a lesson learned twice already** (`Functional`-via-`Functor` in `docs/specs/pointed.md`, `Functor`-via-`Apply` in `docs/specs/apply.md`'s T-014): once a concrete type inherits `Applicative[A]`, it must **not** also separately list `Pointed[A]`/`Apply[A]`/`Functor[A]` — `Applicative` already brings all three transitively, and re-listing any of them produces a contradictory MRO (`TypeError: Cannot create a consistent method resolution order`). Verified directly: `Identity(Applicative[A], Generic[A])` resolves to `[Identity, Applicative, Pointed, Apply, Functor, Functional, Generic, object]` and `isinstance(identity_instance, Applicative)` is `True`. `Identity` needs no new methods — `point`, `ap`, and `fmap` are already fully implemented from the `Pointed`/`Apply`/`Functor` rounds; this ticket is purely a base-class change.

### Reader needs `Apply` first

Reader only has `Functor`/`Pointed` so far. Its `ap` threads the **same** environment value into both the wrapped function and the wrapped value — verified directly (not just by type, by actual behavior): given `add_r: Reader[int, int]` (`run=lambda r: r`) and `multiply_by_r: Reader[int, Callable[[int, int]]]` (`run=lambda r: (lambda x: x * r)`), `add_r.ap(multiply_by_r).run(3) == 9` and `.run(4) == 16` — confirming both sides receive the identical `r`, not independently-supplied ones.

```python
def ap(self, f: "Reader[R, Callable[[A], B]]") -> "Reader[R, B]":  # type: ignore[override]
    return Reader(run=lambda r: f.run(r)(self.run(r)))
```

Same `# type: ignore[override]` situation as `Identity.ap` and `Apply.ap` itself — parameter narrowing only, verified via the same mechanism already established in `docs/specs/apply.md`.

Once `Reader` has `Apply`, its `Applicative` instance is the same "drop the redundant explicit bases" change as `Identity`'s: `class Reader(Applicative[A], Generic[R, A])`, no new methods.

## Concrete instances in scope

- **`Identity[A]`** — retrofit to `Applicative[A]`, base-class change only, no new methods.
- **`Reader[R, A]`** — new `Apply[R, A]` instance (environment-threading `ap`), then retrofit to `Applicative[A]`, base-class change only.

`Const[A, B]`'s instance is deferred — see Motivation and Out of scope.

## Testing strategy

New `tests/applicative_laws.py`, mirroring `functor_laws.py`/`apply_laws.py`'s shape: `assert_applicative_law(point, values, equal=None)`. Unlike `assert_functor_laws`/`assert_apply_law`, this takes `point` (the concrete type's own classmethod, e.g. `Identity.point`) instead of a separate `make` — verified all four laws can be expressed purely in terms of `point` (plus `.fmap`/`.ap`, already methods on the values `point` produces), so no second parameter is needed:

- **Identity law:** `v.ap(point(id)) == v`
- **Homomorphism:** `point(value).ap(point(f)) == point(f(value))`
- **Interchange:** `point(value).ap(u) == u.ap(point(lambda fn: fn(value)))`, where `u = point(f)`
- **Composition:** `w.ap(v.ap(u.fmap(compose))) == w.ap(v).ap(u)`, where `w, v, u = point(value), point(f), point(g)`

Verified all four hold for a correct implementation, and that homomorphism (the simplest genuinely new one — not already exercisable by `Functor`'s or `Apply`'s existing law tests) catches a deliberately broken `ap`. The composition law here is structurally the same formula as `Apply`'s existing associativity law (`docs/specs/apply.md`) — worth testing anyway since it exercises `point`+`ap`+`fmap` together rather than assuming pre-built `Apply` values, but it's not expected to catch anything the `Apply` law test wouldn't already catch on its own; noted as a known overlap, not a gap.

`Identity`'s and `Reader`'s law tests both call this helper — `Reader`'s with the same environment-sampling `equal` comparator already established in `docs/specs/reader.md`.

100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Applicative` section (concept, all four laws in plain language, a runnable example), replacing the current stub.
- `docs/HOWTO.md`'s `Identity` and `Reader` sections get short additions noting they're now `Applicative`.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `liftA2` and other derived combinators — deliberately excluded from this round (confirmed in review); `Applicative` stays a pure `Pointed`+`Apply` composition with zero new methods, matching CLAUDE.md's own description. Could get its own spec later.
- `Const[A, B]`'s `Applicative` instance — blocked on `Pointed`/`Apply` for `Const`, both blocked on `Semigroup`/`Monoid`. No change from the existing deferral.
- `Bind`, `Monad` — later specs.

## Open questions / risks

- None new — this spec mostly assembles pieces already built and verified (`Pointed`, `Apply`, the MRO-narrowing pattern, `Reader`'s extensional equality). The one genuinely new piece is `Reader.ap`'s environment-threading, verified directly above.
