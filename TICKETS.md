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

**Status:** Open
**Depends on:** T-030

Retrofit `All` to inherit `Extractable[bool]`, `extract` returns `self.value`. Example test. Update `docs/HOWTO.md`'s `All` section with a short `extract` addition.

### T-035: Const implements Extractable

**Status:** Open
**Depends on:** T-030

Retrofit `Const[A, B]` to also inherit `Extractable[A]` alongside its existing `Functor[B]`, `extract` returns `self.value` (the held `A`, not the phantom `B`). Verified in Phase 1 that this two-different-type-parameter composition type-checks cleanly. Example test plus a `reveal_type` precision probe. Update `docs/HOWTO.md`'s `Const` section with a short `extract` addition.

### T-036: Ap implements Extractable

**Status:** Open
**Depends on:** T-030, T-031 (Ap's `extract` delegates to Identity's)

Retrofit `Ap[S]` to inherit `Extractable[S]`, `extract` returns `self.value.extract()` -- fully unwrapping through the wrapped `Identity[S]` to `S` directly, per the spec's Design section (not a shallow `Identity[S]` return). Example test plus a `reveal_type` precision probe confirming the full unwrap. Update `docs/HOWTO.md`'s `Ap` section with a short `extract` addition.
