"""Reusable Hypothesis-based Functor law checks.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/functor.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ekans.functor import Functor

A = TypeVar("A")


def _identity(a: A) -> A:
    """Return `a` unchanged; a typed stand-in for `lambda a: a`.

    `st.functions(like=...)` needs an annotated callable to infer the
    generated functions' signature from -- a bare lambda leaves mypy
    unable to infer its parameter type.
    """
    return a


def assert_functor_laws(
    make: Callable[[A], Functor[A]],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Functor[A], Functor[A]], bool]] = None,
) -> None:
    """Assert the Functor identity and composition laws for `make`.

    Args:
        make: Constructs a Functor instance wrapping a given value.
        values: A Hypothesis strategy generating values to wrap.
        equal: How to compare two Functor instances for the purpose of
            the laws below. Defaults to `==`. Pass this when the
            Functor wraps something without meaningful structural
            equality (e.g. a function) -- see docs/specs/reader.md's
            Testing implication section for why.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    @given(values)
    def identity_law(value: A) -> None:
        x = make(value)
        assert eq(x.fmap(lambda a: a), x)

    @given(
        values,
        st.functions(like=_identity, returns=values, pure=True),
        st.functions(like=_identity, returns=values, pure=True),
    )
    def composition_law(value: A, f: Callable[[A], A], g: Callable[[A], A]) -> None:
        x = make(value)
        assert eq(x.fmap(lambda a: g(f(a))), x.fmap(f).fmap(g))

    identity_law()
    composition_law()
