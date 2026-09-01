# Spec: Functor

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Functor"

This is the first spec written under Ekans' spec-driven workflow (see CLAUDE.md's Workflow section). It's also meant to be the template for future specs — if its shape stops working, fix the shape here and note the change, rather than drifting format per spec.

## Summary

Add `Functor[A]`, the first entry in the "Endofunctor based structures" branch of the type hierarchy: an abstract class for "things that can be mapped over without changing their shape." Implement it for `Identity[A]` (retrofit) and a new concrete type, `Const[A, B]`. Ship both a method and a free function, plus a reusable Hypothesis-based law-checker so every future Functor instance gets the same two law tests for free.

## Motivation

`Functional` and `Identity` exist but do nothing functional yet — `Identity` is just an immutable box. `Functor` is the first real capability in the hierarchy, and Identity/Const are the two textbook instances CLAUDE.md already commits to building first (Identity as the "changes nothing" case, Const as the one that actually exercises mapping over the second type parameter by doing *nothing* to it).

## Design

### Shape

```python
A_co = TypeVar("A_co", covariant=True)
B = TypeVar("B")

class Functor(Functional, Generic[A_co]):
    @abstractmethod
    def fmap(self, f: Callable[[A_co], B]) -> "Functor[B]":
        raise NotImplementedError
```

Each concrete type overrides `fmap` with its own precise return type. That's a covariant *return-type* narrowing, which is always sound and needs no `# type: ignore` (unlike the parameter-narrowing situation `Identity.__eq__` is already in):

```python
@dataclass(frozen=True, eq=False)
class Identity(Functor[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "Identity[B]":
        return Identity(value=f(self.value))
```

Verified against `mypy --strict`: calling `.fmap` on an `Identity[int]` reveals `Identity[str]` after mapping with `str`; calling it through a `Functor[int]`-typed reference correctly falls back to the looser `Functor[str]`, exactly as expected for an ABC-typed handle.

`Functional` stays in the MRO through `Functor(Functional, Generic[A_co])` — `Identity` doesn't need to name it again explicitly. Confirmed at runtime: `Identity.__mro__` is `[Identity, Functor, Functional, ABC, Generic, object]`, and mutating a constructed `Identity` still raises `FrozenInstanceError` (a subclass of `AttributeError`) exactly as it does today — the extra inheritance level doesn't let anything slip past the immutability guard.

### Naming: `fmap`, not `map`

Both the method and the free function are called `fmap` (confirmed over `map`, which would shadow the builtin `map()` when imported). This departs slightly from `.map()`-style Python idiom in favor of matching Haskell — consistent with CLAUDE.md's "extremely opinionated... will not feel very pythonic" design principle.

### Variance: covariant

`A_co` is covariant. A `Functor[A]` only ever *produces* `A`s (as the output type of `fmap`'s callable's `Callable[[A_co], B]` parameter — nested inside a `Callable`, `A_co` sits in a contravariant-of-contravariant position, which composes to covariant, so this is sound and mypy accepts it without complaint). This is the standard variance for a read-only container position, matching Haskell's own `Functor` intuition.

### Typing precision: overloaded free function, not a custom mypy plugin

Python has no true higher-kinded types. The `returns` library's `KindN` approach gets full HKT-style polymorphism, but only by shipping and maintaining its own mypy plugin — a maintenance burden this project's scale doesn't justify.

Instead: the free function `fmap` gets one `@overload` per concrete Functor type, added as each type lands, plus a final loose fallback overload typed against the abstract `Functor[A]` itself:

```python
@overload
def fmap(f: Callable[[A], B], functor: Identity[A]) -> Identity[B]: ...
@overload
def fmap(f: Callable[[A], B], functor: Const[C, A]) -> Const[C, B]: ...
@overload
def fmap(f: Callable[[A], B], functor: Functor[A]) -> Functor[B]: ...
def fmap(f, functor):
    return functor.fmap(f)
```

Verified against `mypy --strict`: `fmap(str, Identity(value=1))` still reveals precise `Identity[str]`; `fmap(str, Const(value=1))` still reveals precise `Const[int, str]` — the fallback doesn't cost precision for concrete calls, since mypy resolves `@overload`s top-to-bottom and picks the first match. Without the fallback, generic code written against an abstract `Functor[A]` handle (e.g. a function that takes `x: Functor[A]` and calls `fmap` on it) fails to type-check at all — confirmed the exact failure: `No overload variant of "fmap" matches argument types "Callable[[A], A]", "Functor[A]"`. With the fallback added, that same generic code type-checks, correctly falling back to the loose `Functor[A]` return type.

**Tradeoff, stated plainly:** this doesn't give a caller *fully generic* code (e.g. a function written once against "any Functor" can't get a precisely-typed return without its own overloads or accepting the loose `Functor[B]`). For a library at this scale, where consumers mostly work with concrete, known types, that's an acceptable gap. Revisit if that stops being true.

### Laws

Functor instances must satisfy, for all `x: Functor[A]`:

- **Identity law:** `fmap(id, x) == x`, where `id = lambda a: a`.
- **Composition law:** `fmap(compose(g, f), x) == fmap(g, fmap(f, x))`, for all `f: A → B`, `g: B → C`, where `compose(g, f) = lambda a: g(f(a))`.

## Concrete instances in scope

- **`Identity[A]`** — retrofit. `fmap` unwraps, applies `f`, rewraps. Trivially satisfies both laws; this is the "control group" instance mentioned in `docs/HOWTO.md`.
- **`Const[A, B]`** (`data Const a b = Const a`) — new type. Holds a value of type `A`, ignores `B` entirely; `fmap` is a no-op re-tag (`Const(value=self.value)`), since there's no `B` to touch. New concrete type, so it also needs: `Functional` base, frozen dataclass, type-safe `__eq__`/`__hash__` per the existing Equality convention (extended here to two type parameters — invariant in both `A` and `B`), and its own `docs/HOWTO.md` section (replacing its current "Coming soon" stub).

`Proxy[A]` and `Star[F, A, B]` stay out of scope for this spec — Proxy has no value to map over (mapping over a phantom type is trivially a no-op that's arguably not worth a real Functor instance), and Star's Functor-adjacent behavior depends on Category work that hasn't been speced yet.

## Testing strategy

- Per-type Hypothesis tests for both laws, **plus** a reusable law-checking helper so future Functor instances don't re-derive the same two tests from scratch. Shape (in `tests/`, not shipped as part of the public `ekans` package — this is test infrastructure, not a library primitive, so it does **not** get a `docs/HOWTO.md` entry):

  ```python
  def assert_functor_laws(
      make: Callable[[A], Functor[A]],
      values: SearchStrategy[A],
  ) -> None:
      """Assert the Functor identity and composition laws for `make`."""

      @given(values)
      def identity_law(value: A) -> None:
          x = make(value)
          assert x.fmap(lambda a: a) == x

      @given(
          values,
          st.functions(like=lambda a: a, returns=values, pure=True),
          st.functions(like=lambda a: a, returns=values, pure=True),
      )
      def composition_law(value: A, f: Callable[[A], A], g: Callable[[A], A]) -> None:
          x = make(value)
          assert x.fmap(lambda a: g(f(a))) == x.fmap(f).fmap(g)

      identity_law()
      composition_law()
  ```

  `f` and `g` are generated per-example via `hypothesis.strategies.functions()` rather than hardcoded — `pure=True` keeps a given generated function returning the same output for the same input within one check, which the law's equality assertion depends on, and Hypothesis varies *and shrinks* the actual function used across runs instead of exercising just one fixed pair. Verified two ways: it passes across generated examples for a correct `fmap`, and — checked with a deliberately broken `fmap` (one that applied `f` twice) — it fails with a concrete counterexample, confirming the helper isn't vacuously true.

  Each concrete type's test module calls this with its own constructor and a values strategy under `@given` via the helper — no per-type `f`/`g` to hand-pick.
- Standard example-based tests too (matches the existing pattern for `Identity`/`Functional`): construction, a concrete `fmap` call, equality/hash behavior for `Const`.
- 100% coverage, `mypy --strict` clean, TDD (test before implementation) throughout — no change from existing Code Requirements.

## Documentation requirements

- `docs/HOWTO.md`: replace the `Functor` stub with a real section (concept + the two laws in plain language + a runnable example). Replace `Identity`'s forward-reference ("Once Functor lands...") with the real behavior. Replace `Const[A, B]`'s stub with a real section.
- CLAUDE.md: no structural changes expected: this spec *is* the design record for Functor, so CLAUDE.md's own Design section doesn't need duplicate content — it can stay pointing at the Type hierarchy list, with specs as the detail layer underneath it going forward.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Pointed`, `Apply`, `Applicative`, `Bind`, `Monad` — later specs.
- `Proxy`, `Star` Functor/Profunctor instances — later specs, per above.
- Operator sugar (e.g. a `<$>`-like infix operator) — explicitly rejected, stays close to Python idiom per existing CLAUDE.md principle.

## Open questions / risks

- The overload-per-type approach means `functor.py`'s free `fmap` grows a new overload with every future Functor instance across the whole codebase (Proxy, Star, Maybe, Either, ...) — worth watching whether that becomes unwieldy and, if so, revisiting (possibly the custom-mypy-plugin route, if the project ever grows enough to justify it).
- `Const`'s two-type-parameter equality is new ground for the Equality convention (previously only exercised on Identity's single parameter) — worth double-checking mypy actually rejects mismatches on *either* parameter, not just one, before calling that ticket done.
