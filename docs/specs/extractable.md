# Spec: Extractable

**Status:** Draft — awaiting review
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Extractable"

## Summary

Add `Extractable`, the first type class in a new "Comonad-based structures" branch of the type hierarchy: an ABC for containers that can hand back the single value they hold, via `extract`. It's the dual of `Pointed` — where `point: A -> F[A]` builds a container from a value, `extract: W[A] -> A` pulls the value back out — and, like `Pointed`, needs only `Functional` to make sense on its own. This round also retrofits `Identity`, `Sum`, `Product`, `All`, `Const`, and `Ap` to implement it.

## Motivation

Several concrete types in Ekans hold exactly one value and, until now, exposed it only via direct field access (`.value`) with no uniform way to reach it generically. The prompting use case: `sum = lambda foldable: foldMap(Sum, foldable).extract()` — once `Foldable`/`foldMap` exist (a separate, later round), code like this needs a type-agnostic way to pull the combined `Sum`/`Product`/etc. back down to a plain value. `Extractable` is also, explicitly, the first deliberate step toward a future `Comonad` — mirroring how this project built `Monad` up from `Pointed`/`Functor`/`Apply`/`Bind` in small, separately-shipped pieces rather than one large type class. `Extractable` is that same move applied to `Comonad`'s dual half.

## Design

### Shape: ABC, generic, instance method — no override boilerplate needed

```python
from abc import abstractmethod
from typing import Generic, TypeVar

from ekans.functional import Functional

A_co = TypeVar("A_co", covariant=True)


class Extractable(Functional, Generic[A_co]):
    @abstractmethod
    def extract(self) -> A_co:
        raise NotImplementedError
```

ABC, not `Protocol` — per review, a structural `Protocol` for a bare `extract`/`get`-style method risks accidental collisions with unrelated methods on unrelated types (the concern was raised directly against naming it `get`, since `dict.get`, `Queue.get`, etc. would satisfy it by accident; `extract` itself is less collision-prone, but the ABC choice was made independent of the final name and matches the project's stated default anyway). Verified against `mypy --strict`: unlike `Pointed.point` or `Apply.ap`, `extract` needs **no override narrowing and no `type: ignore` at all** in any concrete subclass — `reveal_type` confirms precise per-type returns (`int`, `str`, `Box`, ...) with zero friction, matching the same reasoning `Semigroup.mappend` benefited from via `typing.Self`, except here it's simpler still: `extract` only narrows a *return* type via a covariant class-scoped `TypeVar`, which instance methods already handle cleanly (per this project's established Phase 1 finding: parameter narrowing needs overrides, return-type-only narrowing doesn't).

### Placement: needs only `Functional`, mirroring `Pointed` exactly

Confirmed by review: `extract`, like `point`, doesn't need `fmap` to make sense as an operation — it's a fact about a container's *shape* (does it hold exactly one value it can hand back?), independent of whether that container is mappable. `Extractable` therefore sits in the type hierarchy as a sibling to `Pointed`, both hanging directly off `Functional`, under a new "Comonad-based structures" branch parallel to "Endofunctor based structures" (which holds `Pointed`/`Functor`/`Apply`/`Bind`/etc.) — see the updated `CLAUDE.md` Type hierarchy.

### Multiple inheritance verified clean

Verified directly: a concrete type inheriting both an Endofunctor-branch class (e.g. `Applicative[A]`) and `Extractable[A]` composes with no MRO conflict — the two branches share no common ancestor besides `Functional` itself, so there's nothing redundant to trip over (unlike the `Apply`-already-inherits-`Functor` situation seen in earlier rounds). Also verified `Const[A, B]`'s two-type-parameter case specifically: `Const(Functor[B], Extractable[A], Generic[A, B])` type-checks cleanly, with `extract` correctly returning the held type `A`, not the phantom `B`.

### `Ap[S].extract()` fully unwraps to `S`, not `Identity[S]`

`Ap[S]`'s immediate held field is `Identity[S]`, but `Extractable`'s whole point is handing back *the* value a container conceptually holds — and `Identity` wrapping `S` inside `Ap` is an implementation detail forced by Python's lack of higher-kinded types (see `docs/specs/semigroup-instances.md`'s `Ap` section), not something a caller of `extract` should have to peel back themselves. `Ap[S].extract()` is therefore implemented as `self.value.extract()`, delegating to `Identity`'s own `Extractable` instance and returning `S` directly. Verified via `reveal_type`: precise, no loss of precision through the delegation.

## Concrete instances in scope

- `Identity[A]`, `Sum[A]`, `Product[M]`, `All`, `Const[A, B]`, `Ap[S]` — each gets `extract` returning its single held value (fully unwrapped, per the `Ap` note above). `Reader`/`Star` are excluded (they wrap functions, not a single value — there's no environment to run against to produce "the" value). `Proxy` is excluded (it holds no runtime value at all — nothing to extract).

## Testing strategy

- `tests/test_extractable.py`: ABC-level tests (cannot instantiate directly, `Functional` in the MRO, abstract `extract` raises if not overridden via a local illustrative type) — same shape as `test_semigroup.py`.
- Each of the six concrete types gets an `extract`-specific test (or a short addition to its existing test file) confirming `extract()` returns the expected held value, plus a `reveal_type`-verified precision probe per type (deleted after use).
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Extractable` section (concept, the `Pointed`-duality framing, a runnable example), replacing the current absence (there's no existing stub for this, since it wasn't part of the originally planned hierarchy until this round).
- Short `extract` additions to each of the six concrete types' existing `docs/HOWTO.md` sections.
- `CLAUDE.md`'s Type hierarchy gets the new "Comonad-based structures" branch (already drafted above, to land in the same commit as spec approval, matching the project's existing precedent for durable rule/hierarchy changes).

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.
- No `Foldable`/`foldMap` work in this round — deferred to its own future Implementation Protocol round, per Phase 0.
- No `Extend`/`Comonad` implementation in this round — `Extractable` alone, matching the project's small-steps pattern; `Extend`/`Comonad` are recorded as stubs in `CLAUDE.md`'s Type hierarchy for shape only.

## Out of scope

- `Extend` (`extend`/`duplicate`) and `Comonad` itself — future rounds.
- `Foldable`/`foldMap` — future round; the motivating `sum = lambda foldable: foldMap(Sum, foldable).extract()` example won't actually run until that round lands, but `Extractable` alone is independently useful and testable now.
- Retrofitting `Reader`, `Star`, or `Proxy` — excluded on the merits (no single value to extract), not deferred.

## Open questions / risks

- None outstanding — every design decision here (ABC shape, no-override-needed claim, MRO composition, `Const`'s two-type-parameter case, `Ap`'s full-unwrap behavior) was verified directly against `mypy --strict` before being written down.
