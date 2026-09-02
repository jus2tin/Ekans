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

None of Ekans's own shipped types satisfied `Foldable` when this spec was first approved — none defined `__iter__`. That was expected for the initial round, not a gap, and is now superseded by the retrofit documented below.

### Retrofit: `__iter__` on existing concrete types (added after initial approval)

Requested directly, after T-064–T-066 shipped: give every Ekans concrete type that has a genuine, Haskell-faithful `Foldable` instance a real `__iter__`, so it satisfies `Foldable` structurally rather than remaining an intentional non-instance forever. "Genuine" means: does the equivalent Haskell type actually derive/define `Foldable`, folding over the same type parameter this project's `Functor`/`Extractable` instances already treat as "the" contained value?

**In scope, each mirroring an existing Haskell `Foldable` instance:**
- `Identity[A]` — `instance Foldable Identity`; one element, `self.value`.
- `Const[A, B]` — `instance Foldable (Const a)`; folds over `B`, which is never actually held, so always empty (`iter(())`), matching `Const`'s own `fmap`, which is a no-op re-tag over the same phantom `B`.
- `Just[A]` / `Nothing[A]` — `instance Foldable Maybe`; one element / empty. Declared abstract on `Maybe` and overridden per variant, the same pattern already used for `fmap`/`ap`/`bind`.
- `Left[L, R]` / `Right[L, R]` — `instance Foldable (Either a)`; folds over `R`, matching the existing `Monad[R]` bias — empty / one element. Same abstract-on-`Either`, override-per-variant shape.
- `Tuple2[A, B]` — `instance Foldable ((,) a)`; folds over `B` only, matching `Tuple2`'s existing `Functor[B]`/`Extractable[B]` bias — one element, `self.second`.
- `Sum[A]`, `Product[M]` — modern GHC `base` derives `Functor`/`Foldable`/`Traversable` for these newtype wrappers; one element, `self.value`.
- `Ap[S]` — wraps `Identity[S]`; folds through the inner `Identity`, yielding its one `S`. `self.value.value` (unwrap through the wrapped `Identity`, not `self.value` itself, which is the `Identity[S]`, not the `S`).

**Excluded, each with a structural reason (Proof Burden):**
- `All` — not generic at all; it wraps a fixed `bool` with no type parameter. Haskell's own `All` has kind `*`, not `* -> *`, so `Foldable All` isn't even expressible there — there is no instance to mirror, faithfully or otherwise.
- `Reader[R, A]` — wraps `Callable[[R], A]`. Producing the `A` requires an `R` that doesn't exist independent of a caller supplying one; there is no canonical, finite enumeration to hand back. Same "functions aren't structurally comparable" reasoning already used to justify `Reader`'s deliberately-absent `__eq__` (see `docs/specs/reader.md`'s Equality section) — applies identically here to iteration.
- `Proxy[A]`, `Star[F, A, B]` — not yet implemented in this codebase; out of scope by non-existence, not by exclusion. Will get their own Proof Burden reasoning if/when built (`Proxy` holds nothing at runtime, so likely excluded the same way `All` is here; `Star` wraps a function, likely excluded the same way `Reader` is).

None of these types nominally inherit from `Foldable` — consistent with the Protocol's whole design point (see above), `__iter__` alone is what makes each structurally satisfy it, with zero explicit inheritance.

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

The initial round had nothing to audit (per the Proof Burden note that stood in this section before the retrofit above). The retrofit changes that: seven concrete types now have real `__iter__` implementations, so this needs a genuine pass. Checked which retrofitted types nominally inherit each compatible type class directly (`issubclass`), not just structurally resemble one:

**`Foldable` × `Functor`** — nominal `Functor` (directly or via `Monad`'s ancestry): `Identity`, `Const`, `Tuple2`, `Maybe`/`Just`/`Nothing`, `Either`/`Left`/`Right`. (`Sum`, `Product`, `Ap` are not `Functor` — no `fmap` — so this pair doesn't apply to them.) The genuine law: **`toList(fmap(f, xs)) == [f(y) for y in toList(xs)]`** — mapping then listing agrees with listing then mapping, i.e. `fmap` and the `Foldable` instance touch the same elements. Holds for every type in this list, verified by hand for each:
- `Identity`/`Just`/`Right`: one element on both sides, trivially the same value run through `f`.
- `Nothing`/`Left`: empty on both sides (`fmap` re-tags without touching anything, `__iter__` yields nothing either way).
- `Const`: both sides empty regardless of `f` — `fmap` never had a `B` to apply `f` to, and `__iter__` never had a `B` to yield.
- `Tuple2`: one element on both sides (`second`), `first` is untouched by both.

This is a real property to test, not a formality — added as a Hypothesis property test per type below.

**`Foldable` × `Extractable`** — nominal `Extractable`: `Identity`, `Const`, `Tuple2`, `Sum`, `Product`, `Ap`. The candidate law: **`toList(xs) == [extract(xs)]`** — `extract` and the `Foldable` instance agree on "the" contained value. Holds for `Identity`, `Tuple2`, `Sum`, `Product`, `Ap`, since each one's `extract` and `__iter__` both operate on the exact same field (`Ap`'s `extract` unwraps the same way its `__iter__` does — through the inner `Identity`). **Does not hold for `Const`**: `Const.extract()` returns the held `A`, but `Const`'s `Foldable` instance folds over the phantom `B` and is always empty — `extract` and `__iter__` touch two entirely different type parameters by construction, so there is no such law for `Const`, and none is claimed. Recorded here per the Proof Burden rather than silently tested-and-skipped; a dedicated test asserts the divergence explicitly (`toList(Const(...)) == []` regardless of what `extract` returns) so the exclusion is demonstrated, not just asserted in prose.

**`Foldable` × `Pointed`** — nominal `Pointed` (via `Monad`'s ancestry): `Identity`, `Maybe`/`Just`/`Nothing`, `Either`/`Left`/`Right`. (`Const.point`/`Tuple2.point` exist as classmethods for the free-function pattern, per CLAUDE.md's conditional-instance design, but neither class nominally inherits `Pointed` — confirmed via `issubclass` — so this pair doesn't formally apply to them, even though `Tuple2.point`'s coherence happens to hold too as a side note.) The candidate law: **`toList(point(x)) == [x]`** — wrapping a value with `point` and then listing it recovers exactly that value. Holds for `Identity.point`, `Maybe.point` (always `Just`), and `Either.point` (always `Right`) — each unconditionally produces the "full" variant.

**`Foldable` × `Semigroup`/`Monoid`** — nominal `Semigroup`/`Monoid`: `Sum`, `Product`, `Const`/`Identity`/`Tuple2`/`Reader` (conditionally, via non-nominal `mempty`/`mappend` free functions). No additional law beyond what's already covered above: for `Sum`/`Product`, `mappend`'s effect on the single element is already fully characterized by the `Extractable`×`Foldable` coherence law above (both `extract` and `toList` see the combined value post-`mappend`, same as pre-`mappend`) — there's no separate "Semigroup coherence" fact to state or test beyond that. Haskell itself has no general law connecting an arbitrary `Semigroup`/`Foldable` pair (e.g. list's `Semigroup` is `++`, entirely unrelated to how `Foldable` folds its elements) — reasoned through and recorded as a legitimate no-new-law outcome, not skipped for lack of looking.

**`Foldable` × `Bind`/`Monad`** — nominal `Monad`: `Identity`, `Maybe`, `Either`. No new law: any relationship between `bind` and the `Foldable` instance for these specific single/zero-element types reduces immediately to `Monad`'s own laws (already tested in the `Monad` round) composed with the `Functor` coherence law above — there is nothing `Foldable`-specific left to state. Haskell has no general `Foldable`/`Monad` law either (`list`'s own `bind` flattens, which plenty of `Foldable` instances don't do at all). Recorded as reasoned-through, not silently assumed.

## Concrete instances in scope

`Identity`, `Const`, `Just`, `Nothing`, `Left`, `Right`, `Tuple2`, `Sum`, `Product`, `Ap` — each gets a real `__iter__`, per the retrofit Design section above. `All` and `Reader` are explicitly excluded, with structural justification recorded there.

## Testing strategy

- `tests/test_foldable.py`: structural satisfaction (list/tuple/generator/custom `__iter__`-only type, both static — a function typed against `Foldable[A]` — and runtime `isinstance` checks, including a genuine rejection for a non-iterable).
- **A real regression test for the Phase 1 stack-safety finding**: fold a genuinely large sequence (tens of thousands of elements) with the process recursion limit deliberately lowered inside the test, asserting no `RecursionError` — this is the test that would have caught the broken first attempt, so it's required, not optional.
- `FoldableABC` override dispatch: a test-only type overriding `foldr` with an observably different implementation from the generic default, confirming the override path is genuinely taken (mirroring this project's established "prove the safety net is real, not just present" rigor from the `Maybe`/`Either` rounds' rogue-subclass tests).
- Every derived function gets an example-based test, plus, wherever the semantics line up with a Python builtin (`sum`, `all`, `any`, `max`/`maximum`, `min`/`minimum`, `len`/`length`), a Hypothesis property test using the builtin itself as the oracle — strong, cheap confidence without hand-deriving formulas for functions whose whole point is matching well-known behavior.
- `foldMap`/`fold`/`fold1`'s `Monoid`/`Semigroup` integration tested against real `Monoid`/`Semigroup` test doubles, both non-empty and (for `foldMap`/`fold`) empty inputs.
- `find` tested for short-circuiting (via a call-log double, matching this project's established technique for proving a function doesn't over-scan) and for its `Just[A] | Nothing[A]` return type staying precise.
- `maximum`/`minimum`/`foldr1`/`foldl1`/`fold1` tested for the documented `ValueError` on empty input.
- **Retrofit tests, per type**: `isinstance(x, Foldable)` now `True` (was `False` before, per each type's existing test suite); `toList`/`list(x)` example-based tests for every element shape (empty and non-empty, where applicable). Existing test files (`test_identity.py`, `test_const.py`, `test_maybe.py`, `test_either.py`, `test_tuple2.py`, `test_sum.py`, `test_product.py`, `test_ap.py`) each gain their own `__iter__`/`Foldable` tests rather than a new shared file, matching how each type's own test file already owns its other behaviors.
- **Cross-Product law tests, per the audit above**: `Functor`×`Foldable` coherence (`toList(fmap(f, xs)) == [f(y) for y in toList(xs)]`) as a Hypothesis property test for `Identity`, `Const`, `Tuple2`, `Just`/`Nothing`, `Left`/`Right`. `Extractable`×`Foldable` coherence (`toList(xs) == [extract(xs)]`) as a Hypothesis property test for `Identity`, `Tuple2`, `Sum`, `Product`, `Ap`, plus one explicit example test on `Const` demonstrating the documented non-law (`extract` and `toList` diverge). `Pointed`×`Foldable` coherence (`toList(point(x)) == [x]`) as a Hypothesis property test for `Identity`, `Maybe`, `Either`.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation, Cumulative Regression against the full existing suite.

## Documentation requirements

- `docs/HOWTO.md`: replace the `Foldable` stub in "Coming soon" with a real section. Since `Foldable` is neither part of Part 1's abstract `Functional` hierarchy nor a concrete type in Part 2's gallery, it gets a short **Part 3** of its own, positioned after Part 2 and before "Coming soon" — covering the Protocol's structural nature, the corrected stack-safety story (told plainly, including the wrong-first-attempt detail — this project's established honest-limitation style), the `FoldableABC` override mechanism, and the full function list with the deliberate naming/signature decisions (`and_`/`or_`, `maximumBy`'s `key`-function divergence, `find`'s `Maybe` return type).
- `CLAUDE.md`'s "Why Foldable is a Protocol" section gets its trampoline description corrected in place, per the Phase 1 finding above — this is exactly the kind of correction the Implementation Protocol's own rules require documenting plainly when a real design gap surfaces mid-round.
- **Retrofit**: `docs/HOWTO.md`'s Part 3 `Foldable` section gets a closing subsection noting which concrete types now satisfy `Foldable` (and the two structural exclusions), rather than leaving the "none of Ekans's own types satisfy Foldable" framing stale. Each individual type's own Part 2 gallery entry (`Identity`, `Const`, `Maybe`, `Either`, `Tuple2`, `Sum`, `Product`, `Ap`) gets a one- or two-line mention of its new `Foldable` instance where that type is introduced, not just in the Part 3 summary.

## Implementation constraints

- Per explicit review this round: **no cap on convenience functions** — the full pure-fold surface of `Data.Foldable` is in scope, not a minimal slice. This supersedes (for this round only) the standing "implement only what's explicitly requested" default.
- Still applies: every function actually built must be one explicitly enumerated in this spec's Design section, not further invented beyond that list without going back through review.

## Out of scope

- The `Applicative`/`Alternative`-based traversal family (`traverse_`, `for_`, `sequenceA_`, `sequence_`, `mapM_`, `forM_`, `asum`, `msum`) — per review, deferred to `Traversable`'s own round. These are effectful traversal, conceptually closer to `Traversable`'s domain even though Haskell files them under `Data.Foldable`; `asum`/`msum` specifically also need `Alternative`, which doesn't exist in this codebase at all yet.
- Additional `FoldableABC` override hooks beyond `foldr`/`length`/`null` — deferred until a real type needs one, per the Design section above.
- `Proxy`/`Star`'s eventual `Foldable` (non-)instances — deferred until those types exist at all; noted in the retrofit Design section above for when that happens.
- Nominal `Foldable` inheritance for any retrofitted type — deliberately not done; `Foldable`'s entire design point (see "Why Foldable is a Protocol") is structural satisfaction via `__iter__` alone, with zero explicit inheritance, for every type this project or its users define.

## Open questions / risks

- None outstanding — every design decision here (the covariance requirement, the corrected stack-safety mechanism, the `Type[M]` requirement for `foldMap`/`fold`, the `SupportsLt` protocol, `find`'s `Maybe` return type, the retrofit's scope/exclusions and Cross-Product laws) was verified directly against `mypy --strict` and at runtime (or, for the retrofit's laws, by hand-derivation matching each type's already-verified `fmap`/`extract`/`point` behavior) before being written down.
