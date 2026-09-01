from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest
from functor_laws import assert_functor_laws
from hypothesis import strategies as st

from ekans.functor import Functor

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class _Box(Functor[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_Box[B]":
        return _Box(value=f(self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Functor[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_BrokenBox[B]":
        # Deliberately unlawful: applies f twice instead of once, to
        # prove the law helper catches it. f only accepts A, but the
        # inner f(self.value) already produced a B, so mypy correctly
        # rejects passing that B back into f ([arg-type]).
        return _BrokenBox(value=f(f(self.value)))  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _AlwaysDifferent(Functor[A], Generic[A]):
    """A lawful Functor with no __eq__ override (default identity-based
    equality, since eq=False leaves __eq__ untouched rather than having
    the dataclass generate a field-based one), to prove `equal` is
    actually used instead of a bare ==.
    """

    value: A

    def fmap(self, f: Callable[[A], B]) -> "_AlwaysDifferent[B]":
        return _AlwaysDifferent(value=f(self.value))


def test_passes_for_a_lawful_functor() -> None:
    assert_functor_laws(_Box, st.integers())


def test_fails_for_an_unlawful_functor() -> None:
    with pytest.raises(AssertionError):
        assert_functor_laws(_BrokenBox, st.integers())


def _compare_always_different(a: Functor[int], b: Functor[int]) -> bool:
    """Typed comparator for the `equal` parameter.

    Parameters are typed as the loose `Functor[int]` to match
    `equal`'s own declared signature -- `assert_functor_laws` doesn't
    know the concrete type `make` will actually produce, so narrows
    via isinstance here rather than the helper assuming it.
    """
    assert isinstance(a, _AlwaysDifferent) and isinstance(b, _AlwaysDifferent)
    return bool(a.value == b.value)


def test_uses_custom_equal_when_provided() -> None:
    assert_functor_laws(
        _AlwaysDifferent,
        st.integers(),
        equal=_compare_always_different,
    )


def test_without_equal_falls_back_to_default_equality() -> None:
    with pytest.raises(AssertionError):
        assert_functor_laws(_AlwaysDifferent, st.integers())
