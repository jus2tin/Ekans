# Tickets

Lightweight, in-repo ticket tracking — no external issue tracker. One `##` section per ticket, self-contained, so this can later split into one-file-per-ticket if it ever grows past a comfortable single file (same pattern as `docs/HOWTO.md`).

**Lifecycle:** `Open` → `Closed`. A ticket closes when its Definition of Done is met — 100% coverage, `mypy --strict` clean, `black`/`isort`/`flake8` clean, TDD followed (test committed before implementation), and `docs/HOWTO.md` updated if the ticket adds a documented concept. Claude closes tickets itself once these are verifiably true, no separate sign-off required — see CLAUDE.md's Workflow section.

Each ticket references the spec it was derived from. No spec, no ticket.

## Functor

Spec: [`docs/specs/functor.md`](docs/specs/functor.md)

### T-001: Functor ABC

**Status:** Open

Add `src/ekans/functor.py` with the `Functor[A_co]` abstract class per the spec: covariant type parameter, abstract `fmap` method, plus the free `fmap` function (empty `@overload` set for now — overloads get added by T-003/T-004 as each concrete type lands). Includes the `docs/HOWTO.md` `Functor` section (concept + both laws in plain language + a runnable example), replacing the current stub.

### T-002: Functor law-checking test helper

**Status:** Open
**Depends on:** T-001

A reusable Hypothesis-based helper (in `tests/`, not part of the public package — no `docs/HOWTO.md` entry, this is test infrastructure) asserting the identity and composition laws from the spec, parameterized over a constructor, a values strategy, and two composable functions. T-003 and T-004 are its first two callers.

### T-003: Identity implements Functor

**Status:** Open
**Depends on:** T-001, T-002

Retrofit `Identity[A]` to inherit `Functor[A]` and implement `fmap`. Add its overload to the free `fmap` function. Law tests via the T-002 helper, plus a concrete example test. Update `docs/HOWTO.md`'s `Identity` section to replace the "Once Functor lands..." forward-reference with the real behavior.

### T-004: Const[A, B] concrete type + Functor instance

**Status:** Open
**Depends on:** T-001, T-002

New type: `src/ekans/const.py`, `Const[A, B]` (`data Const a b = Const a`), `Functional`-based frozen dataclass, `fmap` is a no-op re-tag. Type-safe `__eq__`/`__hash__` per the Equality convention, extended to two type parameters (invariant in both — confirm mypy rejects a mismatch on *either* parameter, not just one, per the spec's open question). Add its overload to the free `fmap` function. Law tests via the T-002 helper, plus example/equality tests. Replace `Const[A, B]`'s `docs/HOWTO.md` stub with a real section.
