from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest
from bind_laws import assert_bind_law
from hypothesis import strategies as st

from ekans.bind import Bind

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class _Box(Bind[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_Box[B]":
        return _Box(value=f(self.value))

    def ap(self, f: "_Box[Callable[[A], B]]") -> "_Box[B]":  # type: ignore[override]
        return _Box(value=f.value(self.value))

    def bind(self, f: Callable[[A], "_Box[B]"]) -> "_Box[B]":  # type: ignore[override]
        return f(self.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Bind[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_BrokenBox[B]":
        return _BrokenBox(value=f(self.value))

    def ap(  # type: ignore[override]
        self, f: "_BrokenBox[Callable[[A], B]]"
    ) -> "_BrokenBox[B]":
        return _BrokenBox(value=f.value(self.value))

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "_BrokenBox[B]"]
    ) -> "_BrokenBox[B]":
        # Deliberately unlawful: applies f twice instead of once, to
        # prove the law helper catches it.
        return f(f(self.value).value)  # type: ignore[arg-type]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_passes_for_a_lawful_bind() -> None:
    assert_bind_law(_Box, st.integers())


def test_fails_for_an_unlawful_bind() -> None:
    with pytest.raises(AssertionError):
        assert_bind_law(_BrokenBox, st.integers())
