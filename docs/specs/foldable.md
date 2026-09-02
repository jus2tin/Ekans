# Spec: Foldable

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Foldable"

## Summary

Add `Foldable` — the `typing.Protocol` CLAUDE.md's "Why Foldable is a Protocol" section already designed in prose — plus the full pure-fold slice of Haskell's `Data.Foldable` API as free functions, plus `FoldableABC`, the optional override mechanism for a concrete type to provide a faster `foldr`/`length`/`null` than the generic `__iter__`-driven default. Per explicit direction this round: no cap on the number of convenience functions: the goal is the full pure-fold surface, not a minimal slice.

## Motivation

`Foldable` has been fully designed in prose in `CLAUDE.md` since early in this project but never built or verified against `mypy --strict`. This spec is that build, plus the free-function API surface CLAUDE.md's design always implied but never enumerated.

## Design

### The Protocol: covariant, structural, `__iter__` only

```python
A_co = TypeVar("A_co", covariant=True)

@runtime_checkable
class Foldable(Protocol[A_co]):
    def __iter__(self) -> Iterator[A_co]: ...
```

Verified against `mypy --strict`: an **invariant** `TypeVar` here is a real error (`Invariant type variable "A" used in protocol where covariant one is expected [misc]`) — `A_co` must be declared covariant, the same reasoning `Functor`'s own `A_co` already uses. With that fix, structural satisfaction is confirmed both statically (a function parameter typed `Foldable[A]` accepts `list[int]`, `tuple[int, ...]`, a generator, and a custom dataclass whose only relevant feature is a hand-written `__iter__`, with zero explicit inheritance from any of them) and at runtime (`@runtime_checkable` + `isinstance` checks agree with the static picture, including correctly rejecting a plain `int`).

None of Ekans's own shipped types (`Identity`, `Const`, `Reader`, `Maybe`, `Either`, `Tuple2`, `Sum`, `Product`, `All`, `Ap`) currently satisfy `Foldable` — none of them define `__iter__`. This is expected, not a gap: `Foldable`'s entire design point is structural satisfaction of things that are *already* iterable (Python's own builtins, and any future custom type that has a real reason to be iterable), not something Ekans's single/double-value wrapper types are meant to opt into. Recorded here per the Proof Burden rather than silently assumed.

### A real bug caught in Phase 1: the "trampoline" as originally described doesn't work

`CLAUDE.md`'s existing prose says the fold functions hide a trampoline internally — "bounce a thunk through an explicit loop instead of actually recursing." Implementing that literally (build a chain of nested closures right-to-left, each one deferring to an `acc()` call for "the rest," then invoke the outermost one) was the first thing tried here, and it's wrong: calling the outermost closure still recurses through a real Python stack frame for every element, because each closure's body is a genuine function call to the next one, not a loop-driven state machine. Verified directly: with `sys.setrecursionlimit(200)`, folding a 100,000-element list this way raises a genuine `RecursionError`.

The actual fix has nothing to do with thunk-chaining at all. A right fold with a *strict* combining function (the only kind a plain Python function can be) is inherently right-associated — the outermost `f(x1, ...)` can't produce a value until everything inside it has — so it needs `O(n)` auxiliary state no matter what. The trick is keeping that state off the *Python call stack* specifically, and the simplest way to do that is also the most obvious one in hindsight: a plain accumulator loop over `reversed(list(xs))`, with zero recursion of any kind:

```python
def foldr(f: Callable[[A, B], B], initial: B, xs: Foldable[A]) -> B:
    acc = initial
    for item in reversed(list(xs)):
        acc = f(item, acc)
    return acc
```

Verified directly: this handles the same 100,000-element list cleanly even with the recursion limit still artificially set to `200`. `foldl` needs no such trick at all — a left fold's accumulator loop runs forward over `xs` directly, no `reversed()`/`list()` materialization required, so it's trivially stack-safe (and streaming-friendly) on its own. This correction is recorded here explicitly since it directly contradicts what `CLAUDE.md` previously said the mechanism was — that prose gets corrected in the same commit that lands this ticket.

### `FoldableABC`: override hooks for `foldr` and `length`/`null`

Per review, built this round rather than deferred. Matches the shape CLAUDE.md's design notes already committed to: an optional base a concrete type can inherit from to provide a faster implementation than the generic `__iter__`-driven default, with free functions checking for the override first and falling back otherwise:

```python
class FoldableABC(Generic[A_co]):
    def __iter__(self) -> Iterator[A_co]: ...
    def foldr(self, f: Callable[[A_co, B], B], initial: B) -> B: ...   # NotImplementedError sentinel = "not overridden"
    def length(self) -> int: ...                                       # same
```

Verified directly: a free function checking `isinstance(x, FoldableABC)` and catching the sentinel `NotImplementedError` to fall back to the generic default dispatches correctly to a genuinely different override implementation (not just "the override exists but silently isn't called"), and stays precisely typed throughout.

Scoped to exactly two override points — `foldr` (since nearly everything else in this spec is defined in terms of it, so overriding it cascades improvements everywhere) and `length`/`null` (the specific O(1)-shortcut example CLAUDE.md's own design notes already called out: a type with a stored count shouldn't have to fold to compute one). Not every derived function gets its own override hook — that would be building speculative infrastructure with nothing to verify it against, the same reasoning this project already applies elsewhere (e.g. deferring a generalized cross-class law helper until a second real instance exists). More hooks can be added later if a real type needs them.

### The full function list, and the design decisions behind the non-obvious names

**Core folds** (everything else is built on these):
- `foldr(f, initial, xs)` — right fold, per above.
- `foldl(f, initial, xs)` — left fold, trivially stack-safe.
- `foldMap(monoid_type, f, xs)` — map each element into a `Monoid`, combine via `mappend`/`mempty`.
- `fold(monoid_type, xs)` — `foldMap` with `f` as the identity function (the elements are already the `Monoid`).
- `foldr1(f, xs)` / `foldl1(f, xs)` — fold with no seed, using the first/last element as the seed instead; raises on an empty `Foldable` (matching Haskell, which is partial here too).
- `fold1(xs)` — `Semigroup`-only, seedless `fold`; raises on empty, needs no `Type[M]` argument since it never has to conjure an empty-case value.

**`foldMap`/`fold` need an explicit `Type[M]` argument** — the same erasure reason `Sum.mempty()` already established. Verified directly: on an empty `Foldable`, there's no runtime value of `M` to call `.mempty()` on, and nothing about `f`'s type annotation is introspectable at runtime to recover `M` from; the explicit argument is the only correct fix, not a convenience shortcut skipped.

**Structural/list-shape:** `toList(xs)`, `null(xs)`, `length(xs)`, `concat(xs)` (`Foldable[Iterable[A]] -> List[A]`), `concatMap(f, xs)`.

**Boolean/search:** `and_(xs)`, `or_(xs)` — `and`/`or` are Python keywords, so these can't be spelled that way at all; named `and_`/`or_` per review, matching the stdlib `operator` module's own established convention for the identical problem (`operator.and_`, `operator.or_`), not an invented one. `any(predicate, xs)`, `all(predicate, xs)`, `elem(x, xs)`, `notElem(x, xs)`.

**`sum`/`product`/`all`/`any` keep their exact Haskell/Python names, per review** — unlike `map`→`fmap` (a real, unavoidable collision with no established qualified-import idiom in play), `sum`/`all`/`any` are conventionally imported qualified when there's a name worth protecting, and `Sum`/`Product` already exist as distinct capitalized class names, so the overlap is cosmetic, not functional.

**Numeric/ordering:** `sum(xs)`, `product(xs)` — reuse the existing `SupportsAdd`/`SupportsMul` structural `Protocol`s from `sum.py`/`product.py` directly rather than redefining them, verified importable with no circular-import issue (`foldable.py` is new, so nothing currently imports it back). `maximum(xs)`/`minimum(xs)` need a new `SupportsLt` `Protocol` (self-typed `__lt__`, matching `SupportsAdd`/`SupportsMul`'s own shape) — nothing in this codebase bounded ordering before now. Both raise `ValueError` on an empty `Foldable`, matching Python's own `max()`/`min()` builtins *and* Haskell's own partial `maximum`/`minimum` — the same behavior for two independent, already-established reasons, not a new precedent invented here.

**`maximumBy`/`minimumBy` deliberately diverge from Haskell's literal signature.** Haskell's is `(a -> a -> Ordering) -> t a -> a` (a raw three-way comparator). Ekans's is a `key`-function instead (`Callable[[A], SupportsLt], Foldable[A] -> A`), matching Python's own `max(iterable, key=...)`/`min(iterable, key=...)` idiom directly — a deliberate divergence, recorded here rather than silently reached for the "obviously more Pythonic" option without saying so, per this project's "close to Python's design philosophy where these design choices allow" principle.

**`find(predicate, xs)` returns Ekans's own `Maybe[A]`, not `typing.Optional`.** Haskell's own signature is already `find :: (a -> Bool) -> t a -> Maybe a` — this isn't a stretch to fit Ekans's `Maybe` in, it's using the exact type the Haskell signature already names. Verified directly: `reveal_type` on a `find` call resolves to the precise `Just[A] | Nothing[A]`, and the short-circuit behavior (stopping at the first match, never scanning further) is verified with an explicit test.

### Argument order

Every function above puts the "action" argument first where one exists (`foldr(f, initial, xs)`, `elem(x, xs)`, `any(predicate, xs)`, `maximumBy(key, xs)`) — this already matches Haskell's own argument order for the whole `Data.Foldable` API, so it needed no deliberate divergence to align with this project's existing `fmap(f, box)`/`ap(f, x)`/`bind(f, x)` convention; the two conventions were already the same thing here.

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

`Foldable` is structural, not nominal, and none of Ekans's own shipped types currently implement `__iter__` — so there is no existing concrete instance shared between `Foldable` and any other type class in this codebase right now (per the Proof Burden, stated explicitly rather than silently skipped). The only "instances" available to test against this round are Python's own builtins (`list`, `tuple`, generators) and test-only illustrative types, which is exactly what the testing strategy below uses.

## Concrete instances in scope

None — `Foldable` is satisfied structurally by existing iterables; no new concrete Ekans type is added or retrofitted this round.

## Testing strategy

- `tests/test_foldable.py`: structural satisfaction (list/tuple/generator/custom `__iter__`-only type, both static — a function typed against `Foldable[A]` — and runtime `isinstance` checks, including a genuine rejection for a non-iterable).
- **A real regression test for the Phase 1 stack-safety finding**: fold a genuinely large sequence (tens of thousands of elements) with the process recursion limit deliberately lowered inside the test, asserting no `RecursionError` — this is the test that would have caught the broken first attempt, so it's required, not optional.
- `FoldableABC` override dispatch: a test-only type overriding `foldr` with an observably different implementation from the generic default, confirming the override path is genuinely taken (mirroring this project's established "prove the safety net is real, not just present" rigor from the `Maybe`/`Either` rounds' rogue-subclass tests).
- Every derived function gets an example-based test, plus, wherever the semantics line up with a Python builtin (`sum`, `all`, `any`, `max`/`maximum`, `min`/`minimum`, `len`/`length`), a Hypothesis property test using the builtin itself as the oracle — strong, cheap confidence without hand-deriving formulas for functions whose whole point is matching well-known behavior.
- `foldMap`/`fold`/`fold1`'s `Monoid`/`Semigroup` integration tested against real `Monoid`/`Semigroup` test doubles, both non-empty and (for `foldMap`/`fold`) empty inputs.
- `find` tested for short-circuiting (via a call-log double, matching this project's established technique for proving a function doesn't over-scan) and for its `Just[A] | Nothing[A]` return type staying precise.
- `maximum`/`minimum`/`foldr1`/`foldl1`/`fold1` tested for the documented `ValueError` on empty input.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression against the full existing suite.

## Documentation requirements

- `docs/HOWTO.md`: replace the `Foldable` stub in "Coming soon" with a real section. Since `Foldable` is neither part of Part 1's abstract `Functional` hierarchy nor a concrete type in Part 2's gallery, it gets a short **Part 3** of its own, positioned after Part 2 and before "Coming soon" — covering the Protocol's structural nature, the corrected stack-safety story (told plainly, including the wrong-first-attempt detail — this project's established honest-limitation style), the `FoldableABC` override mechanism, and the full function list with the deliberate naming/signature decisions (`and_`/`or_`, `maximumBy`'s `key`-function divergence, `find`'s `Maybe` return type).
- `CLAUDE.md`'s "Why Foldable is a Protocol" section gets its trampoline description corrected in place, per the Phase 1 finding above — this is exactly the kind of correction the Implementation Protocol's own rules require documenting plainly when a real design gap surfaces mid-round.

## Implementation constraints

- Per explicit review this round: **no cap on convenience functions** — the full pure-fold surface of `Data.Foldable` is in scope, not a minimal slice. This supersedes (for this round only) the standing "implement only what's explicitly requested" default.
- Still applies: every function actually built must be one explicitly enumerated in this spec's Design section, not further invented beyond that list without going back through review.

## Out of scope

- The `Applicative`/`Alternative`-based traversal family (`traverse_`, `for_`, `sequenceA_`, `sequence_`, `mapM_`, `forM_`, `asum`, `msum`) — per review, deferred to `Traversable`'s own round. These are effectful traversal, conceptually closer to `Traversable`'s domain even though Haskell files them under `Data.Foldable`; `asum`/`msum` specifically also need `Alternative`, which doesn't exist in this codebase at all yet.
- Retrofitting any existing Ekans type with `__iter__` to become `Foldable` — not requested, and per the Cross-Product audit above, there's no existing type this would obviously apply to without inventing a new design question of its own.
- Additional `FoldableABC` override hooks beyond `foldr`/`length`/`null` — deferred until a real type needs one, per the Design section above.

## Open questions / risks

- None outstanding — every design decision here (the covariance requirement, the corrected stack-safety mechanism, the `Type[M]` requirement for `foldMap`/`fold`, the `SupportsLt` protocol, `find`'s `Maybe` return type) was verified directly against `mypy --strict` and at runtime before being written down.
