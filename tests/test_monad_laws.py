from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest
from hypothesis import strategies as st
from monad_laws import assert_monad_law

from ekans.monad import Monad

A = TypeVar("A")
B = TypeVar("B")


@dataclass(frozen=True, eq=False)
class _Box(Monad[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_Box[B]":
        return _Box(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "_Box[A]":  # type: ignore[override]
        return _Box(value=value)

    def ap(self, f: "_Box[Callable[[A], B]]") -> "_Box[B]":  # type: ignore[override]
        return _Box(value=f.value(self.value))

    def bind(self, f: Callable[[A], "_Box[B]"]) -> "_Box[B]":  # type: ignore[override]
        return f(self.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Monad[A], Generic[A]):
    value: A

    def fmap(self, f: Callable[[A], B]) -> "_BrokenBox[B]":
        return _BrokenBox(value=f(self.value))

    @classmethod
    def point(cls, value: A) -> "_BrokenBox[A]":  # type: ignore[override]
        return _BrokenBox(value=value)

    def ap(  # type: ignore[override]
        self, f: "_BrokenBox[Callable[[A], B]]"
    ) -> "_BrokenBox[B]":
        return _BrokenBox(value=f.value(self.value))

    def bind(  # type: ignore[override]
        self, f: Callable[[A], "_BrokenBox[B]"]
    ) -> "_BrokenBox[B]":
        # Deliberately unlawful: ignores f entirely and returns self
        # unchanged, to prove the law helper catches it. self is
        # genuinely _BrokenBox[A], not _BrokenBox[B] -- mypy correctly
        # rejects this on its own merits ([return-value]), which is
        # part of the point: an honest "ignore f" bind isn't even
        # well-typed, let alone lawful.
        return self  # type: ignore[return-value]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_passes_for_a_lawful_monad() -> None:
    assert_monad_law(_Box.point, st.integers())


def test_fails_for_an_unlawful_monad() -> None:
    with pytest.raises(AssertionError):
        assert_monad_law(_BrokenBox.point, st.integers())
