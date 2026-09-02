# Spec: Bind

**Status:** Approved
**Tickets:** see [`TICKETS.md`](../../TICKETS.md), section "Bind"

## Summary

Add `Bind(Apply)`: an ABC providing `bind`, chaining box-producing functions together without ending up with a box of boxes (`>>=` in Haskell). Retrofits `Identity` and `Reader` to implement it. `Const` is deliberately excluded — see Design below. `Monad` (`Applicative` + `Bind`) is its own future round, matching the precedent `Applicative` set combining `Pointed` + `Apply`.

## Motivation

`Bind` is the last piece needed before `Monad` — the same small-steps pattern this project already used for `Applicative` (`Pointed` and `Apply` shipped separately first). `Identity`/`Reader` already have `Functor`/`Pointed`/`Apply`/`Applicative`; `Bind` is the natural next capability for both.

## Design

### Shape: mirrors `Apply` exactly

```python
class Bind(Apply[A_co], Generic[A_co]):
    @abstractmethod
    def bind(self, f: Callable[[A_co], "Bind[B]"]) -> "Bind[B]":
        raise NotImplementedError
```

Verified against `mypy --strict`: concrete overrides need `# type: ignore[override]` on the parameter narrowing, same as `Apply.ap`'s concrete overrides — expected, not a new finding. **Verified `Bind` does *not* need to re-declare `fmap`/`ap`** the way `Applicative` re-declared them from `Apply` — `Applicative` needed that because its law helper chains `.fmap(...).ap(...)`; `Bind`'s own associativity law only ever chains `.bind(...)`, and a concrete type's own overridden `bind` (returning its own precise type) is sufficient for that chain to stay precisely typed all the way through, verified directly (`m.bind(f).bind(g)` and `m.bind(lambda a: f(a).bind(g))` both resolved to the concrete type, not the loose `Bind[...]`, with no re-declaration needed).

### Free function: single plain-typed function first, same as `fmap`'s T-001/`ap`'s T-012

```python
def bind(f: Callable[[A], "Bind[B]"], x: "Bind[A]") -> "Bind[B]":
    return x.bind(f)
```

Verified directly: without a concrete-type overload, this compiles cleanly but the return type is the loose `Bind[B]`, not the caller's actual concrete type — same precision-loss shape `fmap`/`ap` had before their first concrete overload landed, not a new problem. Ships as a single plain function this round (no `@overload` yet), gaining `Identity`'s and `Reader`'s overloads in their own tickets, following the established pattern exactly.

### The law: associativity

```
m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))
```

Verified directly: holds for a correct implementation, and genuinely caught by a deliberately broken one (a `bind` that applies `f` twice).

### `Const` is deliberately excluded (Proof Burden)

Per Phase 0, `Const`'s `Bind` instance was investigated rather than assumed either way. The only well-typed implementation of `Const[A, B].bind(f: Callable[[B], Const[A, C]]) -> Const[A, C]` must ignore `f` entirely and re-tag — there's no `B` value actually stored anywhere to feed into it, exactly the same structural reason `Const.fmap` is a no-op re-tag. Two problems, verified directly, rule this out as a genuine instance rather than a stylistic preference:

1. **It offers zero capability beyond what `Functor.fmap` already provides.** A `bind` that can never call its own function argument is not doing anything a re-tag doesn't already do.
2. **It has a real precision problem, not just a philosophical one.** Verified via `reveal_type`: given `f = lambda s: Const(value=len(s))`, `x.bind(f)` resolves to `Const[int, Never]`, not a sensible `Const[int, C]` — because `Const`'s second parameter is phantom, nothing in `f`'s body ever pins down what `C` should be (unlike `fmap`, where `C` is simply `f`'s own return type, always unambiguous). This isn't a minor ergonomics wrinkle; it means the type signature itself can't be made to work naturally.

`Const` is excluded from this round's scope. If a genuine need for it ever arises, it would need to be revisited as a deliberate, separately-justified decision — not silently added later.

## Cross-Product audit (Compositional Invariance Matrix, per CLAUDE.md)

Compatible type classes: any existing type class sharing at least one concrete instance with `Bind`'s own instances (`Identity`, `Reader`).

- **Bind × Extractable**: `Identity` is both. Law: `m.bind(f).extract() == f(m.extract()).extract()`. Verified directly via Hypothesis before writing this down. `Reader` is `Bind` but not `Extractable` (already excluded, wraps a function) — no shared instance, nothing to test.
- **Bind × Pointed**: `Identity`/`Reader` are both `Pointed` and (about to be) `Bind`. The natural law here — `point(a).bind(f) == f(a)` — is one of `Monad`'s left-identity laws, not `Bind`'s own. Deliberately **deferred to the `Monad` round**, matching this project's own precedent: `Applicative`'s four laws (which combine `Pointed` + `Apply`) were tested only once `Applicative` itself existed, not prematurely inside the `Pointed`-only or `Apply`-only rounds. Documented here rather than silently skipped.
- **Bind × Semigroup / Monoid**: `Identity`/`Reader`'s `Semigroup`/`Monoid` support is conditional on their held/produced type, structurally unrelated to `bind`'s own operation. No meaningful law connects them.

## Concrete instances in scope

- `Identity[A]`, `Reader[R, A]` — each implements `bind`, with a corresponding free-function `@overload`.

## Testing strategy

- `tests/test_bind.py`: ABC-level tests (cannot instantiate directly, `Apply` in the MRO, abstract `bind` raises if not overridden) via a local illustrative type — same shape as `test_apply.py`.
- `tests/bind_laws.py`: `assert_bind_law(make, values, equal=None)` — associativity, same shape as `assert_apply_law` (generated functions via `st.functions(like=...)`, since `f`/`g` here return *wrapped* values, not plain ones — closer to `Apply`'s law helper than `Semigroup`'s).
- Each concrete type gets a `bind`-specific example test, its own overload added to the free function, a law test via the helper, and a `reveal_type` precision probe.
- Cross-Product audit test: `Identity`'s `bind`/`extract` law.
- 100% coverage, `mypy src tests --strict` clean, TDD throughout, Cumulative Regression (full suite every ticket), per-ticket signature review before implementation.

## Documentation requirements

- `docs/HOWTO.md`: new `Bind` section (concept, the associativity law, a runnable example, and the `Const` exclusion explained plainly — an interesting, honest limitation worth explaining, not hiding).
- Short `bind` additions to `Identity`'s and `Reader`'s existing sections.

## Implementation constraints

- Implement only what is explicitly requested in the ticket. Do not add convenience functions, helper utilities, or alternative syntax sugar unless specified.

## Out of scope

- `Monad` (`Applicative` + `Bind`) — its own future round, per Phase 0.
- `Const`'s `Bind` instance — excluded on the merits, not deferred (see Design above).
- Any `>>=`/operator sugar for `bind` — matches this project's general no-operator-sugar stance, already established for `mappend`.

## Open questions / risks

- None outstanding — every design decision here (the override-narrowing shape, the fmap/ap-re-declaration question, the free function's precision-loss-until-overloads shape, the associativity law's genuine catch of a broken instance, `Const`'s exclusion, and the `Bind`/`Extractable` cross-class law) was verified directly against `mypy --strict` and at runtime before being written down.
