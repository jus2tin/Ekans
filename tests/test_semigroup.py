from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from ekans.functional import Functional
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


def test_cannot_instantiate_semigroup_directly() -> None:
    with pytest.raises(TypeError):
        Semigroup()  # type: ignore[abstract]


def test_functional_is_in_the_mro() -> None:
    assert issubclass(Semigroup, Functional)


def test_concrete_subclass_implements_mappend() -> None:
    assert _Box(value=1).mappend(_Box(value=2)) == _Box(value=3)


def test_immutability_still_holds_through_semigroup() -> None:
    box = _Box(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_mappend_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    with pytest.raises(NotImplementedError):
        Semigroup.mappend(box, box)
