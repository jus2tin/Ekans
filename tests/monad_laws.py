"""Reusable Hypothesis-based Monad law checks.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/monad.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ekans.monad import Monad

A = TypeVar("A")


def _identity(a: A) -> A:
    """Return `a` unchanged; a typed stand-in for `lambda a: a`.

    `st.functions(like=...)` needs an annotated callable to infer the
    generated functions' signature from.
    """
    return a


def assert_monad_law(
    point: Callable[[A], Monad[A]],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Monad[A], Monad[A]], bool]] = None,
) -> None:
    """Assert the Monad left- and right-identity laws for `point`.

    Associativity isn't retested here -- it's already covered by
    `Bind`'s own law, unconditionally true for anything satisfying
    `Monad` (which requires `Bind`).

    Args:
        point: The concrete type's own `point` classmethod (e.g.
            `Identity.point`) -- used to construct every Monad the
            laws need.
        values: A Hypothesis strategy generating values to wrap.
        equal: How to compare two Monad instances for the purpose of
            the laws below. Defaults to `==`. Same reasoning as
            `assert_applicative_law`'s `equal` parameter.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    @given(values, st.functions(like=_identity, returns=values, pure=True))
    def left_identity_law(value: A, f: Callable[[A], A]) -> None:
        def wrapped_f(a: A) -> Monad[A]:
            return point(f(a))

        lhs = point(value).bind(wrapped_f)
        rhs = wrapped_f(value)
        assert eq(lhs, rhs)

    @given(values)
    def right_identity_law(value: A) -> None:
        m = point(value)
        assert eq(m.bind(point), m)

    left_identity_law()
    right_identity_law()
