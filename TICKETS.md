# Tickets

Lightweight, in-repo ticket tracking — no external issue tracker. One `##` section per ticket, self-contained, so this can later split into one-file-per-ticket if it ever grows past a comfortable single file (same pattern as `docs/HOWTO.md`).

**Lifecycle:** `Open` → `Closed`. A ticket closes when its Definition of Done is met — 100% coverage, `mypy --strict` clean, `black`/`isort`/`flake8` clean, TDD followed (test committed before implementation), and `docs/HOWTO.md` updated if the ticket adds a documented concept. Claude closes tickets itself once these are verifiably true, no separate sign-off required — see CLAUDE.md's Workflow section.

Each ticket references the spec it was derived from. No spec, no ticket.

## Functor

Spec: [`docs/specs/functor.md`](docs/specs/functor.md)

### T-001: Functor ABC

**Status:** Closed

Add `src/ekans/functor.py` with the `Functor[A_co]` abstract class per the spec: covariant type parameter, abstract `fmap` method, plus the free `fmap` function with its fallback `@overload` (`Functor[A] -> Functor[B]`) in place from the start, so generic code against the abstract handle type-checks immediately — T-003/T-004 add their own concrete overloads *above* the fallback as each type lands. Includes the `docs/HOWTO.md` `Functor` section (concept + both laws in plain language + a runnable example), replacing the current stub.

### T-002: Functor law-checking test helper

**Status:** Closed
**Depends on:** T-001

A reusable Hypothesis-based helper (in `tests/`, not part of the public package — no `docs/HOWTO.md` entry, this is test infrastructure) asserting the identity and composition laws from the spec, parameterized over a constructor and a values strategy — `f`/`g` are generated internally per-example via `hypothesis.strategies.functions()`, not passed in by the caller. T-003 and T-004 are its first two callers.

### T-003: Identity implements Functor

**Status:** Closed
**Depends on:** T-001, T-002

Retrofit `Identity[A]` to inherit `Functor[A]` and implement `fmap`. Add its overload to the free `fmap` function. Law tests via the T-002 helper, plus a concrete example test. Update `docs/HOWTO.md`'s `Identity` section to replace the "Once Functor lands..." forward-reference with the real behavior.

### T-004: Const[A, B] concrete type + Functor instance

**Status:** Closed
**Depends on:** T-001, T-002

New type: `src/ekans/const.py`, `Const[A, B]` (`data Const a b = Const a`), `Functional`-based frozen dataclass, `fmap` is a no-op re-tag. Type-safe `__eq__`/`__hash__` per the Equality convention, extended to two type parameters (invariant in both — confirm mypy rejects a mismatch on *either* parameter, not just one, per the spec's open question). Add its overload to the free `fmap` function. Law tests via the T-002 helper, plus example/equality tests. Replace `Const[A, B]`'s `docs/HOWTO.md` stub with a real section.

## Pointed

Spec: [`docs/specs/pointed.md`](docs/specs/pointed.md)

### T-005: Pointed ABC

**Status:** Closed

Add `src/ekans/pointed.py` with the `Pointed[A_co]` abstract class per the spec: covariant type parameter, abstract classmethod `point`. No free function (rejected in the spec — see Design). Includes the real `docs/HOWTO.md` `Pointed` section (concept, why no free function, a runnable example), replacing the current stub.

### T-006: Identity implements Pointed

**Status:** Closed
**Depends on:** T-005

Retrofit `Identity[A]` to also inherit `Pointed[A]` (alongside its existing `Functor[A]`) and implement `point`. Tests: construction via `point`, immutability still holds, `point(...).fmap(...)` chains correctly, and a Hypothesis-generated property test (`Identity.point(x).value == x`) — not a universal law, just varied rather than hardcoded, per the spec's Testing strategy. Update `docs/HOWTO.md`'s `Identity` section with a short addition showing `Identity.point(5)`.

## Reader

Spec: [`docs/specs/reader.md`](docs/specs/reader.md)

### T-007: Extend assert_functor_laws with an optional equality comparator

**Status:** Closed

Add an optional `equal` parameter to `tests/functor_laws.py`'s `assert_functor_laws`, defaulting to `==` when omitted. Existing `Identity`/`Const` callers keep passing (verify by running their existing test suites unmodified). T-009 is the first caller to actually use a custom `equal`.

### T-008: Add the `const` combinator

**Status:** Closed

`def const(value: A) -> Callable[[C], A]` in `src/ekans/reader.py` per the spec's Design section — `C` inferred from call-site context, not a caller-supplied argument. Small standalone example-based test. T-010 is its only consumer.

### T-009: Reader[R, A] concrete type + Functor instance

**Status:** Closed
**Depends on:** T-007

`src/ekans/reader.py`: `Reader[R, A]` (`Functional`-based frozen dataclass, `run: Callable[[R], A]`), `Functor[A]` instance via composition. Deliberately no `__eq__`/`__hash__` override — see the spec's Equality section for why. Law tests via the T-007-extended helper with a comparator sampling environment values. Add its overload to the free `fmap` function. Real `docs/HOWTO.md` `Reader` section, replacing the current stub.

### T-010: Reader implements Pointed

**Status:** Closed
**Depends on:** T-008, T-009

Retrofit `Reader[R, A]` to also inherit `Pointed[A]` and implement `point` using `const`. Tests: construction via `point`, `point(...).fmap(...)` chains correctly (compared via `.run(env)`, not `==`). Update `docs/HOWTO.md`'s `Reader` section with `point` and `const`.

### T-011: Reader.__call__

**Status:** Closed

Add `__call__` to `Reader[R, A]` per the spec's amended Design section — delegates to `run`, no other behavior. Update `docs/HOWTO.md`'s `Reader` section with a short mention.

## Apply

Spec: [`docs/specs/apply.md`](docs/specs/apply.md)

### T-012: Apply ABC

**Status:** Closed

Add `src/ekans/apply.py` with the `Apply[A_co]` abstract class per the spec: `Functor[A_co]` subclass, abstract `ap` method, plus the free `ap` function (function-first argument order) as a single plain-typed function for now, same as `fmap`'s T-001 shape — no `Identity` overload yet, since `Identity` doesn't implement `Apply` until T-014 (an earlier draft got this wrong; corrected during implementation, see the spec's Design section). Includes the real `docs/HOWTO.md` `Apply` section, replacing the current stub.

Amended during T-013: `Apply` also re-declares `fmap`, narrowing its return type to `Apply[B]` (inherited from `Functor` it would otherwise stay `Functor[B]`) — needed for the law helper's chained `.fmap(...)`/`.ap(...)` calls to type-check; see the spec's Design section.

### T-013: Apply associativity law-checking helper

**Status:** Closed
**Depends on:** T-012

`tests/apply_laws.py`: `assert_apply_law(make, values, equal=None)` per the spec's Testing strategy — generates `w`'s value plus two endofunctions via `hypothesis.strategies.functions()`, with a small typed `_compose` helper alongside it. T-014 is its first caller.

### T-014: Identity implements Apply

**Status:** Closed
**Depends on:** T-012, T-013

Retrofit `Identity[A]` to also inherit `Apply[A]` (alongside its existing `Functor[A]`/`Pointed[A]`) and implement `ap`. Add its overload to the free `ap` function. Law test via the T-013 helper, plus a concrete example test. Update `docs/HOWTO.md`'s `Identity` section with a short `ap` addition.

## Applicative

Spec: [`docs/specs/applicative.md`](docs/specs/applicative.md)

### T-015: Applicative ABC

**Status:** Closed

Add `src/ekans/applicative.py` with `Applicative[A_co](Pointed[A_co], Apply[A_co], Generic[A_co])` per the spec: no new abstract methods, pure composition. Includes the real `docs/HOWTO.md` `Applicative` section, replacing the current stub.

Amended during T-016: `Applicative` also re-declares `fmap` and `ap`, narrowing both from the inherited `Apply[...]` to `Applicative[...]` — needed for the law helper's chained `.fmap(...)`/`.ap(...)` calls to type-check; see the spec's Design section.

### T-016: Applicative law-checking helper

**Status:** Closed
**Depends on:** T-015

`tests/applicative_laws.py`: `assert_applicative_law(point, values, equal=None)` per the spec's Testing strategy — identity, homomorphism, interchange, and composition laws, all expressed via `point` alone (no separate `make`). T-017 and T-019 are its callers.

### T-017: Identity implements Applicative

**Status:** Closed
**Depends on:** T-015, T-016

Retrofit `Identity[A]`'s base classes to `Applicative[A]` only, dropping the now-redundant explicit `Pointed[A]`/`Apply[A]` (MRO conflict otherwise — same lesson as T-006/T-014). No new methods. Law test via the T-016 helper. Update `docs/HOWTO.md`'s `Identity` section with a short note.

### T-018: Reader implements Apply

**Status:** Closed
**Depends on:** T-012 (Apply ABC)

Add `ap` to `Reader[R, A]`, threading the same environment value into both the wrapped function and the wrapped value — verified behavior, not just type, per the spec's Design section. Add its overload to the free `ap` function. Law test via `apply_laws.assert_apply_law` with the environment-sampling `equal` comparator. Update `docs/HOWTO.md`'s `Reader` section with a real `ap` example.

### T-019: Reader implements Applicative

**Status:** Closed
**Depends on:** T-016, T-018

Retrofit `Reader[R, A]`'s base classes to `Applicative[A]` only, dropping the now-redundant explicit `Functor[A]`/`Pointed[A]` — same MRO lesson as T-017. No new methods. Law test via the T-016 helper with the environment-sampling `equal` comparator. Update `docs/HOWTO.md`'s `Reader` section with a short note.

## Semigroup

Spec: [`docs/specs/semigroup.md`](docs/specs/semigroup.md)

### T-020: Semigroup ABC

**Status:** Closed

Add `src/ekans/semigroup.py` with the `Semigroup(Functional)` abstract class per the spec: abstract `mappend(self, other: Self) -> Self`, no override narrowing needed anywhere thanks to `typing.Self` (verified in Phase 1 — see spec's Design section). No free `mappend` function yet — that's T-022, since it needs at least one concrete container overload to be worth introducing (same reasoning as `fmap`'s T-001/`ap`'s T-012). Includes the real `docs/HOWTO.md` `Semigroup` section, replacing the current stub.

### T-021: Semigroup associativity law-checking helper

**Status:** Closed
**Depends on:** T-020

`tests/semigroup_laws.py`: `assert_semigroup_law(make, values, equal=None)` per the spec's Testing strategy — the single associativity law. T-022's Identity test and later tickets are its callers.

### T-022: `mappend` free function + Identity support

**Status:** Closed
**Depends on:** T-020, T-021

Add the free `mappend(a, b)` function to `src/ekans/semigroup.py`, typed `Identity[S] -> Identity[S] -> Identity[S]` and bound by `S = TypeVar("S", bound=Semigroup)` (per the spec's Design section — `Identity` itself does not inherit `Semigroup`). Ships as a single plain-typed function, *not* an `@overload` — mypy rejects a single-variant overload set (`error: Single overload definition, multiple required  [misc]`, confirmed during this ticket; see the spec's Design section correction note), same lesson as `fmap`'s T-001/`ap`'s T-012. Becomes a real `@overload` set once T-023 adds `Const`'s variant. A small local illustrative `Semigroup`-implementing type lives in the test module for this and all following Semigroup tickets, per the spec's note that no shipped Ekans type is unconditionally a Semigroup. Law test via the T-021 helper. Update `docs/HOWTO.md`'s `Identity` section with a short `mappend` addition.

### T-023: `Const[A, B]` `mappend` support

**Status:** Closed
**Depends on:** T-022

Add the `Const[S, A] -> Const[S, A] -> Const[S, A]` overload to the free `mappend` function, converting it from T-022's single plain-typed function into a real two-variant `@overload` set: `Const x mappend Const y = Const (x mappend y)`, ignoring the phantom second parameter, per the spec's Design section. The implementation body dispatches on `isinstance` (typed with a real `Union[Identity[S], Const[S, A]]`, not `Any`) rather than delegating to a shared method, since neither `Identity` nor `Const` nominally implements `Semigroup` — see the spec's Design section correction note. Law test via the T-021 helper. Update `docs/HOWTO.md`'s `Const` section with a short `mappend` addition.

### T-024: `Reader[R, A]` `mappend` support

**Status:** Closed
**Depends on:** T-022

Add the `Reader[R, S] -> Reader[R, S] -> Reader[R, S]` overload to the free `mappend` function: pointwise combination, `(f mappend g)(r) = f(r) mappend g(r)`, per the spec's Design section. Law test via the T-021 helper with the environment-sampling `equal` comparator (same pattern as `Reader`'s Functor/Apply law tests). Update `docs/HOWTO.md`'s `Reader` section with a short `mappend` addition.

## Semigroup instances

Spec: [`docs/specs/semigroup-instances.md`](docs/specs/semigroup-instances.md)

### T-025: `Sum[A]` Semigroup instance

**Status:** Closed
**Depends on:** T-020

New type: `src/ekans/sum.py`, `Sum[A]` with a dedicated `SupportsAdd` `Protocol` (self-typed via its own `TypeVar`, not the outer `A`) bounding `A`. Nominally inherits `Semigroup` directly -- unlike `Identity`/`Const`/`Reader`, no conditional-instance problem here. `Functional`-based frozen dataclass, type-safe `__eq__`/`__hash__` per the Equality convention. Law test via `tests/semigroup_laws.py`'s `assert_semigroup_law`, applied directly since `Sum` is a nominal instance. Real `docs/HOWTO.md` `Sum` section.

### T-026: `Product[M]` Semigroup instance

**Status:** Closed
**Depends on:** T-020

Same shape as T-025 with a `SupportsMul` `Protocol` (`__mul__`) instead of `SupportsAdd`. `src/ekans/product.py`. Law test via `assert_semigroup_law`. Real `docs/HOWTO.md` `Product` section.

### T-027: `All` Semigroup instance

**Status:** Closed
**Depends on:** T-020

New type: `src/ekans/all.py`, `All` fixed to `bool` (not generic), `mappend` is boolean AND, matching Haskell's `newtype All = All Bool` exactly. `Functional`-based frozen dataclass, type-safe `__eq__`/`__hash__`. Law test via `assert_semigroup_law`. Real `docs/HOWTO.md` `All` section.

### T-028: `liftA2` free function

**Status:** Closed
**Depends on:** T-016 (Applicative ABC + law helper)

Add `liftA2` to `src/ekans/applicative.py`: `@overload`-per-concrete-type (`Identity`, `Reader`) plus the loose `Applicative[A]`/`Applicative[B]` fallback, matching `ap`'s shape in `apply.py` -- per the spec's Design section correction, a single fully-generic version silently loses precision (`reveal_type` gives `Applicative[int]`, not `Identity[int]`), the same failure mode that got `Pointed.point`'s free-function form rejected earlier; the overload set fixes this. Example-based tests per overload, plus a `reveal_type` precision probe (deleted after use). Short `docs/HOWTO.md` addition to the existing `Applicative` section.

### T-029: `Ap[S]` Semigroup instance

**Status:** Closed
**Depends on:** T-020, T-028

New type: `src/ekans/ap.py`, `Ap[S]` fixed to wrap `Identity[S]` (not generic over an arbitrary Applicative `F` -- Python has no higher-kinded types, verified in Phase 1: `Generic[F, A]` with a field typed `F[A]` where `F` is a bare `TypeVar` is a hard mypy error). `mappend` is a direct transcription of Haskell's `mappend (Ap x) (Ap y) = Ap (liftA2 mappend x y)`, built on T-028's `liftA2`. `Functional`-based frozen dataclass, type-safe `__eq__`/`__hash__`. Law test via `assert_semigroup_law`, plus a Hypothesis-checked associativity confirmation matching Phase 1's verification. Real `docs/HOWTO.md` `Ap` section, explaining the higher-kinded-types limitation plainly.

## Extractable

Spec: [`docs/specs/extractable.md`](docs/specs/extractable.md)

### T-030: Extractable ABC

**Status:** Closed

Add `src/ekans/extractable.py` with the `Extractable[A_co](Functional, Generic[A_co])` abstract class per the spec: covariant type parameter, abstract `extract` method, no override narrowing needed anywhere (verified in Phase 1 -- return-type-only narrowing on an instance method doesn't trigger `[override]`, same category of finding as `Semigroup.mappend`'s `typing.Self`). Includes the real `docs/HOWTO.md` `Extractable` section (new -- no prior stub existed for this, since it wasn't part of the originally planned hierarchy). `CLAUDE.md`'s Type hierarchy gets the new "Comonad-based structures" branch (`Extractable`, plus `Extend`/`Comonad` as stubs) in this same commit.

### T-031: Identity implements Extractable

**Status:** Closed
**Depends on:** T-030

Retrofit `Identity[A]` to also inherit `Extractable[A]` and implement `extract` (returns `self.value`). Verified via Phase 1 that this composes with `Applicative[A]` in the MRO with no conflict. Example test plus a `reveal_type` precision probe (deleted after use). Update `docs/HOWTO.md`'s `Identity` section with a short `extract` addition.

**Amended during T-033:** added a Hypothesis-checked test of `extract(point(a)) == a` -- a real law connecting `Pointed` and `Extractable` when a type implements both (only `Identity` does, of the six types in this round). See the spec's Testing strategy section correction note.

### T-032: Sum implements Extractable

**Status:** Closed
**Depends on:** T-030

Retrofit `Sum[A]` to inherit `Extractable[A]`, `extract` returns `self.value`. Example test. Update `docs/HOWTO.md`'s `Sum` section with a short `extract` addition.

### T-033: Product implements Extractable

**Status:** Closed
**Depends on:** T-030

Retrofit `Product[M]` to inherit `Extractable[M]`, `extract` returns `self.value`. Example test. Update `docs/HOWTO.md`'s `Product` section with a short `extract` addition.

### T-034: All implements Extractable

**Status:** Closed
**Depends on:** T-030

Retrofit `All` to inherit `Extractable[bool]`, `extract` returns `self.value`. Example test. Update `docs/HOWTO.md`'s `All` section with a short `extract` addition.

### T-035: Const implements Extractable

**Status:** Closed
**Depends on:** T-030

Retrofit `Const[A, B]` to also inherit `Extractable[A]` alongside its existing `Functor[B]`, `extract` returns `self.value` (the held `A`, not the phantom `B`). Verified in Phase 1 that this two-different-type-parameter composition type-checks cleanly. Example test plus a `reveal_type` precision probe. Update `docs/HOWTO.md`'s `Const` section with a short `extract` addition.

### T-036: Ap implements Extractable

**Status:** Closed
**Depends on:** T-030, T-031 (Ap's `extract` delegates to Identity's)

Retrofit `Ap[S]` to inherit `Extractable[S]`, `extract` returns `self.value.extract()` -- fully unwrapping through the wrapped `Identity[S]` to `S` directly, per the spec's Design section (not a shallow `Identity[S]` return). Example test plus a `reveal_type` precision probe confirming the full unwrap. Update `docs/HOWTO.md`'s `Ap` section with a short `extract` addition.

## Monoid

Spec: [`docs/specs/monoid.md`](docs/specs/monoid.md)

### T-037: Monoid ABC

**Status:** Closed
**Depends on:** T-020 (Semigroup ABC)

Add `src/ekans/monoid.py` with `Monoid(Semigroup)` per the spec: abstract `mempty(cls) -> Self` classmethod, nullary, no `Type[X]` argument at the ABC level (the erasure workaround only applies to types that hit the wall -- `Monoid` itself states the honest, correct Haskell-faithful contract). Includes the real `docs/HOWTO.md` `Monoid` section, including the erasure-wall story.

### T-038: Monoid law-checking helper

**Status:** Closed
**Depends on:** T-037

`tests/monoid_laws.py`: `assert_monoid_law(make, mempty, values, equal=None)` -- left/right identity, extending `assert_semigroup_law`'s pattern per the spec's Testing strategy. T-039 is its first caller.

### T-039: All implements Monoid

**Status:** Closed
**Depends on:** T-037, T-038

Retrofit `All` to nominally inherit `Monoid` (no erasure problem -- `All` isn't generic). `mempty(cls) -> All` returns `All(value=True)`, the identity for AND. Law test via T-038's helper. Cross-Product audit test: `All.mempty().extract() == True` (Monoid/Extractable). Update `docs/HOWTO.md`'s `All` section.

### T-040: Sum's mempty classmethod

**Status:** Closed
**Depends on:** T-037

Add `Sum.mempty(cls, value_type: Type[X])` per the spec's Design section: a new `SupportsZero` protocol (extending `SupportsAdd`) plus a hardcoded `int`/`float` registry, as a 3-variant `@overload` set. Does **not** override `Monoid.mempty` -- `Sum` does not nominally inherit `Monoid` (verified `[override]` LSP violation otherwise). Tests: `int`/`float`/custom-`SupportsZero`-type construction, genuine rejection of a type with neither, left/right identity against `.mappend()` directly (not via the T-038 helper, since `Sum` isn't nominally `Monoid`), plus `reveal_type` precision probes for all three positive cases. Cross-Product audit test: `Sum.mempty(int).extract() == 0`. Update `docs/HOWTO.md`'s `Sum` section.

### T-041: Product's mempty classmethod

**Status:** Closed
**Depends on:** T-037

Same shape as T-040 with a `SupportsOne` protocol (extending `SupportsMul`) and an `int`/`float` registry mapping to `1`/`1.0`. Update `docs/HOWTO.md`'s `Product` section.

### T-042: Ap's mempty classmethod

**Status:** Closed
**Depends on:** T-037, T-030 (Extractable, for the cross-product test), T-036 (Ap implements Extractable)

Add `Ap.mempty(cls, value_type: Type[S])` where `S: Monoid`, returning `Ap(value=Identity(value=value_type.mempty()))`. Does not override `Monoid.mempty` -- same non-nominal reasoning as T-040/T-041. Tests: construction, left/right identity against `.mappend()` directly, `reveal_type` precision probe. Cross-Product audit test: `Ap.mempty(Box).extract() == Box.mempty()`. Update `docs/HOWTO.md`'s `Ap` section.

### T-043: Identity's mempty classmethod

**Status:** Closed
**Depends on:** T-037

Add `Identity.mempty(cls, value_type: Type[S])` where `S: Monoid` (a fresh method-scoped `TypeVar`, independent of `Identity`'s own `A`), returning `Identity(value=value_type.mempty())`. Verified in Phase 1 this works as a classmethod directly on `Identity` -- no free function needed, unlike `mappend`, since a classmethod's fresh `TypeVar` doesn't contaminate every `Identity[A]` instance the way a nominal instance method would have. Tests: construction, left/right identity, genuine rejection of a non-`Monoid` `value_type` (e.g. `Identity.mempty(str)`), `reveal_type` precision probe. Update `docs/HOWTO.md`'s `Identity` section.

### T-044: Const's mempty classmethod

**Status:** Closed
**Depends on:** T-037

Same shape as T-043: `Const.mempty(cls, value_type: Type[S]) -> Const[S, B]`, `B` freely inferred from context, unrelated to `S`. Verified in Phase 1. Update `docs/HOWTO.md`'s `Const` section.

### T-045: Reader's mempty classmethod

**Status:** Closed
**Depends on:** T-037

Same shape as T-043/T-044: `Reader.mempty(cls, value_type: Type[S]) -> Reader[R, S]`, pointwise (`Reader(run=lambda r: value_type.mempty())`, ignoring the environment entirely -- same pattern as `Reader.point`/`const`), `R` freely inferred. Verified in Phase 1. Update `docs/HOWTO.md`'s `Reader` section.

## Bind

Spec: [`docs/specs/bind.md`](docs/specs/bind.md)

### T-046: Bind ABC + free `bind` function

**Status:** Closed
**Depends on:** T-012 (Apply ABC)

Add `src/ekans/bind.py` with `Bind[A_co](Apply[A_co], Generic[A_co])` per the spec: abstract `bind` method, no `fmap`/`ap` re-declaration needed (verified in Phase 1 -- `Bind`'s law only chains `.bind()`, unlike `Applicative`'s chained `.fmap()`/`.ap()`). Free `bind(f, x)` function as a single plain-typed function for now (no `Identity`/`Reader` overload yet, matching `fmap`'s T-001/`ap`'s T-012 precedent). Includes the real `docs/HOWTO.md` `Bind` section, including the `Const` exclusion explained plainly.

### T-047: Bind associativity law-checking helper

**Status:** Closed
**Depends on:** T-046

`tests/bind_laws.py`: `assert_bind_law(make, values, equal=None)` -- associativity, generated functions via `st.functions(like=...)` since `f`/`g` return wrapped values (closer to `apply_laws.py`'s shape than `semigroup_laws.py`'s). T-048/T-049 are its callers.

### T-048: Identity implements Bind

**Status:** Closed
**Depends on:** T-046, T-047

Retrofit `Identity[A]` to also inherit `Bind[A]` and implement `bind` (returns `f(self.value)`). Add its overload to the free `bind` function. Law test via T-047's helper, plus a concrete example test. Cross-Product audit test: `m.bind(f).extract() == f(m.extract()).extract()` (Bind/Extractable). Update `docs/HOWTO.md`'s `Identity` section.

**Amended during T-048:** found and documented a real precision gap in the free `bind` function -- `bind(f, x)` silently degrades to `Any` when `f` is a bare, unannotated lambda (mypy can't infer the lambda's parameter type from `x`, which comes second positionally). The method form (`x.bind(f)`) doesn't have this problem. Not a bug in `Identity`'s own instance -- documented as a known limitation of the free function's argument order in the spec's Design section correction note.

### T-049: Reader implements Bind

**Status:** Closed
**Depends on:** T-046, T-047

Retrofit `Reader[R, A]` to also inherit `Bind[A]` and implement `bind` (`Reader(run=lambda r: f(self.run(r)).run(r))`, threading the environment through both `self` and the result of `f`). Add its overload to the free `bind` function. Law test via T-047's helper with the environment-sampling `equal` comparator (same pattern as `Reader`'s other law tests). Update `docs/HOWTO.md`'s `Reader` section.

## Monad

Spec: [`docs/specs/monad.md`](docs/specs/monad.md)

### T-050: Monad ABC

**Status:** Closed
**Depends on:** T-015 (Applicative ABC), T-046 (Bind ABC)

Add `src/ekans/monad.py` with `Monad[A_co](Applicative[A_co], Bind[A_co], Generic[A_co])` per the spec: pure composition. Verified in Phase 1 that the MRO resolves cleanly despite `Applicative` and `Bind` both independently reaching `Apply`. Includes the real `docs/HOWTO.md` `Monad` section.

**Amended during T-051:** the initial "no `bind` re-declaration needed" finding was verified only against a concrete subclass's own chain, not the *abstract* `Monad[A]` handle the law helper actually needs. Confirmed directly that a `.bind()` call on a bare `Monad[A]`-typed value resolves to the inherited `Bind[B]`, not `Monad[B]`, without a re-declaration -- same gap `Applicative.ap`'s own re-declaration from `Apply` already exists to close. Fixed by adding `Monad`'s own `bind` re-declaration (narrowing `Bind[B]` to `Monad[B]`, `# type: ignore[override]`). See the spec's Design section correction note.

### T-051: Monad law-checking helper

**Status:** Closed
**Depends on:** T-050

`tests/monad_laws.py`: `assert_monad_law(point, values, equal=None)` -- left identity (`point(a).bind(f) == f(a)`) and right identity (`m.bind(point) == m`), expressed via `point` alone, same shape as `applicative_laws.py`. Associativity is not retested (already covered by `Bind`'s own law). T-052/T-053 are its callers.

### T-052: Identity implements Monad

**Status:** Closed
**Depends on:** T-050, T-051

Retrofit `Identity[A]`'s base classes to `Monad[A]` + `Extractable[A]` only, dropping the now-redundant explicit `Applicative[A]`/`Bind[A]` (MRO conflict otherwise -- same lesson as T-017/T-019). No new methods -- everything already implemented. Law test via T-051's helper. Update `docs/HOWTO.md`'s `Identity` section with a short note.

### T-053: Reader implements Monad

**Status:** Closed
**Depends on:** T-050, T-051

Retrofit `Reader[R, A]`'s base classes to `Monad[A]` only, dropping the now-redundant explicit `Applicative[A]`/`Bind[A]`. No new methods. Law test via T-051's helper with the environment-sampling `equal` comparator (same pattern as `Reader`'s other law tests). Update `docs/HOWTO.md`'s `Reader` section with a short note.

## do

Spec: [`docs/specs/do.md`](docs/specs/do.md)

### T-054: `@do` decorator

**Status:** Closed

Add `src/ekans/do.py`'s `do` decorator per the spec: `ParamSpec`-forwarding trampoline over `Callable[P, Generator[Monad[T], Any, Monad[U]]]`, calling `.bind`/`.send` to flatten the generator into a single `Monad[U]`. Both `except StopIteration as e: return e.value` lines carry `# type: ignore[no-any-return]` with the one-sentence justification from the spec (`StopIteration.value` is typeshed-`Any`; no narrower type is derivable at that boundary).

Tests (`tests/test_do.py`): Hypothesis-driven equivalence tests asserting a `@do`-decorated computation over `Identity` and over `Reader` produces the same result as the same computation written as an explicit manual `.bind()` chain. A short-circuit test using a local, test-file-only `_Just`/`_Nothing` double (matching `test_monad.py`'s illustrative-type convention, not exported) confirming a do-block halts at the first `_Nothing()` and never executes code after that `yield`. Every do-block in the test file follows the spec's required style: an explicit outer `Generator[Monad[T], Any, Monad[U]]` return annotation, and an explicit local type annotation on every `yield` assignment.

Documentation: new `docs/HOWTO.md` section introducing `@do`, written in the required style, stating the `Any`-wall limitation and its mitigation plainly (same honest treatment as the Monoid erasure wall / `Bind`'s free-function precision gap elsewhere in the doc), with runnable `Identity` and `Reader` examples and a short conceptual paragraph on short-circuiting.

## Const Applicative

Spec: [`docs/specs/const-applicative.md`](docs/specs/const-applicative.md)

### T-055: `Const.point` classmethod + `ap` overload

**Status:** Closed

Add `Const.point(value_type: Type[S], value: B) -> Const[S, B]` (`S` bound to `Monoid`) as a classmethod directly on `Const`, mirroring `Const.mempty`'s exact shape and reasoning -- `value` is accepted and unconditionally discarded, same precedent as `Const.fmap`'s unused `f`. Add a new `@overload` (`S` bound to `Semigroup`) to the existing free `ap` function in `apply.py`: `ap(f: Const[S, Callable[[A], B]], x: Const[S, A]) -> Const[S, B]`, dispatching to `Const(value=x.value.mappend(f.value))`. No nominal `Pointed[B]`/`Apply[B]` inheritance -- proven impossible in the spec's Design section, not merely skipped.

Tests (`tests/test_const.py`): construction and precision for `Const.point`, including an explicit assertion that the passed `value` has no effect on the result. Construction and precision for the `ap` overload, plus a genuine `mypy`-level rejection test for a non-`Semigroup` `A` (mirroring `test_mappend_rejects_mismatched_container_types_at_runtime`'s style). The `extract(ap(f, x)) == x.extract().mappend(f.extract())` law from the spec's Cross-Product audit, as a Hypothesis property test. Explicitly no `assert_applicative_law`/`assert_apply_law` usage against `Const` (see the spec's Cross-Product audit for why).

Documentation: short addition to `docs/HOWTO.md`'s existing `Const` section covering `point`/`ap`, stated with the same plain-limitation honesty as the existing `Semigroup`/`Monoid` framing there -- `Const` still never "is" an `Applicative`.

### T-056: `liftA2` overload for `Const`

**Status:** Closed
**Depends on:** T-055

Add a new `@overload` (`S` bound to `Semigroup`) to the existing free `liftA2` function in `applicative.py`: `liftA2(f: Callable[[A, B], C], fa: Const[S, A], fb: Const[S, B]) -> Const[S, C]`, dispatching to `Const(value=fa.value.mappend(fb.value))`. Example-based tests plus a precision (`reveal_type`) probe, deleted after use. Short `docs/HOWTO.md` addition alongside T-055's.

## Maybe

Spec: [`docs/specs/maybe.md`](docs/specs/maybe.md)

### T-057: `Maybe`/`Just`/`Nothing` core type

**Status:** Closed

New file `src/ekans/maybe.py`: abstract `Maybe(Monad[A], Generic[A])` plus concrete `Just[A]`/`Nothing[A]`. Per the spec's key finding: `Maybe`'s own abstract `fmap`/`ap`/`bind` re-declarations return `Union[Just[B], Nothing[B]]`, not the abstract `Maybe[B]` -- required for real `match`/`case` exhaustiveness and field narrowing under `mypy --strict` (verified in Phase 1: the naive `Maybe[B]`-returning version produces a genuine `Missing return statement` error on an exhaustive two-case `match`, plus `Any`-typed narrowing inside `case Just(value=v):`). `point` is defined once, concretely, directly on `Maybe` (not abstract, not re-implemented per variant) -- `Maybe.point(value) = Just(value=value)`, matching Haskell's `pure = Just`, with no variant-specific behavior. `Just`/`Nothing` both frozen dataclasses, type-safe `__eq__`/`__hash__` per the Equality convention. `Nothing` is Ekans' first genuinely zero-field concrete type. No `Extractable` instance -- excluded on the merits (no total `extract() -> A` possible for `Nothing`), matching `Reader`/`Star`'s existing exclusion style.

Add `Maybe`/`Just`/`Nothing` overloads to the existing free `fmap` (`functor.py`), `ap` (`apply.py`), `bind` (`bind.py`) functions.

Tests (`tests/test_maybe.py`): construction, equality/hash (including cross-variant inequality), immutability. A `match`/`case` exhaustiveness demonstration with no fallback `case _:`, verified it type-checks under `mypy tests --strict`. Law tests via the existing helpers (`assert_functor_laws`, `assert_apply_law`, `assert_applicative_law`, `assert_bind_law`, `assert_monad_law`) called against `Just` -- no new law infrastructure needed, `Maybe` is a genuinely nominal instance of the whole hierarchy. Explicit, separate example-based tests confirming `Nothing.fmap`/`.ap`/`.bind` never call their argument function (via a call-log/side-effect check) -- per the spec's Cross-Product audit, the standard laws hold *vacuously* for `Nothing` and don't actually exercise this guarantee. A documented example showing bare `Nothing()` decaying to `Nothing[Never]` without context, contrasted with a bracketed/contextual construction resolving precisely.

Documentation: new `docs/HOWTO.md` `Maybe` section covering the sealed shape, a runnable `match`/`case` example, the `Union[Just[B], Nothing[B]]`-vs-`Maybe[B]` finding stated plainly, and the bare-`Nothing()` gap with its mitigation.

### T-058: `Maybe`'s conditional `Semigroup`/`Monoid`

**Status:** Closed
**Depends on:** T-057

Add a `Maybe` overload to the existing shared free `mappend` (`semigroup.py`), `S` bound to `Semigroup`: `Nothing <> x = x`, `x <> Nothing = x`, `Just a <> Just b = Just (a.mappend(b))`, via `match`/`case`. Add a `mempty(value_type: Type[S]) -> Maybe[S]` classmethod directly on `Maybe`, alongside `point` -- per the spec's Design section, `S` is bound to `Semigroup`, **not** `Monoid` (a real, verified difference from `Identity`/`Const`/`Reader`'s `mempty`): `Maybe.mempty` never calls `value_type.mempty()` at all, since `Nothing()` is unconditionally a valid identity regardless of `A`; `value_type` exists purely to pin the static type parameter.

Tests: `mappend`/`mempty` example and property tests (associativity, left/right identity) mirroring `Identity`/`Const`/`Reader`'s existing shape, plus a test using a type that's a `Semigroup` but deliberately *not* a `Monoid`, confirming `Maybe.mempty` still works with it (the concrete verification of the spec's central `Semigroup`-not-`Monoid` claim).

Documentation: `docs/HOWTO.md` addition to the `Maybe` section explaining the conditional instance and why `mempty` only needs `Semigroup`.

### T-059: Real `Maybe`-based short-circuit regression test for `@do`

**Status:** Closed
**Depends on:** T-057

Per `docs/specs/do.md`'s own flagged follow-up: add one additional test to `tests/test_do.py` using real `Just`/`Nothing` (not the existing local `_Just`/`_Nothing` double, which stays -- the do-notation guarantee is generic over any `Monad`, not `Maybe`-specific) confirming a `@do` block halts at the first `Nothing` and never resumes past it. Short addition to `docs/HOWTO.md`'s existing `@do` section noting the real example now exists.

## Either

Spec: [`docs/specs/either.md`](docs/specs/either.md)

### T-060: `Either`/`Left`/`Right` core type

**Status:** Closed

New file `src/ekans/either.py`: abstract `Either(Monad[R], Generic[L, R])` plus concrete `Left[L, R]`/`Right[L, R]`, biased `Right` (matching Haskell's `Functor`/`Monad` convention). Per the spec: `Either`'s own abstract `fmap`/`ap`/`bind`/`point` re-declarations return `Union[Left[L, R2], Right[L, R2]]`, not the abstract `Either[L, R2]` -- same `match`/`case` exhaustiveness reasoning verified fresh for `Either` in Phase 1, not assumed from `Maybe`. `point` defined once, concretely, directly on `Either` (`Either.point(value) = Right(value=value)`, matching Haskell's `pure = Right`). `Left`'s `fmap`/`ap`/`bind` are no-op re-tags of `R`, structurally identical to `Const.fmap`'s re-tagging -- but unlike `Const`, `Left` gets a real, precise, nominal `Bind`/`Monad` instance (verified in Phase 1: `Left(value=...).bind(...)` resolves precisely, no `Never`, because `Right` -- `Left`'s sealed-hierarchy sibling -- keeps `R` real and inferable across the pair, the way `Just` does for `Nothing`'s `A`). Both `Left`/`Right` frozen dataclasses, type-safe `__eq__`/`__hash__` checking both type parameters independently (`Const`'s existing two-parameter Equality convention). No `Extractable` instance (excluded, same reasoning as `Maybe`'s `Nothing`) and no `Semigroup`/`Monoid` instance (excluded structurally -- no canonical Haskell base instance to port, unlike `Maybe`'s).

Add `Either`/`Left`/`Right` overloads to the existing free `fmap` (`functor.py`), `ap` (`apply.py`), `bind` (`bind.py`) functions.

Tests (`tests/test_either.py`): construction, equality/hash (both type parameters checked independently, including confirming `Left(...) != Right(...)` even with equal-comparing held values), immutability. A `match`/`case` exhaustiveness demonstration mirroring `test_maybe.py`'s `_describe` helper. Law tests via the existing helpers (`assert_functor_laws`, `assert_apply_law`, `assert_applicative_law`, `assert_bind_law`, `assert_monad_law`) called against `Right`. Explicit, separate example-based tests confirming `Left.fmap`/`.ap`/`.bind` never call their argument function. A test-only third `Either` subclass (mirroring `test_maybe.py`'s `_RogueMaybe`) proving `Right.ap`/`.bind`'s `case _: raise AssertionError` fallbacks are real safety nets. A documented example contrasting `Either`'s bare-construction behavior (a real `mypy` `[var-annotated]` error on an unannotated assignment) against `Maybe`'s silent `Nothing[Never]` decay.

Documentation: new `docs/HOWTO.md` `Either` section covering the sealed shape and `Right`-bias, a runnable `match`/`case` example, the `Union`-vs-abstract finding (may reference `Maybe`'s section for the shared reasoning), the better-behaved bare-construction contrast, and a short note on why `Semigroup`/`Monoid` don't appear here.

### T-061: Real `Either`-based short-circuit regression test for `@do`

**Status:** Closed
**Depends on:** T-060

Per `docs/specs/do.md`'s original follow-up (which named both `Maybe` and `Either`): add one additional test to `tests/test_do.py` using real `Left`/`Right` confirming a `@do` block halts at the first `Left` and never resumes past it. Short addition to `docs/HOWTO.md`'s existing `@do` section noting the second real example now exists.

## Tuple2

Spec: [`docs/specs/tuple2.md`](docs/specs/tuple2.md)

### T-062: `Tuple2` core type

**Status:** Closed

New file `src/ekans/tuple2.py`: `Tuple2[A, B]` (`first: A`, `second: B`), nominal `Functor[B]` only (unconditional -- `fmap` never touches `A`). Nominal `Apply`/`Applicative`/`Bind` proven impossible (same wall `Const` hit, verified fresh: `"A" has no attribute "mappend"` on a naive attempt) -- so, per the spec's Design section, conditional/free-function-and-classmethod operations instead, mirroring `Const`'s established playbook exactly: `Tuple2.point(value_type: Type[S], value: B) -> Tuple2[S, B]` (`S` bound `Monoid`, classmethod alongside `Extractable`; unlike `Const.point`, `value` is genuinely used, not discarded -- `pure x = (mempty, x)`) plus new `Tuple2` overloads (`S` bound `Semigroup`) on the existing shared free `ap`/`liftA2`/`bind` functions, each doing real work (real function application on `second`, real `mappend` on `first`) -- not `Const`'s degenerate case, verified at runtime. Nominal `Extractable[B]` (`extract() -> B`, matching `Functor`'s bias) -- unlike `Const`, all three standard cross-class laws hold in their full, undiluted form (`Pointed`/`Extractable` round-trip, `Apply`/`Extractable` commutation, `Bind`/`Extractable`), verified directly rather than assumed. Type-safe `__eq__`/`__hash__` checking both type parameters independently (`Const`'s two-parameter Equality convention).

Tests (`tests/test_tuple2.py`): construction, equality/hash, immutability. `assert_functor_laws` applies directly (nominal `Functor`). No `assert_apply_law`/`assert_applicative_law`/`assert_bind_law` (non-nominal, same reasoning as `Const`'s testing strategy). Direct Hypothesis property tests for the `Applicative` laws (identity, homomorphism, interchange, composition) against the free `point`/`ap` -- following through on `docs/specs/const-applicative.md`'s own flagged "worth a second look" open question, meaningful here since `Tuple2`'s `ap` does real work. The three `Extractable` cross-product laws as direct property tests.

Documentation: new `docs/HOWTO.md` `Tuple2` section -- the nominal-`Functor`-but-conditional-everything-else shape, contrasted directly against `Const` (real capability vs. `Const`'s degenerate case), and the three `Extractable` laws holding in full.

### T-063: `Tuple2`'s own pointwise `Semigroup`/`Monoid`

**Status:** Closed
**Depends on:** T-062

Add a `Tuple2` overload to the existing shared free `mappend` (`semigroup.py`) needing **two independent bounds simultaneously** (`SA`/`SB`, both bound `Semigroup`) -- a genuinely new pattern, not yet built anywhere in this codebase: `mappend(a, b) = Tuple2(first=a.first.mappend(b.first), second=a.second.mappend(b.second))`. Add a `mempty(a_type: Type[MA], b_type: Type[MB]) -> Tuple2[MA, MB]` classmethod directly on `Tuple2`, alongside `point` (`MA`/`MB` independently bound `Monoid`).

Tests: `mappend`/`mempty` example and property tests (associativity, left/right identity) mirroring the existing conditional-instance shape, plus a genuine `mypy`-level rejection test for a pair where only *one* side satisfies the `Monoid` bound (the concrete verification that the two bounds are independently enforced, not just nominally declared). The `mappend(x, y).extract() == x.extract().mappend(y.extract())` law from the spec's Cross-Product audit, as a property test.

Documentation: `docs/HOWTO.md` addition to the `Tuple2` section explaining the two-independent-bound pattern, contrasted with every prior conditional instance's single bound.

## Foldable

Spec: [`docs/specs/foldable.md`](docs/specs/foldable.md)

### T-064: `Foldable` Protocol, `FoldableABC`, and the core folds

**Status:** Closed

New file `src/ekans/foldable.py`: `Foldable(Protocol[A_co])` requiring only `__iter__` (`A_co` covariant -- verified an invariant TypeVar is a real `mypy --strict` error here), `@runtime_checkable`. `FoldableABC(Generic[A_co])`: override hooks for `foldr` and `length`/`null` only (`NotImplementedError` sentinel = "not overridden"), per the spec's Design section -- not one hook per derived function. Core folds: `foldr(f, initial, xs)` (a plain accumulator loop over `reversed(list(xs))` -- **not** a chain of thunks; per the spec, a literal "trampoline" implementation was tried first and is a genuine bug, verified to blow a deliberately-lowered recursion limit at 100k elements), `foldl(f, initial, xs)` (trivially stack-safe, no reversal needed), `foldMap(monoid_type, f, xs)` and `fold(monoid_type, xs)` (`Type[M]` argument required, same erasure reason as `Sum.mempty()`), `foldr1`/`foldl1` (seedless, raise on empty), `fold1(xs)` (`Semigroup`-only seedless fold, no `Type[M]` needed, raises on empty). Free functions check `isinstance(x, FoldableABC)` and fall back to the generic default on the sentinel.

Also lands the `CLAUDE.md` "Why Foldable is a Protocol" correction: the trampoline description there is wrong as written (verified in Phase 1, not assumed) and gets fixed in the same commit.

Tests (`tests/test_foldable.py`): structural satisfaction (list/tuple/generator/custom `__iter__`-only type, static and runtime `isinstance`, plus a genuine rejection for a non-iterable). **A real stack-safety regression test**: fold tens of thousands of elements with the recursion limit deliberately lowered inside the test, asserting no `RecursionError` -- the test that would have caught the original broken attempt. `FoldableABC` override dispatch proven with a test-only type whose overridden `foldr` is observably different from the generic default. `foldMap`/`fold`/`fold1` tested against real `Monoid`/`Semigroup` test doubles (empty and non-empty where applicable). `foldr1`/`foldl1`/`fold1` tested for the documented `ValueError` on empty input.

Documentation: new `docs/HOWTO.md` Part 3 section (Foldable sits outside both the abstract `Functional` hierarchy and the concrete-type gallery) covering the Protocol's structural nature, the corrected stack-safety story told plainly (including the wrong first attempt), and the `FoldableABC` mechanism.

### T-065: List-shape, boolean, and search derived functions

**Status:** Open
**Depends on:** T-064

Add to `src/ekans/foldable.py`: `toList(xs)`, `null(xs)`, `length(xs)` (using `FoldableABC`'s override where present), `concat(xs)` (`Foldable[Iterable[A]] -> List[A]`), `concatMap(f, xs)`. `and_(xs)`/`or_(xs)` (named with a trailing underscore per review -- `and`/`or` are Python keywords, can't be spelled that way at all; matches the stdlib `operator` module's own convention for the identical problem). `any(predicate, xs)`, `all(predicate, xs)`, `elem(x, xs)`, `notElem(x, xs)` -- kept at their exact Haskell/Python names per review (unlike `map`/`fmap`, no real forced collision here; `Sum`/`Product` already exist as distinct capitalized names). `find(predicate, xs) -> Union[Just[A], Nothing[A]]` -- Ekans's own `Maybe`, matching Haskell's own `find :: (a -> Bool) -> t a -> Maybe a` signature directly, verified precise via `reveal_type` and short-circuiting verified via a call-log double.

Tests: example-based per function, plus Hypothesis property tests using Python's own builtins (`len`, `any`, `all`) as the oracle wherever the semantics line up. `find`'s short-circuit and precise return type tested explicitly.

Documentation: addition to the `Foldable` HOWTO section covering this function group.

### T-066: Numeric and ordering derived functions

**Status:** Open
**Depends on:** T-064

Add to `src/ekans/foldable.py`: `sum(xs)`/`product(xs)`, reusing the existing `SupportsAdd`/`SupportsMul` `Protocol`s from `sum.py`/`product.py` directly (verified importable, no circular-import issue). New `SupportsLt` `Protocol` (self-typed `__lt__`, matching `SupportsAdd`/`SupportsMul`'s shape) for `maximum(xs)`/`minimum(xs)`, both raising `ValueError` on empty input (matching Python's own `max()`/`min()` *and* Haskell's own partial `maximum`/`minimum` -- two independent, already-established reasons, not a new one invented here). `maximumBy(key, xs)`/`minimumBy(key, xs)` -- deliberately a `key`-function per review, not Haskell's raw three-way comparator, matching Python's own `max(iterable, key=...)` idiom; recorded as an intentional divergence.

Tests: example-based per function, plus Hypothesis property tests using Python's own `sum`/`max`/`min` builtins as the oracle. Empty-input `ValueError` tested for `maximum`/`minimum`.

Documentation: addition to the `Foldable` HOWTO section covering this function group; replaces the `Foldable` stub entry in "Coming soon" with a link to the real section once all three tickets are closed.
