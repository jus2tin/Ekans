# Spec: Const's conditional Applicative-shaped operations

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Const Applicative"

## Summary

Give `Const[A, B]` the two operations `Applicative` needs — a `point`-equivalent and an `ap`-equivalent — conditionally on `A`, the same way `Const` already gets `Semigroup`/`Monoid` support conditionally (`docs/specs/semigroup.md`, `docs/specs/monoid.md`) rather than nominally. `Const` never becomes an actual `isinstance(x, Applicative)` — this is impossible, not merely undesirable, verified directly in Phase 1 below — but it satisfies the free-function/classmethod shape of both operations whenever `A` carries the right structure.

## Motivation

`docs/specs/monad.md`'s Out of scope section flagged this explicitly as deferred, unstarted follow-up work: "`Const`'s deferred `Pointed`/`Applicative` instance — a separate, still-unstarted follow-up, unrelated to this round." This spec is that follow-up.

## Design

### Why nominal `Pointed[B]`/`Apply[B]`/`Applicative[B]` is impossible for `Const`, not just undesirable

Verified directly with a throwaway `mypy --strict` probe before writing anything else:

- **`ap` needs `A: Semigroup`.** `Const[A, B]`'s `ap` must combine `self`'s held `A` with `f`'s held `A` (both sides hold an `A`; `B` is phantom on both) — the only sensible operation is `self.value.mappend(f.value)`. Attempting this inside a naive nominal `Apply[B]` implementation, with `A` left as `Apply`'s ordinary unconstrained `TypeVar`, produces a genuine error: `"A" has no attribute "mappend"  [attr-defined]`. `A` would need a `Semigroup` bound to make this well-typed — but `Apply`'s own class-level `TypeVar` for `Const`'s declared base has no way to carry that bound only when `A` happens to satisfy it; nominal inheritance is unconditional by construction.
- **`point` needs `A: Monoid`, and there's nowhere to put it.** `Pointed.point`'s fixed shape is `point(cls, value: A_co) -> Pointed[A_co]` — for `Const`, `A_co` corresponds to `B` (the type `Functor` maps over), so a nominal override would be `point(cls, value: B) -> Const[A, B]`. But producing a real `Const[A, B]` requires an actual `A` value from somewhere, and this signature has no way to say *which* `Monoid` to use for `A` — confirmed directly: the naive attempt produces `Argument "value" to "ConstPointedAttempt" has incompatible type "B"; expected "A"  [arg-type]`. There is no fix available within `Pointed.point`'s fixed signature; the information needed genuinely isn't there.

This is the exact same class of wall `Identity`/`Const`/`Reader`'s conditional `Semigroup`/`Monoid` support already hit and solved with free functions / classmethods carrying an explicit `Type[S]` — Python generics are erased at runtime, so nothing can be inferred from context alone; it has to be passed in.

### `Const.point`: a classmethod, mirroring `Const.mempty` exactly

```python
S = TypeVar("S", bound=Monoid)
B = TypeVar("B")

@classmethod
def point(cls, value_type: Type[S], value: B) -> "Const[S, B]":
    return Const(value=value_type.mempty())
```

Verified against `mypy --strict`: `Const.point(_MonoidBox, "ignored")` reveals precisely `Const[_MonoidBox, str]`, not a loose or `Any`-decayed type.

Per review: kept as a classmethod directly on `Const` (not a free function) — matching `Pointed`'s own established project-wide rule of no free-function form for `point` (`docs/specs/pointed.md`), and matching `Const.mempty`'s exact reasoning: a fresh, classmethod-scoped `TypeVar` doesn't contaminate every `Const[A, B]` instance the way a nominal method would.

**`value: B` is accepted and unconditionally discarded.** Under the hood this makes `Const.point(S, value)` behave identically to `Const.mempty(S)` for any `value` — there is no way to make an argument that's structurally unreachable (see `Const.fmap`'s `f` parameter) do anything else. Per review, kept anyway: it preserves the conventional `Pointed.point(value_type_context, value) -> F[value_type]` shape a reader would expect to find, the same way `Const.fmap` keeps a real `f: Callable[[B], C]` parameter it never calls, rather than silently dropping the parameter and becoming a different-shaped, harder-to-recognize operation. This is a deliberate, acknowledged redundancy with `Const.mempty`, not an oversight — recorded plainly rather than glossed over.

### `Const`'s `ap`: a new `@overload` on the existing free `ap` function, `Semigroup`-bound

```python
S = TypeVar("S", bound=Semigroup)

@overload
def ap(f: "Const[S, Callable[[A], B]]", x: "Const[S, A]") -> "Const[S, B]": ...
```
added to `apply.py`'s existing `ap` function (alongside its `Identity`/`Reader`/loose-`Apply[A]`-fallback overloads), with the dispatch body:
```python
if isinstance(f, Const) and isinstance(x, Const):
    return Const(value=x.value.mappend(f.value))
```

Verified against `mypy --strict`: `ap(const_f, const_x)` with `A: _SemiBox` (a `Semigroup`) reveals precisely `Const[_SemiBox, B]`; the same call with `A: int` (not a `Semigroup`) is a genuine error, `Value of type variable "S" of "ap" cannot be "int"  [type-var]` — the constraint is real, not just documentation.

Per review: added as a new overload on the *existing shared* `ap` function rather than a separately-named function — mirrors `Const`'s existing `mappend` overload, which already lives on the one shared `Semigroup.mappend` free function rather than a `const_mappend` of its own.

No corresponding method — `Const` doesn't nominally implement `Apply[B]` (see above), so there's no `.ap()` method to delegate to; the free function is the only interface, matching the API-shape convention already established in `CLAUDE.md` for constrained/conditional instances (`Identity`'s `Semigroup` support is the precedent cited there directly).

### `liftA2`: a new `@overload`, same bound, falls out directly

```python
@overload
def liftA2(
    f: Callable[[A, B], C], fa: "Const[S, A]", fb: "Const[S, B]"
) -> "Const[S, C]": ...
```
added to `applicative.py`'s existing `liftA2`, dispatching to `Const(value=fa.value.mappend(fb.value))` — the same `Semigroup`-bound combination `ap` uses, since `liftA2(f, fa, fb) = fb.ap(fa.fmap(...))` in the general case, and `Const.fmap` never touches the held value at all. Verified against `mypy --strict`: precise `Const[_SemiBox, C]` result, no precision loss.

Per review: included in this same round rather than deferred — the underlying constraint (`A: Semigroup`) and implementation shape are identical to `ap`'s, so building one without the other would leave a known, easily-anticipated gap for a future round to rediscover from scratch.

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: any existing type class sharing a concrete instance with this round's operations (`Const`'s existing `Functor`, `Extractable`, and conditional `Semigroup`/`Monoid`).

- **`point`-equivalent × `Extractable`: the standard round-trip law does *not* hold, by design.** `Identity`'s `Pointed`/`Extractable` law is `extract(point(a)) == a`. For `Const`, `Const.point(S, value).extract()` returns `S.mempty()`, never `value` — `value` is discarded unconditionally. This is not a gap to close; it's the direct, necessary consequence of `Const.point` existing at all (there is no `A` to extract `value` back out of, `value` was never an `A`). Recorded explicitly per the Proof Burden rather than silently omitted from the law-testing scope: no property test asserts `extract(point(a)) == a` for `Const`, and the reason is structural, matching `Const.fmap`'s own precedent of a parameter that's accepted but provably never used.
- **`ap`-equivalent × `Extractable`: a real, different law holds, and is worth testing.** `Identity`'s `Apply`/`Extractable` law is a function-application homomorphism: `x.ap(f).extract() == f.extract()(x.extract())`. `Const`'s `ap` never applies a function at all (same reason `Const` has no `Bind` — there's no `B` value to apply anything to); the actual, meaningful law is a `mappend` homomorphism instead: `extract(ap(f, x)) == x.extract().mappend(f.extract())` — directly true by `ap`'s own construction, and worth a property test the same way `mappend`'s own extract-homomorphism is already tested (`test_mappend_extract_homomorphism` in `tests/test_const.py`).
- **`ap`/`point`-equivalents × `Semigroup`/`Monoid`**: not a new pair — both operations exist entirely *because of* the already-established conditional `Semigroup`/`Monoid` support; no additional law beyond what those rounds already cover.
- **`ap`-equivalent × `point`-equivalent (the `Applicative` identity/homomorphism/interchange laws)**: not tested. These laws are stated over a genuine `Applicative` instance (`isinstance` included); `Const` is never nominally `Applicative`; see the Design section's Proof Burden above for why that's impossible, not deferred. Testing the *free-function* versions of these laws against `Const` specifically would be testing a different, `Const`-specific claim than what `assert_applicative_law` (built for real `Applicative` instances) checks — out of scope for this round; flagged under Open questions below as worth a second look if a future round wants it.

## Concrete instances in scope

- `Const[A, B]` only. No other type is affected.

## Testing strategy

- `tests/test_const.py`: example-based tests for `Const.point` (construction, the discarded-argument behavior stated as a real assertion, not just implied), the new `ap` overload (construction, precision, and the genuine `[type-var]` rejection for a non-`Semigroup` `A` — mirroring `test_mappend_rejects_mismatched_container_types_at_runtime`'s style for a compile-time-only check), and `liftA2`.
- The `extract(ap(f, x)) == x.extract().mappend(f.extract())` law from the Cross-Product audit above, as a direct property test (Hypothesis-driven, mirroring `test_mappend_extract_homomorphism`'s shape).
- No `assert_applicative_law`/`assert_apply_law` usage against `Const` — those helpers are built for real `Applicative`/`Apply` instances (`isinstance`-based), which `Const` structurally isn't; see Cross-Product audit above.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression against the full existing suite.

## Documentation requirements

- `docs/HOWTO.md`'s existing `Const` section: a short addition explaining `Const.point`/the `ap`/`liftA2` overloads, written with the same plain-limitation honesty as the `Semigroup`/`Monoid` conditional-instance framing already there — `Const` still never "is" an `Applicative`, and the doc should say so directly rather than let a reader infer it.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- Nominal `Pointed[B]`/`Apply[B]`/`Applicative[B]` inheritance for `Const` — proven impossible in the Design section above, not merely skipped.
- The `Applicative` identity/homomorphism/interchange laws tested against `Const`'s free-function operations specifically — flagged as a possible future round in Open questions, not included here.
- Any change to `Identity`/`Reader`'s existing, already-nominal `Applicative` instances.

## Open questions / risks

- Whether a `Const`-specific set of `Applicative`-shaped laws (identity/homomorphism/interchange, restated over the free `point`/`ap` functions rather than real methods) is worth writing as its own reusable helper in a future round — not resolved here; the Cross-Product audit's `ap`/`Extractable` law is judged sufficient rigor for this round given `Const`'s `ap` is a thin, directly-verifiable wrapper over `mappend`.
