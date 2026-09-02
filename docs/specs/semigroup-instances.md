# Spec: Semigroup instances (Sum, Product, All, Ap) + liftA2

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Semigroup instances"

## Summary

Add four small, concrete, *unconditionally* `Semigroup` types — `Sum[A]`, `Product[A]`, `All`, `Ap[A]` — matching Haskell's `Data.Monoid` newtypes of the same names. Unlike `Identity`/`Const`/`Reader`'s conditional instances from the `Semigroup` round (which never nominally inherit `Semigroup` at all), these four exist specifically to *be* a `Semigroup`: wrapping a value and picking one particular combining operation for it. Also adds `liftA2`, a free function lifting a two-argument function into any two `Applicative`s of the same shape — revisited from an earlier explicit deferral because `Ap`'s `mappend` is naturally defined in terms of it.

## Motivation

Every `Semigroup` example so far (`Box` in `docs/HOWTO.md`, `tests/`) has been a throwaway illustrative type. `Sum`/`Product`/`All`/`Ap` are the first genuinely useful, shippable `Semigroup` instances — "to keep us sane," per the request that started this round: concrete evidence the machinery built in the `Semigroup` round does something real. They're also the natural stepping stone toward `Monoid` (each has an obvious identity element — `0`, `1`, `True`, `pure mempty` — deferred to that round per the spec's own scope decision below).

## Design

### Scope: Semigroup now, Monoid later

All four types get `Semigroup` instances only, this round. `Monoid` doesn't exist yet in Ekans; once it does, a follow-up round adds `mempty` to each of these four (`Sum`'s `0`, `Product`'s `1`, `All`'s `True`, `Ap`'s `pure mempty`) rather than blocking this round on `Monoid`'s own spec/implementation.

### `Sum[A]` and `Product[A]`: bounded by a per-operation `Protocol`, not a concrete numeric `TypeVar`

```python
_AddT = TypeVar("_AddT", bound="SupportsAdd")


class SupportsAdd(Protocol):
    def __add__(self: _AddT, other: _AddT) -> _AddT: ...


A = TypeVar("A", bound=SupportsAdd)


@dataclass(frozen=True, eq=False)
class Sum(Semigroup, Generic[A]):
    value: A

    def mappend(self, other: "Sum[A]") -> "Sum[A]":
        return Sum(value=self.value + other.value)
```

`Product[M]` is the exact same shape with a `SupportsMul` protocol (`__mul__`) instead. Verified against `mypy --strict`: this self-typed `Protocol` pattern needs its own dedicated `TypeVar` for the `self`/`other` binding (`_AddT`, scoped to the protocol) — reusing the outer `A`/`M` `TypeVar` for that binding produces a real mypy error (`Invalid self argument`), a mistake made and caught during Phase 1. With the dedicated binding: `int` and `float` both satisfy `SupportsAdd`/`SupportsMul` structurally (no explicit inheritance needed, per `Protocol`'s whole point), mismatched type parameters (`Sum[int].mappend(Sum[float])`) are genuinely rejected (`[arg-type]`), and constructing `Sum` with a type that doesn't support `+` (e.g. a bare class with no `__add__`) is genuinely rejected too (`[type-var]`). Both `SupportsAdd` and `SupportsMul` are `Protocol`, not `ABC` — matching the project's existing "structural where the operation is already common, nominal where it isn't" split (see `Foldable`'s rationale in `CLAUDE.md`); `+`/`*` are exactly the kind of already-ubiquitous dunder methods that rule favors structural typing for.

Nominal, unconditional `Semigroup` instances — unlike `Identity`/`Const`/`Reader`, `Sum`/`Product` directly inherit `Semigroup` in their class declaration. There's no constrained-instance problem to solve here: the constraint (`A: SupportsAdd`) is baked into `Sum`'s own type parameter, not deferred to a free function.

### `All`: fixed to `bool`, not generic

```python
@dataclass(frozen=True, eq=False)
class All(Semigroup):
    value: bool

    def mappend(self, other: "All") -> "All":
        return All(value=self.value and other.value)
```

Matches Haskell's `newtype All = All { getAll :: Bool }` exactly — `All` is not generic over anything, `mappend` is boolean AND. No `Protocol`/`TypeVar` machinery needed at all, verified clean against `mypy --strict` with no surprises.

### `liftA2`: a free function, `@overload`-per-type like `ap`/`fmap`

```python
@overload
def liftA2(
    f: Callable[[A, B], C], fa: "Identity[A]", fb: "Identity[B]"
) -> "Identity[C]": ...
@overload
def liftA2(
    f: Callable[[A, B], C], fa: "Reader[R, A]", fb: "Reader[R, B]"
) -> "Reader[R, C]": ...
@overload
def liftA2(
    f: Callable[[A, B], C], fa: Applicative[A], fb: Applicative[B]
) -> Applicative[C]: ...
def liftA2(
    f: Callable[[A, B], C], fa: Applicative[A], fb: Applicative[B]
) -> Applicative[C]:
    return fb.ap(fa.fmap(lambda a: lambda b: f(a, b)))
```

**Correction found during Phase 1, applied here directly (spec drafted after verification, so this is the corrected shape, not a later patch):** the initial framing of this ticket (a single function generic against the abstract `Applicative[A]`/`Applicative[B]`, no per-concrete overloads needed "since it never touches a concrete class directly") turned out to be wrong. Verified directly: that fully generic version type-checks with **no errors at all**, but silently returns the loose `Applicative[C]` for every call, including `liftA2(f, Identity(...), Identity(...))` — `reveal_type` confirmed `Applicative[int]`, not `Identity[int]`. This is the identical failure mode that got `Pointed.point`'s free-function form rejected outright earlier in this project (`docs/specs/pointed.md`) — a function that type-checks cleanly but silently degrades precision is worse than one that visibly needs work. Unlike `point`, though, `liftA2` has a real generic implementation available (`fb.ap(fa.fmap(...))`, expressible purely via `Applicative`'s existing abstract methods) — so instead of rejecting a free function outright the way `point` did, `liftA2` gets the same `@overload`-per-concrete-type treatment `ap`/`fmap` already use, with the generic `Applicative[A]`/`Applicative[B]` version kept as the final loose fallback (matching `ap`'s fallback-overload shape from `apply.py`) rather than being the only signature. Verified with `reveal_type`: `Identity[int]` and `Reader[str, int]` both resolve precisely through this overload set.

`liftA2` lives in `applicative.py`, alongside the `Applicative` class it operates on — same placement logic as `ap` living in `apply.py`.

### `Ap[A]`: fixed to `Identity[A]`, not generic over an arbitrary Applicative

Haskell's `Ap` (`Data.Monoid.Ap`) is `newtype Ap f a = Ap { getAp :: f a }`, generic over *any* `Applicative` `f`. Verified directly that Python's typing cannot express this: `Generic[F, A]` with a field typed `F[A]` where `F` is a bare `TypeVar` is a hard mypy error (`Type variable "F" used with arguments [valid-type]`) — Python has no higher-kinded types, full stop, this isn't a style choice. Ekans' `Ap[A]` is therefore fixed to wrap `Identity[A]` specifically, not generic over `F`:

```python
@dataclass(frozen=True, eq=False)
class Ap(Semigroup, Generic[S]):
    value: "Identity[S]"

    def mappend(self, other: "Ap[S]") -> "Ap[S]":
        return Ap(value=liftA2(lambda a, b: a.mappend(b), self.value, other.value))
```

where `S = TypeVar("S", bound=Semigroup)`. Written this way, `mappend`'s body is a direct, faithful transcription of Haskell's `mappend (Ap x) (Ap y) = Ap (liftA2 mappend x y)` — the whole reason `liftA2` needed revisiting for this round rather than being reimplemented inline as a one-off `fmap`/`ap` chain inside `Ap` alone. Verified via `reveal_type` that `liftA2`'s `Identity`-specific overload keeps this precise (`Ap[Box]` in, `Ap[Box]` out, not a loose `Ap[Any]`), and confirmed the associativity law holds via a direct Hypothesis check before writing this down.

**Naming note:** `Ap` (the class) and `ap` (the existing free function in `ekans.apply`, and the method `Apply.ap`) differ only in case. This mirrors Haskell exactly (`Data.Monoid.Ap` vs. `<*>`/`Control.Applicative`'s `ap`), so the name is kept — flagged here explicitly so it doesn't read as an accident.

## Concrete instances in scope

- `Sum[A]`, `Product[M]`, `All`, `Ap[S]` — new concrete types, each a nominal `Semigroup` instance.
- `liftA2` — new free function on `Applicative`, with `Identity`/`Reader` overloads plus the loose `Applicative` fallback.

## Testing strategy

- `Sum`/`Product`/`All`/`Ap` are nominal `Semigroup` instances, so `tests/semigroup_laws.py`'s existing `assert_semigroup_law` applies directly to each with no new test infrastructure — this is exactly the case it was designed for (unlike `Identity`/`Const`/`Reader`'s conditional instances, which needed a hand-rolled associativity check against the free `mappend` function instead).
- `liftA2` gets its own example-based tests per concrete overload (`Identity`, `Reader`) plus a `reveal_type`-verified precision probe (deleted after use, per the Implementation Protocol).
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new sections for `Sum`, `Product`, `All`, and `Ap` (each concept, a runnable example, and — for `Ap` — the higher-kinded-types limitation explained plainly, since it's a genuine and interesting constraint worth a reader understanding, not hiding).
- `liftA2` gets a short addition to the existing `Applicative` section.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Monoid` instances (`mempty`) for any of these four types — deferred until `Monoid` itself exists.
- `First`/`Last`/`Endo`/`Dual` or any other `Data.Monoid` newtype not explicitly requested this round.
- Generalizing `Ap` beyond `Identity` — would require solving Python's higher-kinded-types gap for real, out of scope here.
- Adding `liftA2` as a default method on `Applicative` — free-function-only, per Phase 0.

## Open questions / risks

- None outstanding — every design decision here was verified directly against `mypy --strict` and at runtime (including the associativity law, via Hypothesis) before being written down.
