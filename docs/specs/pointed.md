# Spec: Pointed

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Pointed"

## Summary

Add `Pointed[A]`, the next entry in the "Endofunctor based structures" branch of the type hierarchy: an abstract class for constructing a fresh instance of a container from a single raw value, independent of `Functor` (per CLAUDE.md's Design section: "needs only Functional"). Implement it for `Identity[A]` (retrofit, alongside its existing `Functor[A]`). `Const[A, B]`'s `Pointed` instance is explicitly deferred — see Out of scope.

## Motivation

`Functor` let us transform what's already inside a container. `Pointed` is about getting a value *into* a container in the first place — the other half of what `Applicative` (`Pointed` + `Apply`, not yet built) will need. Haskell calls this `pure`; CLAUDE.md's Design section already commits to the name `point` and the `Pointed`/`Apply`/`Applicative` split.

## Design

### Shape

```python
A_co = TypeVar("A_co", covariant=True)
A = TypeVar("A")


class Pointed(Functional, Generic[A_co]):
    @classmethod
    @abstractmethod
    def point(cls, value: A) -> "Pointed[A]":
        raise NotImplementedError
```

`point`'s own `A` is a fresh TypeVar, not `A_co` — `point` is a classmethod that *binds* `A_co` for a brand-new instance; there's no existing `self` to inherit it from, unlike `fmap`.

Each concrete type overrides `point` with its own precise return type:

```python
@dataclass(frozen=True, eq=False)
class Identity(Functor[A], Pointed[A], Generic[A]):
    ...

    @classmethod
    def point(cls, value: A) -> "Identity[A]":  # type: ignore[override]
        return Identity(value=value)
```

Unlike `fmap`'s return-type narrowing (always sound, no ignore needed), `point`'s override needs `# type: ignore[override]` on *both* counts — verified mypy flags the return type narrowing *and* the argument type as incompatible with the supertype, because `point`'s parameter and return type both involve method-scoped TypeVars rather than a `self`-bound one, so mypy can't establish the substitutability it can for instance methods. Both complaints share the `[override]` code, so one ignore with one explanatory comment (per the `type: ignore` rule) covers it.

### Multiple inheritance: Functor + Pointed together

`Identity` now inherits both `Functor[A]` and `Pointed[A]`, each independently inheriting `Functional`. Verified this diamond resolves cleanly: `Identity.__mro__` is `[Identity, Functor, Pointed, Functional, ABC, Generic, object]` — `Functional` appears exactly once, the immutability guard still fires, and both `.point(...)` and `.fmap(...)` type-check precisely and chain correctly (`Identity.point(5).fmap(str)` reveals `Identity[str]`).

### No free function

Unlike `fmap`, `point` does **not** get a free-function form. Investigated and rejected: `fmap`'s free function gets its precision from matching an *already-constructed* value, which already knows its own type parameter. `point` only ever receives a bare class reference with nothing to infer a type parameter from — verified `point(Identity, 5)` silently reveals `Identity[Any]`, not `Identity[int]`, no mypy error, just quiet loss of precision (only explicit subscripting, `point(Identity[int], 5)`, recovers it). That gotcha isn't worth it when `Identity.point(5)` is already fully precise with zero caveats. `point` is classmethod-only.

## Concrete instances in scope

- **`Identity[A]`** — retrofit, alongside its existing `Functor[A]`. `Identity.point(value)` constructs `Identity(value=value)`.

`Const[A, B]`'s `Pointed` instance is deferred — see Out of scope.

## Testing strategy

- No dedicated Hypothesis *law* for `Pointed` alone — its contract (construct a value) doesn't have a meaningful cross-type law until combined with `Apply` into `Applicative` (not yet built). Per CLAUDE.md's Testing section, only Functor/Applicative/Monad (etc.) instances currently require the Hypothesis law-test requirement; `Pointed` alone doesn't yet.
- Still add a Hypothesis-generated (not hardcoded) property test specific to Identity: `Identity.point(x).value == x` for generated `x` — type-specific, not a universal law, but still varied rather than one hand-picked example.
- Standard example-based tests: construction via `point`, an `isinstance` check, immutability still holds, and `point(...).fmap(...)` chains correctly.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation — no change from existing Code Requirements/Workflow.

## Documentation requirements

- `docs/HOWTO.md`: new `Pointed` section (concept + why there's no free function + a runnable example), replacing its "Coming soon" stub.
- `docs/HOWTO.md`'s `Identity` section gets a short addition showing `Identity.point(5)`.
- CLAUDE.md: no structural changes expected — this spec is the design record.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Apply`, `Applicative`, `Bind`, `Monad` — later specs.
- **`Const[A, B]`'s `Pointed`/`Applicative` instance.** Checked against Haskell: `instance Monoid a => Applicative (Const a)`, with `pure _ = Const mempty` — `point` needs *some* value of the held type `A` to construct `Const[A, B]` from just a `B`, and the Monoid identity element (`mempty`) is the only principled source; there's no other way to conjure an `A` from nothing. `Semigroup`/`Monoid` don't exist in Ekans yet. Revisit this once they do, constraining `Const`'s `Pointed` instance to `A: Monoid` — **do not implement an unconstrained or hardcoded-default version in the meantime.**
- Free-function form of `point` — rejected, see Design above.

## Open questions / risks

- Once `Semigroup`/`Monoid` exist, revisit whether `Pointed`'s abstract signature itself needs adjustment to express a type-constrained instance (`Const[A, B]` where `A: Monoid`) — Python's typing doesn't have a direct analogue to Haskell's constrained instances, so this may need its own design pass rather than a drop-in retrofit.
