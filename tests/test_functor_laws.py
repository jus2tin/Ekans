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


def test_passes_for_a_lawful_functor() -> None:
    assert_functor_laws(_Box, st.integers())


def test_fails_for_an_unlawful_functor() -> None:
    with pytest.raises(AssertionError):
        assert_functor_laws(_BrokenBox, st.integers())
