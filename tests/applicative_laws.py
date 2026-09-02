"""Reusable Hypothesis-based Applicative law checks.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/applicative.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ekans.applicative import Applicative

A = TypeVar("A")


def _identity(a: A) -> A:
    return a


def _compose(g: Callable[[A], A]) -> Callable[[Callable[[A], A]], Callable[[A], A]]:
    """Typed stand-in for a composition-building lambda; same reasoning
    as `functor_laws.py`'s `_identity` and `apply_laws.py`'s `_compose`.
    """

    def _compose_with(f: Callable[[A], A]) -> Callable[[A], A]:
        def _composed(a: A) -> A:
            return g(f(a))

        return _composed

    return _compose_with


def assert_applicative_law(
    point: Callable[[A], Applicative[A]],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Applicative[A], Applicative[A]], bool]] = None,
) -> None:
    """Assert the Applicative identity, homomorphism, interchange, and
    composition laws for `point`.

    Args:
        point: The concrete type's own `point` classmethod (e.g.
            `Identity.point`) -- used to construct every wrapped value
            and wrapped function the laws need; no separate `make`.
        values: A Hypothesis strategy generating values to wrap.
        equal: How to compare two Applicative instances for the
            purpose of the laws below. Defaults to `==`. Same
            reasoning as `functor_laws.assert_functor_laws`'s `equal`.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    # `point` is typed Callable[[A], Applicative[A]] to wrap plain
    # values (per the approved signature) -- every law below also
    # reuses it to wrap *functions*, the same deliberate,
    # understood mismatch already documented in apply_laws.py's
    # assert_apply_law. Each such call gets an explicit annotation
    # correcting the type mypy would otherwise infer from `point`'s
    # declared (wrong-for-this-call) return type ([arg-type]).

    @given(values)
    def identity_law(value: A) -> None:
        v = point(value)
        id_wrapped: Applicative[Callable[[A], A]]
        id_wrapped = point(_identity)  # type: ignore[arg-type, assignment]
        assert eq(v.ap(id_wrapped), v)

    @given(values, st.functions(like=_identity, returns=values, pure=True))
    def homomorphism_law(value: A, f: Callable[[A], A]) -> None:
        f_wrapped: Applicative[Callable[[A], A]]
        f_wrapped = point(f)  # type: ignore[arg-type, assignment]
        assert eq(point(value).ap(f_wrapped), point(f(value)))

    @given(values, st.functions(like=_identity, returns=values, pure=True))
    def interchange_law(value: A, f: Callable[[A], A]) -> None:
        u: Applicative[Callable[[A], A]]
        u = point(f)  # type: ignore[arg-type, assignment]
        applied: Applicative[Callable[[Callable[[A], A]], A]]
        applied = point(lambda fn: fn(value))  # type: ignore[arg-type, assignment]
        lhs = point(value).ap(u)
        rhs = u.ap(applied)
        assert eq(lhs, rhs)

    @given(
        values,
        st.functions(like=_identity, returns=values, pure=True),
        st.functions(like=_identity, returns=values, pure=True),
    )
    def composition_law(value: A, f: Callable[[A], A], g: Callable[[A], A]) -> None:
        w = point(value)
        v: Applicative[Callable[[A], A]]
        v = point(f)  # type: ignore[arg-type, assignment]
        u: Applicative[Callable[[A], A]]
        u = point(g)  # type: ignore[arg-type, assignment]
        lhs = w.ap(v.ap(u.fmap(_compose)))
        rhs = w.ap(v).ap(u)
        assert eq(lhs, rhs)

    identity_law()
    homomorphism_law()
    interchange_law()
    composition_law()
