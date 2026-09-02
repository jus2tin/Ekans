"""Reusable Hypothesis-based Monoid law check.

Test infrastructure, not part of the public `ekans` package -- see
docs/specs/monoid.md's Testing strategy section.
"""

from typing import Callable, Optional, TypeVar

from hypothesis import given
from hypothesis.strategies import SearchStrategy

from ekans.monoid import Monoid

A = TypeVar("A")


def assert_monoid_law(
    make: Callable[[A], Monoid],
    mempty: Monoid,
    values: SearchStrategy[A],
    equal: Optional[Callable[[Monoid, Monoid], bool]] = None,
) -> None:
    """Assert the Monoid left/right identity laws for `make`.

    Args:
        make: Constructs a Monoid instance wrapping a given value.
        mempty: The identity element for this Monoid (e.g. `Box.mempty()`).
        values: A Hypothesis strategy generating values to wrap.
        equal: How to compare two Monoid instances for the purpose of
            the laws below. Defaults to `==`. Same reasoning as
            `assert_semigroup_law`'s `equal` parameter.
    """
    eq = equal if equal is not None else (lambda a, b: a == b)

    @given(values)
    def left_identity_law(a: A) -> None:
        x = make(a)
        assert eq(mempty.mappend(x), x)

    @given(values)
    def right_identity_law(a: A) -> None:
        x = make(a)
        assert eq(x.mappend(mempty), x)

    left_identity_law()
    right_identity_law()
