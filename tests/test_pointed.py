from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from ekans.functional import Functional
from ekans.pointed import Pointed

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class _Box(Pointed[A], Generic[A]):
    value: A

    @classmethod
    def point(cls, value: A) -> "_Box[A]":  # type: ignore[override]
        return _Box(value=value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_cannot_instantiate_pointed_directly() -> None:
    with pytest.raises(TypeError):
        Pointed()  # type: ignore[abstract]


def test_functional_is_in_the_mro() -> None:
    assert issubclass(Pointed, Functional)


def test_concrete_subclass_implements_point() -> None:
    assert _Box.point(1) == _Box(value=1)


def test_immutability_still_holds_through_pointed() -> None:
    box = _Box.point(1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_point_raises_if_not_overridden() -> None:
    with pytest.raises(NotImplementedError):
        Pointed.point(1)
