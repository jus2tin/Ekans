from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest
from applicative_laws import assert_applicative_law
from hypothesis import strategies as st

from ekans.applicative import Applicative

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class _Box(Applicative[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_Box[B]":
        return _Box(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "_Box[A]":  # type: ignore[override]
        return _Box(value=value)

    def ap(self, f: "_Box[Callable[[A], B]]") -> "_Box[B]":  # type: ignore[override]
        return _Box(value=f.value(self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Applicative[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_BrokenBox[B]":
        return _BrokenBox(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "_BrokenBox[A]":  # type: ignore[override]
        return _BrokenBox(value=value)

    def ap(  # type: ignore[override]
        self, f: "_BrokenBox[Callable[[A], B]]"
    ) -> "_BrokenBox[B]":
        # Deliberately unlawful: applies f.value twice instead of once,
        # same bug apply_laws.py's own _BrokenBox uses. f.value only
        # accepts A, but the inner f.value(self.value) already produced
        # a B, so mypy correctly rejects passing that B back in
        # ([arg-type]).
        return _BrokenBox(value=f.value(f.value(self.value)))  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_passes_for_a_lawful_applicative() -> None:
    assert_applicative_law(_Box.point, st.integers())


def test_fails_for_an_unlawful_applicative() -> None:
    with pytest.raises(AssertionError):
        assert_applicative_law(_BrokenBox.point, st.integers())
