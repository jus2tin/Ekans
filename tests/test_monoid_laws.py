from dataclasses import dataclass

import pytest
from hypothesis import strategies as st
from monoid_laws import assert_monoid_law

from ekans.monoid import Monoid


@dataclass(frozen=True, eq=False)
class _Box(Monoid):
    value: int

    def mappend(self, other: "_Box") -> "_Box":
        return _Box(value=self.value + other.value)

    @classmethod
    def mempty(cls) -> "_Box":
        return _Box(value=0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _BrokenBox(Monoid):
    value: int

    def mappend(self, other: "_BrokenBox") -> "_BrokenBox":
        return _BrokenBox(value=self.value + other.value)

    @classmethod
    def mempty(cls) -> "_BrokenBox":
        # Deliberately unlawful: 1 isn't addition's identity, to prove
        # the law helper catches it.
        return _BrokenBox(value=1)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _BrokenBox) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_passes_for_a_lawful_monoid() -> None:
    assert_monoid_law(_Box, _Box.mempty(), st.integers())


def test_fails_for_an_unlawful_monoid() -> None:
    with pytest.raises(AssertionError):
        assert_monoid_law(_BrokenBox, _BrokenBox.mempty(), st.integers())
