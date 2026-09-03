# Spec: Compose

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Compose"

## Summary

Add `Compose[W, A]` (`newtype Compose f g a = Compose (f (g a))`), a new concrete type wrapping one functor nested inside another. Gets `Functor`, `Applicative` (for the subset of pairs where both sides are nominally `Applicative`), and `Foldable` this round. A `Traversable` instance is explicitly deferred — see Out of scope — since the `Traversable` class this round exists to unblock doesn't exist yet.

## Motivation

This type exists for two reasons, in order:

1. **Immediate:** `Traversable`'s composition law (`traverse (Compose . fmap g . f) = Compose . fmap (traverse g) . traverse f`) needs a real `Compose` functor to state and test at all. Without it, `Traversable`'s composition law can't be tested — only asserted by hand-waving, which the project's existing law-testing standard doesn't accept.
2. **Standing:** discussed and agreed this round should build `Compose` as a genuine, publicly-exported type (full Haskell parity where feasible) rather than a throwaway internal fixture scoped only to one test.

## Design

### Shape

Python has no higher-kinded types, so `Compose` can't be generic over type *constructors* `f`/`g` the way Haskell is. Instead — matching the project's existing answer to this same limitation in `apply.py`/`functor.py` (per-concrete-type `@overload`s, not a fully generic HKT signature) — `Compose` is generic over `W`, the *whole* concrete nested type (e.g. `Just[Identity[int]]`), plus `A`, the innermost element type:

```python
A = TypeVar("A")
W = TypeVar("W", bound=_FoldableFunctor)  # see Foldable instance below

@dataclass(frozen=True, eq=False)
class Compose(Functor[A], Generic[W, A]):
    value: W
```

Precision for a *specific* pair (e.g. "this is a `Just` of an `Identity`") comes entirely from `@overload`s on the free functions, the same mechanism `fmap`/`ap`/`liftA2` already use. Verified against `mypy --strict`, using `Just[Identity[A]]` and `Identity[Maybe[A]]` as the two representative pairs: a free function

```python
@overload
def compose_fmap(
    f: Callable[[A], B], c: "Compose[Just[Identity[A]], A]"
) -> "Compose[Just[Identity[B]], B]": ...
@overload
def compose_fmap(
    f: Callable[[A], B], c: "Compose[Identity[Maybe[A]], A]"
) -> "Compose[Identity[Maybe[B]], B]": ...
```

reveals the fully precise `Compose[Just[Identity[str]], str]` / `Compose[Identity[Maybe[str]], str]` for each pair respectively — the pattern scales the same way `fmap`'s own overload list already does, just with more type arguments per line.

### Foldable instance: a private structural bound, not `Any`

`__iter__` needs to iterate `self.value` (the outer functor) and then iterate each yielded item (the inner functor) — i.e. `W` needs to satisfy *both* `Functor` (so `Compose.fmap` can double-map into it) *and* `Foldable` (so `Compose.__iter__` can flatten it). A bound of plain `Functor[Functor[object]]` isn't enough — verified directly: `for inner in self.value` under that bound fails with `"W" has no attribute "__iter__" (not iterable) [attr-defined]`.

Fix, verified clean with no `# type: ignore` needed: an internal (non-exported) structural `Protocol` combining both requirements, declared once in `compose.py`:

```python
class _FoldableFunctor(Foldable[Any], Protocol):
    def fmap(self, f: Callable[[Any], Any]) -> "Functor[Any]": ...
```

`W = TypeVar("W", bound=_FoldableFunctor)`. Every one of this round's candidate types (`Identity`, `Const`, `Maybe`/`Just`/`Nothing`, `Either`/`Left`/`Right`, `Tuple2`) already nominally implements `Functor` and already defines `__iter__`, so all of them satisfy `_FoldableFunctor` structurally with no changes to those files. `__iter__` itself:

```python
def __iter__(self) -> Iterator[A]:
    for inner in self.value:
        yield from inner
```

Verified against `mypy --strict`: `list(c)` for `c: Compose[Just[Identity[int]], int]` and for `c: Compose[Identity[Maybe[int]], int]` both reveal `list[int]`, with zero errors and zero ignores.

### Equality

`__eq__`/`__hash__` typed against `Compose[W, A]`, per the existing Equality convention — no new ground here beyond what `Const`'s two-type-parameter case already established.

### Naming

Field is called `value` (not Haskell's `getCompose`), matching `Identity`/`Const`/`Ap`'s existing `.value` convention.

### Applicative instance: restricted to a real subset

`Const` and `Tuple2` are **not** nominally `Applicative` in this codebase already (`docs/specs/const-applicative.md`, `docs/specs/tuple2.md`) — neither has a real `.ap()`. Haskell's own `instance (Applicative f, Applicative g) => Applicative (Compose f g)` requires *both* sides to be `Applicative`, so `Compose`'s `Applicative` instance is only meaningful when both `F` and `G` are drawn from `{Identity, Maybe, Either}` — the three of this round's five candidate types that are actually `Applicative`. `Const`/`Tuple2` still get `Compose`'s `Functor` and `Foldable` instances, same as everywhere else in the codebase they're excluded only from `Apply`/`Applicative`.

### Laws

- **Functor:** the existing identity/composition laws, reusing `tests/functor_laws.py`'s helper — no new law shape needed.
- **Applicative:** the existing identity/homomorphism/interchange/composition laws, reusing `tests/applicative_laws.py`'s helper, for the 9 eligible pairs only.
- **Foldable:** no separate law beyond what's already implied by `__iter__` existing and behaving as a real iterator (flattening both levels) — matches how `Const`/`Tuple2`/`Sum`/etc.'s own `__iter__` additions were tested (example-based, not property-law-based, since `Foldable` itself declares no laws of its own).

### Cross-Product audit (Compositional Invariance Matrix)

- **Functor ↔ Applicative:** connected by the standard law that `ap`/`liftA2` built on `fmap` already satisfy for every existing Applicative type — no new law, reuses the existing Applicative law helper (which already exercises this).
- **Functor ↔ Foldable:** no formal law connects them in Haskell's own base libraries either (`Functor` and `Foldable` are independent superclasses of `Traversable`, not of each other) — none added here.
- **Extractable:** compatible in principle — `Identity`, `Const`, and `Tuple2` (three of this round's five candidate types) already implement `Extractable`, so a `Compose` of two `Extractable` functors could sensibly support `extract` (`self.value.extract().extract()`). Not added this round: Haskell's own `Data.Functor.Compose` has no `Comonad`/extract instance in `base` either, and it wasn't part of the agreed scope (Functor + Applicative + Foldable). Proof Burden: excluded because it's genuinely out of this round's agreed scope, not a structural impossibility — worth a future round if a real use for it turns up.
- **Traversable:** the reason this type exists, but can't be implemented yet — see Out of scope.

## Concrete instances in scope

`Compose[W, A]` itself is the only new *type*; "instances" here means which `(F, G)` pairs get `fmap`/`ap` `@overload` precision, drawn from this round's five `Traversable`-candidate types: `Identity`, `Const`, `Maybe`, `Either`, `Tuple2`.

- **Functor:** all 25 ordered pairs, `F, G ∈ {Identity, Const, Maybe, Either, Tuple2}`, get a `fmap` `@overload` — including same-type pairs (e.g. `Compose[Maybe[Maybe[A]], A]`, genuinely meaningful nested-optionality, same as Haskell's `Compose Maybe Maybe` would be). **Correction from the scoping discussion:** earlier framing said "~20 pairs, excluding self-pairs" — self-pairs were never actually a well-reasoned exclusion, just an arbitrary framing on my part; there's no structural reason to exclude them, so all 25 are in scope.
- **Foldable needs no per-pair overloads at all.** Correction, found while breaking this spec into tickets: unlike `fmap`/`ap`, which must preserve the container's precise shape in their return type (the reason `Const`/`Tuple2` needed per-type overloads in the first place), `Foldable`'s free functions (`foldr`, `length`, `toList`, ...) already return non-container types (`B`, `int`, `List[A]`, ...) and are already typed generically against the `Foldable[A_co]` protocol — they work for *any* type with `__iter__`, `Compose` included, with no per-pair anything. One `__iter__` method (already in the core ticket) is the entire `Foldable` instance.
- **Applicative:** all 9 ordered pairs among the Applicative-eligible subset, `F, G ∈ {Identity, Maybe, Either}` (including self-pairs, same reasoning), get `point`/`ap` overload precision.
- `Const`/`Either`/`Tuple2` each carry an extra "fixed" type parameter (`Const[M, _]`, `Either[L, _]`, `Tuple2[H, _]`) that doesn't participate in composition — each relevant `@overload` introduces its own fresh `TypeVar` for that slot, exactly like `apply.py`'s existing `ap` overloads already do for `S`/`L`/`H`.

## Testing strategy

- Reuse `tests/functor_laws.py` and `tests/applicative_laws.py`'s existing Hypothesis helpers — no new law-checking infrastructure needed.
- Example-based construction/equality/`__iter__` tests per pair, matching the existing per-type test pattern.
- 100% coverage, `mypy --strict` clean, TDD throughout — no change from existing Code Requirements.
- Given the pair count (25 Functor/Foldable, 9 Applicative), exact per-ticket breakdown (e.g. one ticket per capability with all its pairs, vs. smaller batches) is decided at Phase 3 ticket-writing, not fixed here.

## Documentation requirements

- `docs/HOWTO.md`: new section introducing `Compose` (concept, one or two representative pairs as runnable examples, note on why it exists — unblocking `Traversable`'s composition law — without forward-referencing `Traversable` in detail, since that section doesn't exist yet).
- `CLAUDE.md`: add `Compose` to the "First concrete types" list under Design, with the same kind of structural note the other entries there already carry.

## Implementation constraints

- Implement only what is explicitly requested in each ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.
- `_FoldableFunctor` stays private (module-local, not exported, not added to `ekans/__init__.py`'s `__all__`) — it's a typing implementation detail of `compose.py`, not public API.

## Out of scope

- **`Traversable` instance for `Compose`.** Circular by construction: `Compose` is being built specifically to test `Traversable`'s composition law, so `Traversable` itself must exist first. Ships as part of `Traversable`'s own round instead, with `Compose` simply added to that round's concrete-type list alongside `Identity`/`Const`/`Maybe`/`Either`/`Tuple2` once the `Traversable` ABC is real.
- **`Reader` as an `F`/`G` position.** Same Proof Burden already used to exclude `Reader` from `Traversable` itself: it wraps a function over a potentially-unbounded domain, so it has no sensible `Foldable`/`__iter__` instance to begin with (confirmed: `reader.py` has no `__iter__`), which rules it out of `_FoldableFunctor` structurally, not by choice.
- **`Sum`/`Product`/`All`/`Ap`.** None of the four are nominally `Functor` at all (they're `Semigroup`/`Extractable` wrappers) — structurally impossible to use as an `F`/`G` position regardless of scope decisions.
- **`Extractable` instance for `Compose`.** See Cross-Product audit above.
- Operator sugar — stays out per the same standing decision `functor.md` already recorded.

## Open questions / risks

- 25 Functor/Foldable overload pairs (plus 9 Applicative ones) is a large mechanical surface for one round — worth watching whether `apply.py`/`functor.py`-style per-pair `@overload` lists get unwieldy at this count, same open risk `functor.md` already flagged at a much smaller scale.
- `Compose`'s own `fmap`/`ap` *methods* (as opposed to the free functions) can only be typed against the loose `_FoldableFunctor`/`Applicative` bounds, not per-pair precision — same tradeoff `Functor.fmap`'s abstract signature already accepts project-wide, stated plainly here since `Compose` has no subclasses to narrow it further the way `Identity`/`Const`/etc. do for their own `fmap` overrides.
- Exact per-ticket breakdown of the 25+9 pairs isn't fixed by this spec (see Testing strategy) — resolved at Phase 3.
