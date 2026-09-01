from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest
from apply_laws import assert_apply_law
from hypothesis import strategies as st

from ekans.apply import Apply

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class _Box(Apply[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_Box[B]":
        return _Box(value=f(self.value))

    def ap(self, f: "_Box[Callable[[A], B]]") -> "_Box[B]":  # type: ignore[override]
        return _Box(value=f.value(self.value))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Apply[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_BrokenBox[B]":
        return _BrokenBox(value=f(self.value))

    def ap(  # type: ignore[override]
        self, f: "_BrokenBox[Callable[[A], B]]"
    ) -> "_BrokenBox[B]":
        # Deliberately unlawful: applies f.value twice instead of once,
        # to prove the law helper catches it. f.value only accepts A,
        # but the inner f.value(self.value) already produced a B, so
        # mypy correctly rejects passing that B back in ([arg-type]).
        return _BrokenBox(value=f.value(f.value(self.value)))  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_passes_for_a_lawful_apply() -> None:
    assert_apply_law(_Box, st.integers())


def test_fails_for_an_unlawful_apply() -> None:
    with pytest.raises(AssertionError):
        assert_apply_law(_BrokenBox, st.integers())
