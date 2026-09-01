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

**Status:** Open

Add `src/ekans/apply.py` with the `Apply[A_co]` abstract class per the spec: `Functor[A_co]` subclass, abstract `ap` method, plus the free `ap` function (function-first argument order) with its fallback `@overload` in place from the start, mirroring `fmap`'s pattern. Includes the real `docs/HOWTO.md` `Apply` section, replacing the current stub.

### T-013: Apply associativity law-checking helper

**Status:** Open
**Depends on:** T-012

`tests/apply_laws.py`: `assert_apply_law(make, values, equal=None)` per the spec's Testing strategy — generates `w`'s value plus two endofunctions via `hypothesis.strategies.functions()`, with a small typed `_compose` helper alongside it. T-014 is its first caller.

### T-014: Identity implements Apply

**Status:** Open
**Depends on:** T-012, T-013

Retrofit `Identity[A]` to also inherit `Apply[A]` (alongside its existing `Functor[A]`/`Pointed[A]`) and implement `ap`. Add its overload to the free `ap` function. Law test via the T-013 helper, plus a concrete example test. Update `docs/HOWTO.md`'s `Identity` section with a short `ap` addition.
