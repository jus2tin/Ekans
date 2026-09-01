# Spec: Apply

**Status:** Draft — awaiting review
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Apply"

## Summary

Add `Apply[A]`, the next entry in the "Endofunctor based structures" branch: an abstract class for applying a *wrapped* function to a wrapped value (`Apply[Callable[[A], B]] -> Apply[A] -> Apply[B]`), per CLAUDE.md's existing Design section ("Apply — provides `ap`; needs Functor"). Implement it for `Identity[A]` in this same round. `Const[A, B]`'s instance is deferred — same `Semigroup`/`Monoid` blocker already documented for its `Pointed` instance.

## Motivation

`Functor` lets you transform what's inside a box with a plain function. `Apply` lets you do the same thing when the function *itself* is also stuck inside a box — the step between `Functor` and `Applicative` (`Pointed` + `Apply`, not yet combined). This is the last type class needed before `Applicative` becomes assemblable from parts already built.

## Design

### Shape

```python
class Apply(Functor[A_co], Generic[A_co]):
    @abstractmethod
    def ap(self, f: "Apply[Callable[[A_co], B]]") -> "Apply[B]":
        raise NotImplementedError
```

`self` is the wrapped *value* (`Apply[A_co]`); `f` is the wrapped *function*. This matches the phrasing in the task that requested this spec — "applying a wrapped function `F[Callable[[A], B]]` to a wrapped value `F[A]`" — and corresponds to Haskell's `f <*> x` as `x.ap(f)` (function argument first in Haskell's operator, but the *value* is `self` here since `ap` is a method on the value being applied to, matching how `fmap` and `point` are already methods on their own subject).

Each concrete type overrides `ap` with its own precise parameter and return type:

```python
class Identity(Functor[A], Pointed[A], Apply[A], Generic[A]):
    ...

    def ap(self, f: "Identity[Callable[[A], B]]") -> "Identity[B]":  # type: ignore[override]
        return Identity(value=f.value(self.value))
```

Verified against `mypy --strict`: the override needs `# type: ignore[override]` on the *parameter* only (narrowing `Apply[Callable[[A_co], B]]` to `Identity[Callable[[A], B]]` is an LSP violation the same way `Identity.__eq__`'s parameter narrowing was) — but *not* the return type, unlike `Pointed.point`'s override, which needed both. The difference: `ap` is an instance method with `self`-bound `A_co` (like `fmap`), so only the parameter (contravariant position) is unsound to narrow; `point` is a classmethod using method-scoped TypeVars with no `self` to bind them, which made both positions unsound there.

### Free function: `ap(f, x)`, function first

```python
@overload
def ap(f: "Identity[Callable[[A], B]]", x: "Identity[A]") -> "Identity[B]": ...
@overload
def ap(f: "Apply[Callable[[A], B]]", x: Apply[A]) -> Apply[B]: ...
def ap(f, x):
    return x.ap(f)
```

Verified precise: `ap(wrapped_fn, wrapped_value)` reveals the concrete subtype (e.g. `Identity[str]`), not the loose fallback — same overload-per-type pattern as `fmap`, no `point`-style precision gotcha, since both arguments here are already-constructed values (unlike `point`'s bare class reference).

### The associativity law, and its honest limitation

`Apply` (independent of `Applicative`) has exactly one law:

```
(.) <$> u <*> v <*> w == u <*> (v <*> w)
```

In this project's method-call notation, with `u: Apply[Callable[[B], C]]`, `v: Apply[Callable[[A], B]]`, `w: Apply[A]`, and `compose(g)` returning the function `f -> (a -> g(f(a)))`:

```
w.ap(v.ap(u.fmap(compose))) == w.ap(v).ap(u)
```

Verified this holds for `Identity` across Hypothesis-generated examples, and — importantly — verified what it *doesn't* catch: an `ap` that ignores its function argument entirely and returns `self` unchanged trivially satisfies this law (both sides reduce to the same "untouched self" regardless of what `u`/`v`/`w` actually are). Confirmed this isn't a flaw in the test, but an inherent property of the associativity law by itself — the same category of gap `Functor`'s identity law alone has (needing the composition law too to catch double-application bugs). A double-apply bug in `ap`, by contrast, *is* caught (verified with a deliberately broken instance). This limitation is worth stating plainly rather than glossing over; the full `Applicative` laws (homomorphism, interchange), once `Pointed` and `Apply` combine, would likely close this gap, but that's out of scope here.

## Concrete instances in scope

- **`Identity[A]`** — retrofit, alongside its existing `Functor[A]`/`Pointed[A]`. Unconstrained, no blocker (matches Haskell: `Identity f <*> Identity x = Identity (f x)`).

`Const[A, B]`'s instance is deferred — see Out of scope.

## Testing strategy

- New `tests/apply_laws.py` (mirrors `tests/functor_laws.py`'s shape and its own `equal` parameter): `assert_apply_law(make, values, equal=None)`, generating `w`'s value plus two endofunctions (`f`, `g`) via `hypothesis.strategies.functions()`, same as the Functor law helper. A small `_compose` typed helper (same reasoning as `_identity`: `st.functions(like=...)` needs an annotated callable to infer from) lives alongside it.
- `Identity`'s law test calls the new helper. Plus standard example-based tests: `ap` applies correctly, immutability still holds.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout (red step shown before implementation), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Apply` section (concept, the associativity law in plain language including its honest limitation, a runnable example), replacing the current stub.
- `docs/HOWTO.md`'s `Identity` section gets a short addition showing `ap`.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Applicative`, `Bind`, `Monad` — later specs (`Applicative` becomes assemblable from `Pointed` + `Apply` once both exist, but combining them is its own spec).
- **`Const[A, B]`'s `Apply` instance.** Checked against Haskell: `instance Monoid a => Applicative (Const a)` combines held values via `Const f <*> Const x = Const (f <> x)`, using `Semigroup`'s `<>` — same `Semigroup`/`Monoid` blocker already documented for `Const`'s `Pointed` instance in `docs/specs/pointed.md`. Revisit both together once `Semigroup`/`Monoid` exist.
- Homomorphism/interchange laws — those belong to `Applicative` (they involve `pure`/`point`), not `Apply` alone; out of scope until `Applicative` is speced.

## Open questions / risks

- The associativity-law-alone gap (doesn't catch an `ap` that ignores its argument) means `Identity`'s law test isn't a complete correctness guarantee by itself — the standard examples-based test (`ap` applies correctly) is load-bearing here, not just a formality. Worth remembering when `Const`'s instance eventually lands: its law test will have the same gap.
- `apply_laws.py`'s `_compose` helper duplicates the *shape* of reasoning `functor_laws.py`'s `_identity` already established (typed stand-in for a `st.functions(like=...)` argument) without sharing code — acceptable for now since the two modules test different laws, but worth watching if a third law-helper module needs the same pattern again.
