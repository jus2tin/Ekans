from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest

from ekans.functional import Functional
from ekans.functor import Functor, fmap

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


def test_cannot_instantiate_functor_directly() -> None:
    with pytest.raises(TypeError):
        # Functor is abstract; mypy correctly flags direct instantiation
        # ([abstract]), which is exactly what we're confirming raises.
        Functor()  # type: ignore[abstract]


def test_functional_is_in_the_mro() -> None:
    assert issubclass(Functor, Functional)


def test_concrete_subclass_implements_fmap() -> None:
    assert _Box(value=1).fmap(str) == _Box(value="1")


def test_free_fmap_delegates_to_the_method() -> None:
    assert fmap(str, _Box(value=1)) == _Box(value="1")


def test_immutability_still_holds_through_functor() -> None:
    box = _Box(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_fmap_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    with pytest.raises(NotImplementedError):
        Functor.fmap(box, str)
