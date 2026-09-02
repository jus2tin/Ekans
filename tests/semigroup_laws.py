"""Reusable Hypothesis-based Semigroup law check.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/semigroup.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis.strategies import SearchStrategy

from ekans.semigroup import Semigroup

A = TypeVar("A")


def assert_semigroup_law(
    make: Callable[[A], Semigroup],
    values: SearchStrategy[A],
    equal: Optional[Callable[[Semigroup, Semigroup], bool]] = None,
) -> None:
    """Assert the Semigroup associativity law for `make`.

    Args:
        make: Constructs a Semigroup instance wrapping a given value.
        values: A Hypothesis strategy generating three values to wrap
            and combine.
        equal: How to compare two Semigroup instances for the purpose
            of the law below. Defaults to `==`. Pass this when the
            type doesn't have meaningful structural equality -- same
            reasoning as `functor_laws.assert_functor_laws`'s `equal`
            parameter.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    @given(values, values, values)
    def associativity_law(a: A, b: A, c: A) -> None:
        x, y, z = make(a), make(b), make(c)
        assert eq(x.mappend(y).mappend(z), x.mappend(y.mappend(z)))

    associativity_law()
