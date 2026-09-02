from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.semigroup import Semigroup

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class _Box(Semigroup, Generic[A]):
    value: A

    def mappend(self, other: "_Box[A]") -> "_Box[A]":
        return _Box(value=self.value + other.value)  # type: ignore[operator]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Semigroup, Generic[A]):
    value: A

    def mappend(self, other: "_BrokenBox[A]") -> "_BrokenBox[A]":
        # Deliberately unlawful: subtraction isn't associative, to
        # prove the law helper catches it.
        return _BrokenBox(value=self.value - other.value)  # type: ignore[operator]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_passes_for_a_lawful_semigroup() -> None:
    assert_semigroup_law(_Box, st.integers())


def test_fails_for_an_unlawful_semigroup() -> None:
    with pytest.raises(AssertionError):
        assert_semigroup_law(_BrokenBox, st.integers())
