"""Reusable Hypothesis-based Bind law check.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/bind.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from ekans.bind import Bind

A = TypeVar("A")


def _identity(a: A) -> A:
    """Return `a` unchanged; a typed stand-in for `lambda a: a`.

    `st.functions(like=...)` needs an annotated callable to infer the
    generated functions' signature from -- a bare lambda leaves mypy
    unable to infer its parameter type.
    """
    return a


def assert_bind_law(
    make: Callable[[A], Bind[A]],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Bind[A], Bind[A]], bool]] = None,
) -> None:
    """Assert the Bind associativity law for `make`.

    Args:
        make: Constructs a Bind instance wrapping a given value.
        values: A Hypothesis strategy generating values to wrap.
        equal: How to compare two Bind instances for the purpose of
            the law below. Defaults to `==`. Same reasoning as
            `assert_apply_law`'s `equal` parameter.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    @given(
        values,
        st.functions(like=_identity, returns=values, pure=True),
        st.functions(like=_identity, returns=values, pure=True),
    )
    def associativity_law(value: A, f: Callable[[A], A], g: Callable[[A], A]) -> None:
        m = make(value)

        def wrapped_f(a: A) -> Bind[A]:
            return make(f(a))

        def wrapped_g(a: A) -> Bind[A]:
            return make(g(a))

        lhs = m.bind(wrapped_f).bind(wrapped_g)
        rhs = m.bind(lambda a: wrapped_f(a).bind(wrapped_g))
        assert eq(lhs, rhs)

    associativity_law()
