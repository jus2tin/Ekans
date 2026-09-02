# Spec: Monoid

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Monoid"

## Summary

Add `Monoid(Semigroup)`: an ABC adding `mempty`, the identity element, to `Semigroup`'s associative `mappend`. Also gives `All` a real, nominal `Monoid` instance, and gives `Sum`, `Product`, `Ap`, `Identity`, `Const`, and `Reader` a `mempty`-shaped classmethod that is **not** a `Monoid` override — a hard Python constraint, verified directly, forces this split. See Design below.

## Motivation

`Sum`/`Product`/`All`/`Ap` were built during the Semigroup instances round explicitly anticipating this: their own docs already promise `0`/`1`/`True`/`pure mempty`. `Identity`/`Const`/`Reader`'s conditional `Semigroup` (via the free `mappend` function) has a natural conditional-`Monoid` counterpart once the held/produced type is itself a `Monoid`.

## Design

### The core problem: Python generics are erased at runtime, and `mempty` has no value to work from

Every prior `classmethod` in this project that constructs a value (`Pointed.point`, `Applicative`'s use of it) takes an actual **value** as an argument, from which both mypy and the runtime can recover the concrete type parameter. `mempty` is different: Haskell's `mempty :: a` is nullary — it must conjure a value of type `a` from nothing but the type itself. Python has no runtime representation of "which `A`" a generic class was instantiated with (type erasure), so a truly nullary `Sum.mempty()` classmethod has no way to know, *at runtime*, whether the caller wants `int`'s `0` or `float`'s `0.0`.

**Verified directly, and it's worse than a type error:** a naive `Sum.mempty()` hardcoded to `return Sum(value=0)` lets mypy *confidently and incorrectly* infer `Sum[float]` from an assignment like `y: Sum[float] = Sum.mempty()` (bidirectional type inference solves the classmethod's return-type `TypeVar` from the expected type just fine) — but the **runtime value is silently wrong**: `y.value` is `0` (an `int`), not `0.0`. This is a genuine, silent runtime lie that mypy cannot catch, not a narrow-return-type situation `# type: ignore[override]` could honestly paper over.

### Resolution: `mempty` takes an explicit `Type[X]` argument wherever erasure is a problem

Per review, `mempty` takes the concrete value type explicitly: `Sum.mempty(int)`, not `Sum.mempty()`. This isn't purely nullary the way Haskell's is, but it's honestly correct — verified this type-checks precisely per concrete type and, critically, genuinely **rejects** types that can't supply an identity element, rather than silently constructing a wrong one.

### `Sum[A]`/`Product[M]`: a `SupportsZero`/`SupportsOne` protocol plus a small registry for `int`/`float`

Built-in `int`/`float` have no `.zero()`/`.one()` method of their own — Haskell solves this via `Num`'s `fromInteger`; Python has no equivalent. Per review, `Sum.mempty`/`Product.mempty` combine two mechanisms, verified together against `mypy --strict`:
- A new `SupportsZero`/`SupportsOne` `Protocol` (extending `SupportsAdd`/`SupportsMul` respectively) requiring a real `.zero()`/`.one()` classmethod, for custom types that define one.
- A small hardcoded registry (`int → 0`/`1`, `float → 0.0`/`1.0`) for the two built-ins that don't.

Shape, verified precise and runtime-correct for all three cases (`int`, `float`, a custom `SupportsZero` type) and verified to genuinely reject a type with neither:

```python
@overload
@classmethod
def mempty(cls, value_type: Type[int]) -> "Sum[int]": ...
@overload
@classmethod
def mempty(cls, value_type: Type[float]) -> "Sum[float]": ...
@overload
@classmethod
def mempty(cls, value_type: Type[_ZeroT]) -> "Sum[_ZeroT]": ...
@classmethod
def mempty(cls, value_type: Any) -> Any:
    if value_type is int:
        return Sum(value=0)
    if value_type is float:
        return Sum(value=0.0)
    return Sum(value=value_type.zero())
```

`SupportsZero` must itself extend `SupportsAdd` (verified required — without it, mypy rejects the third overload's return type as incompatible with `Sum`'s own `A: SupportsAdd` bound).

### `Sum`/`Product`/`Ap` cannot nominally inherit `Monoid`

Verified directly: overriding `Monoid.mempty(cls) -> Self` with a version requiring an additional mandatory `value_type` parameter is a genuine `mypy --strict` `[override]` error — "Signature of mempty incompatible with supertype" — not a cosmetic one. Adding a required parameter genuinely breaks substitutability: code written generically against `Monoid` and calling `.mempty()` would crash on `Sum`. So `Sum`, `Product`, and `Ap` do **not** nominally inherit `Monoid`, even though they already nominally inherit `Semigroup` — the same type can be a genuine nominal `Semigroup` (its `mappend` is an ordinary instance method, `self` already carries the concrete type at runtime, no erasure problem) while *not* being a genuine nominal `Monoid` (its `mempty` is a classmethod that must synthesize a value from nothing, which does hit the erasure wall). `isinstance(Sum(value=1), Monoid)` is `False`; `Sum.mempty(int)` still works.

`All` has no generic type parameter at all — no erasure problem, no wall — so it nominally inherits `Monoid` cleanly, the way `Semigroup` already worked for it.

### `mempty` lives as a classmethod on each type directly, not a free function — even for `Identity`/`Const`/`Reader`

Per review, this deliberately departs from `CLAUDE.md`'s free-function-primary API-shape rule, for a specific, verified reason: a free function would need *two* independent type parameters (which container, and which value type) with nothing to infer either from — unlike `mappend(a, b)`, which infers everything from the runtime/static types of `a`/`b` themselves. A classmethod scopes "which container" naturally through the class it's called on (`Sum.mempty(int)`, `Identity.mempty(Box)`), exactly as ergonomic as each type's existing `.mappend()`/`.point()`.

**Verified this also resolves `Identity`/`Const`/`Reader`'s conditional case cleanly, without needing a free function at all** — a real correction to the initial framing that assumed it would. The reason `mappend` had to be free-function-only for these three doesn't apply to `mempty`: `mappend` is an *instance* method, so if `Identity` had a nominal `.mappend()`, it would show up on `Identity[str]` too (compiling fine, crashing at runtime, since `str` isn't a `Semigroup`) — that's what forced the free-function-only design there. `mempty` is a *classmethod* with its own fresh, independently-bound `TypeVar` (`S: Monoid`), completely unrelated to the class's own type parameter `A` — the exact same shape `Identity.point`'s classmethod already uses successfully. Verified directly: `Identity.mempty(Box)` (where `Box: Monoid`) resolves to `Identity[Box]` precisely, and `Identity.mempty(str)` is genuinely rejected (`Value of type variable "S" of "mempty" of "Identity" cannot be "str"`) — same for `Const[S, B]` (`B` freely inferred from context, unrelated to `S`) and `Reader[R, S]` (pointwise: `Reader(run=lambda r: value_type.mempty())`, ignoring the environment, `R` freely inferred).

None of `Identity`/`Const`/`Reader` nominally inherit `Monoid` either (same reasoning as `Sum`/`Product`/`Ap` — and the same reasoning `Semigroup` already established for them).

### Monoid's law: left and right identity

```
mappend(mempty(), x) == x
mappend(x, mempty()) == x
```

Verified directly: holds for a correct instance (integer addition, `mempty = 0`), and genuinely caught by a deliberately broken one (wrong identity element, `mempty = 1` instead of `0`).

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: any existing type class sharing at least one concrete instance with `Monoid`'s own instances.

- **Monoid × Semigroup**: not a separate audit item — `Monoid` *is* a `Semigroup` (inherits it directly), and the identity laws above are exactly this pairing's law. No additional test needed beyond the identity laws themselves.
- **Monoid × Extractable**: `All` is both (nominally). Law: `mempty().extract()` equals the identity of the underlying operation `mappend` delegates to — `All.mempty().extract() == True`, the identity for AND. Tested directly. `Sum`/`Product`/`Ap` aren't nominally `Monoid`, but their `mempty(Type[X])` classmethods are still `Extractable`, so the analogous (non-nominal) check is tested too: `Sum.mempty(int).extract() == 0`, `Product.mempty(int).extract() == 1`, `Ap.mempty(Box).extract() == Box.mempty()`.
- **Monoid × Pointed**: no concrete type is nominally both (`Identity`/`Reader` are `Pointed` but not nominally `Monoid`; `All` is `Monoid` but not `Pointed`). No shared instance, no law to test — documented here rather than silently skipped, per the Proof Burden.
- **Monoid × Functor / Apply / Applicative**: same as above — `All` (the only nominal `Monoid`) implements none of these. No shared instance.

## Concrete instances in scope

- `Monoid(Semigroup)` — new ABC.
- `All` — nominal `Monoid` instance.
- `Sum[A]`, `Product[M]`, `Ap[S]`, `Identity[A]`, `Const[A, B]`, `Reader[R, A]` — each gets a `mempty` classmethod per the Design section above, none nominally inheriting `Monoid`.

## Testing strategy

- `tests/test_monoid.py`: ABC-level tests (cannot instantiate directly, `Semigroup` in the MRO, abstract `mempty` raises if not overridden) via a local illustrative type — same shape as `test_semigroup.py`.
- `tests/monoid_laws.py`: `assert_monoid_law(make, mempty, values, equal=None)` — left/right identity, extending `assert_semigroup_law`'s pattern.
- Each concrete type gets `mempty`-specific tests (constructs the right value, satisfies the identity laws) plus a `reveal_type` precision probe (deleted after use).
- Cross-Product audit tests per the section above (`All.mempty().extract()`, `Sum.mempty(int).extract()`, etc.).
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression (full suite, not just new tests) per ticket.

## Documentation requirements

- `docs/HOWTO.md`: new `Monoid` section (concept, the identity laws, a runnable example, and the erasure-wall story — this is a genuinely interesting, honest limitation worth explaining, not hiding).
- Short `mempty` additions to `Sum`/`Product`/`All`/`Ap`/`Identity`/`Const`/`Reader`'s existing sections.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Const`'s `Pointed`/`Applicative` instance (`pure _ = Const mempty`) — its own follow-up round, per Phase 0.
- Any Monoid instance beyond `Sum`/`Product`/`All`/`Ap`/`Identity`/`Const`/`Reader`.
- A generic `SupportsZero`/`SupportsOne`-satisfying wrapper for `int`/`float` themselves (e.g. making `int` satisfy `SupportsZero` structurally) — the registry inside `mempty` is the chosen fix; no changes to how `int`/`float` are used elsewhere.

## Open questions / risks

- None outstanding — every design decision here (the erasure wall, the `Type[X]`-argument fix, the `SupportsZero`/`SupportsOne` + registry combination, the non-nominal-inheritance requirement for `Sum`/`Product`/`Ap`, the classmethod-not-free-function shape working for `Identity`/`Const`/`Reader` too) was verified directly against `mypy --strict` and at runtime before being written down.
