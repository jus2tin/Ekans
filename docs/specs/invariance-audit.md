# Retroactive Cross-Class Invariance Audit

**Status:** Complete
**Scope:** All type classes and concrete types implemented as of 2026-09-02 (`Functional`, `Functor`, `Pointed`, `Apply`, `Applicative`, `Semigroup`, `Extractable`; `Identity`, `Const`, `Reader`, `Sum`, `Product`, `All`, `Ap`).

## Why this exists

The Compositional Invariance Matrix rule (added to `CLAUDE.md`'s Implementation Protocol) requires every future round to audit a new capability's interaction with every type class already compatible with it. This document is the one-time retroactive pass over everything that existed *before* that rule was codified, so the codebase isn't carrying undocumented debt going forward. Every finding below is either a tested law or a documented non-law — nothing was left implicit.

"Compatible" here means: an existing pair of type classes with at least one concrete type implementing both. Pairs with no shared concrete instance aren't listed (there's nothing to test).

## Inventory

### Verified laws (tested)

| Law | Types | Test | Formula |
|---|---|---|---|
| Pointed / Extractable round-trip | `Identity` | `test_identity.py::test_extract_after_point_is_identity` (pre-existing, added during the Extractable round) | `extract(point(a)) == a` |
| Functor / Extractable naturality | `Identity` | `test_identity.py::test_fmap_extract_naturality` | `w.fmap(f).extract() == f(w.extract())` |
| Apply / Extractable commutation | `Identity` | `test_identity.py::test_ap_extract_commutes` | `x.ap(f).extract() == f.extract()(x.extract())` |
| Semigroup / Extractable homomorphism (free `mappend`) | `Identity`, `Const` | `test_identity.py::test_mappend_extract_homomorphism`, `test_const.py::test_mappend_extract_homomorphism` | `mappend(x, y).extract() == x.extract().mappend(y.extract())` |
| Semigroup / Extractable homomorphism (nominal `mappend`) | `Ap` | `test_ap.py::test_mappend_extract_homomorphism` | `x.mappend(y).extract() == x.extract().mappend(y.extract())`, via `S`'s own `mappend` |
| Semigroup / Extractable homomorphism (operator form) | `Sum`, `Product`, `All` | `test_sum.py`/`test_product.py`/`test_all.py::test_mappend_extract_distributes_over_*` | `x.mappend(y).extract() == x.extract() <op> y.extract()` (`+`/`*`/`and`) |

Each law above was verified in three steps before being written into a formal test: (1) confirmed it holds via a direct Hypothesis check, (2) confirmed a deliberately broken instance gets caught by it (not a vacuous pass), (3) only then added as a permanent property test.

The **Applicative/Functor/Pointed consistency** requested for this audit is already fully covered by the existing law suites (`functor_laws.assert_functor_laws`, `apply_laws.assert_apply_law`, `applicative_laws.assert_applicative_law`), run against both `Identity` and `Reader` since their respective rounds — the four Applicative laws (identity, homomorphism, interchange, composition) *are* the Functor/Apply/Pointed consistency conditions; there was no gap to fill here, only confirmation that the existing suite still passes (it does — see Test results below).

### Documented non-laws (Proof Burden)

| Pair | Types where it would apply | Why no law holds |
|---|---|---|
| Functor / Extractable naturality | `Const[A, B]` | `fmap` operates on `B` (the phantom parameter); `extract` returns `A` (the held value). No single function `f` types both `w.fmap(f)` and `f(w.extract())` — verified directly: `mypy --strict` confirms `extract()` on `Const[int, str]` reveals `int` while `fmap` only ever transforms the `str` side. The naturality law as stated isn't just false for `Const`, it's not well-typed for `Const`. |
| Functor / Semigroup | `Identity`, `Const` (both `Functor` and conditionally `Semigroup`) | No general law connects `fmap` and `mappend`: `fmap(f, mappend(x, y)) == mappend(fmap(f, x), fmap(f, y))` would require `f` to itself be a semigroup homomorphism (`f(a).mappend(f(b)) == f(a.mappend(b))`), which isn't guaranteed for an arbitrary `f: A -> B`. Not a gap — a genuinely false general law, so no property test was written for it (writing one would either be vacuously scoped to homomorphism-only `f`, which isn't what `Functor`'s `fmap` promises, or would fail on `Hypothesis`-generated non-homomorphism functions). |
| Pointed / Semigroup | `Identity` (`Pointed`), none of `Sum`/`Product`/`All`/`Ap` are `Pointed` | No meaningful law without an identity element — that's exactly what `Monoid` adds. A `Semigroup`-only law connecting `point` to `mappend` would need something like `mappend(point(mempty), x) == x`, which requires `mempty`. Deferred until `Monoid` exists; noted here so it isn't forgotten when that round starts. |

`Reader`/`Star` were already excluded from `Extractable` itself (they wrap a function, not a single value) and `Proxy` (holds nothing at runtime) — both documented in `docs/specs/extractable.md`'s Design section at the time `Extractable` was built; this audit doesn't repeat that reasoning, only cross-references it.

## Test results

Full suite, run after all audit tests were added:

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 160 items

tests\test_all.py ............                                           [  7%]
tests\test_ap.py ............                                            [ 15%]
tests\test_applicative.py .......                                        [ 19%]
tests\test_applicative_laws.py ..                                        [ 20%]
tests\test_apply.py .......                                              [ 25%]
tests\test_apply_laws.py ..                                              [ 26%]
tests\test_const.py ...............                                      [ 35%]
tests\test_extractable.py .....                                          [ 38%]
tests\test_functional.py .....                                           [ 41%]
tests\test_functor.py ......                                             [ 45%]
tests\test_functor_laws.py ....                                          [ 48%]
tests\test_identity.py ...........................                       [ 65%]
tests\test_pointed.py .....                                              [ 68%]
tests\test_product.py .............                                      [ 76%]
tests\test_reader.py ..................                                  [ 87%]
tests\test_semigroup.py .....                                            [ 90%]
tests\test_semigroup_laws.py ..                                          [ 91%]
tests\test_sum.py .............                                         [100%]

TOTAL coverage: 100.00% (230/230 statements)
160 passed in 12.28s
```

Before this audit: 152 tests, all passing, 100% coverage. After: 160 tests (8 new cross-class law tests), all passing, 100% coverage — zero regressions. `mypy src tests --strict`, `black --check`, `isort --check`, and `flake8` all clean; no new `# type: ignore` was needed anywhere, since this audit added tests against already-typed existing APIs rather than new implementation.

## Implementation constraints

This document records findings only — it introduces no new production code, type class, or concrete type. Any future round that touches a type class or concrete type listed above should re-check this document's inventory for staleness before assuming its entries still hold.
