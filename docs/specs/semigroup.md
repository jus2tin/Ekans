# Spec: Semigroup

**Status:** Draft — awaiting review
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Semigroup"

## Summary

Add `Semigroup`, the first entry in the "Algebraic structures" branch of the type hierarchy: an ABC for types with an associative combining operation, `mappend`. Architecturally different from everything built so far — it isn't a container type class (nothing gets wrapped; a `Semigroup` combines two values of *its own* type into a third). Also add free-function `mappend` support for `Identity[A]`, `Const[A, B]`, and `Reader[R, A]`, each conditional on their held/wrapped type itself being a `Semigroup`.

## Motivation

Everything under "Endofunctor based structures" describes a container's behavior. `Semigroup` is the first "algebraic" type class — a property of plain values, independent of any container. It's also the direct prerequisite for `Monoid` (adds an identity element), which is in turn what's still blocking `Const`'s `Pointed`/`Apply`/`Applicative` instances (both need `A: Monoid` for `Const`'s held type — see `docs/specs/pointed.md` and `docs/specs/apply.md`). This spec doesn't unblock those yet — `Monoid` still needs to exist first — but it's the first real step toward it.

## Design

### Shape: `typing.Self`, not the established narrowing pattern

```python
from abc import abstractmethod
from typing import Self

class Semigroup(Functional):
    @abstractmethod
    def mappend(self, other: Self) -> Self:
        raise NotImplementedError
```

Every other type class here has hit "the abstract method's return type is loose, the concrete override needs narrowing plus `# type: ignore[override]`" repeatedly (`Pointed.point`, `Apply.ap`, `Applicative.ap`). `Semigroup.mappend` always returns exactly `self`'s own type — precisely what `typing.Self` (PEP 673, available since our Python 3.11 floor) is for. Verified directly: a concrete `Box(Semigroup)` overriding `mappend` needs **no override narrowing and no `type: ignore` at all** — `reveal_type` on `Box(...).mappend(...)` correctly gives `Box`, and on a further subclass `SubBox(Box)` correctly gives `SubBox`, both without either class re-declaring anything beyond the method body. This is a first for this project; every prior ABC needed at least one ignore somewhere in its concrete overrides.

No new immutability concerns — inherits `Functional` directly (not through another type class), matching the Type hierarchy's existing "Algebraic structures" placement.

### Method name: `mappend`, not `combine`

Haskell's own operation is the operator `<>`, with `mappend` as its ASCII/historical name (from before `Semigroup` was split out of `Monoid`) — matches this project's established lean toward Haskell-faithful naming (`fmap` over `map`, `ap`, `point`) over what reads more natural in isolation.

### Free function: `mappend(a, b)`, one `@overload` per container type — but no fallback

```python
@overload
def mappend(a: "Identity[S]", b: "Identity[S]") -> "Identity[S]": ...
@overload
def mappend(a: "Const[S, A]", b: "Const[S, A]") -> "Const[S, A]": ...
@overload
def mappend(a: "Reader[R, S]", b: "Reader[R, S]") -> "Reader[R, S]": ...
def mappend(a, b):
    ...
```

where `S = TypeVar("S", bound=Semigroup)`. Same overload-per-type growth pattern as `fmap`/`ap`, with one structural difference: there's no `Functor[A]`-style loose fallback, because there's no generic "any Semigroup-wrapping container" ABC to fall back to — each container's `mappend` support is its own overload, full stop.

### The constrained-instance problem: free functions bounded by `S: Semigroup`, no nominal inheritance

`Identity[A]`'s natural instance only makes sense when `A` itself is a `Semigroup` (`Identity x` `mappend` `Identity y = Identity (x` `mappend` `y)`) — Haskell expresses this with a constrained instance (`instance Semigroup a => Semigroup (Identity a)`); Python has no equivalent for a *class-level* constraint. Resolved by **not** making `Identity`/`Const`/`Reader` nominally inherit `Semigroup` at all — the constraint lives entirely in the free function's bound TypeVar instead. Verified this gives genuine, not just documented, type safety:

```python
x: Identity[Box] = Identity(value=Box(value=1))  # Box is Semigroup
y: Identity[Box] = Identity(value=Box(value=2))
mappend(x, y)  # OK, reveals Identity[Box]

bad1: Identity[str] = Identity(value="a")  # str is NOT our Semigroup
bad2: Identity[str] = Identity(value="b")
mappend(bad1, bad2)
# error: Value of type variable "S" of "mappend" cannot be "str"  [type-var]
```

`Identity`/`Const`/`Reader`'s own class definitions don't change at all for this — no new bases, no MRO to worry about, since they never claim to implement `Semigroup`. The rejected-nominal-inheritance alternative (unconditionally inherit `Semigroup`, check at runtime, fail with `AttributeError` if the held type doesn't support it) was considered and rejected: it would let `Identity[str].mappend(...)` type-check fine and then crash — exactly the class of bug this project's whole approach to typing exists to prevent.

### `Const`'s and `Reader`'s instances

- `Const[A, B]`: `Const x mappend Const y = Const (x mappend y)`, ignoring `B` entirely, conditional on `A: Semigroup` — same shape as `Const`'s existing `Functor` instance (operates on the held value, ignores the phantom parameter).
- `Reader[R, A]`: pointwise — `(f mappend g)(r) = f(r) mappend g(r)`, conditional on `A: Semigroup`. Verified the shape type-checks correctly (see combined probe in Testing strategy) alongside `Identity`'s and `Const`'s overloads in the same `@overload` set.

### Worth stating plainly: nothing Ekans ships is unconditionally a Semigroup yet

Because every instance this round is conditional (`Identity`/`Const`/`Reader`, each depending on their held type), and no concrete type currently in Ekans (`Identity`, `Proxy`, `Const`, `Star`, `Reader`) has a natural *unconditional* `Semigroup` instance, every example and test for this round necessarily uses a small local illustrative type (the same `Box`-in-`docs/HOWTO.md` pattern already established for `Functor`) — except here it isn't a temporary stand-in waiting for a real type to catch up, it's just what demonstrating a constrained instance requires. A genuinely useful shipped `Semigroup` instance (a numeric wrapper, `First`/`Last`, etc.) is natural follow-up work, not part of this spec.

## Concrete instances in scope

- `Identity[A]`, `Const[A, B]`, `Reader[R, A]` — all as free-function `mappend` overloads only, per Design above. None of the three's own class definitions change.

## Testing strategy

- New `tests/semigroup_laws.py`: `assert_semigroup_law(make, values, equal=None)` — the single associativity law, `x.mappend(y).mappend(z) == x.mappend(y.mappend(z))`. Verified this type-checks cleanly with **no friction at all** — unlike `apply_laws.py`/`applicative_laws.py`, `make` here is used for exactly one purpose (constructing the type under test from a raw value), so none of the "`make` also needs to wrap functions" workaround from those helpers applies. Verified the law holds for a correct implementation (integer addition) and is caught for a deliberately broken one (integer subtraction — non-associative).
- Local illustrative `Box`-style type for both the ABC's own tests and the `Identity`/`Const`/`Reader` free-function tests, per the note above.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Semigroup` section (concept, the associativity law, a runnable example with a local illustrative type, and why it's a permanent stand-in rather than a temporary one this time), replacing the current stub.
- Short additions to `Identity`'s, `Const`'s, and `Reader`'s existing sections noting their conditional `mappend` support.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Monoid` — its own spec, once `Semigroup` lands.
- Any unconditionally-Semigroup concrete type (numeric wrapper, `First`/`Last`, etc.) — natural follow-up, not required to prove this spec's mechanism.
- Re-examining `Const`'s `Pointed`/`Apply`/`Applicative` deferral — still blocked on `Monoid` specifically, not `Semigroup` alone.
- `__add__`/operator sugar for `mappend` — rejected in review; `mappend` is a plain method plus free function, matching this project's general operator-sugar stance.

## Open questions / risks

- None outstanding — every design decision here was verified directly against `mypy --strict` and at runtime before being written down, including the negative case (a non-Semigroup value type genuinely gets rejected, not just assumed to be rejected).
