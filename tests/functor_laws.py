"""Reusable Hypothesis-based Functor law checks.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/functor.md's Testing strategy section.
"""

from typing import Callable, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ekans.functor import Functor

A = TypeVar("A")


def assert_functor_laws(
    make: Callable[[A], Functor[A]],
    values: SearchStrategy[A],
) -> None:
    """Assert the Functor identity and composition laws for `make`.

    Args:
        make: Constructs a Functor instance wrapping a given value.
        values: A Hypothesis strategy generating values to wrap.
    """

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
