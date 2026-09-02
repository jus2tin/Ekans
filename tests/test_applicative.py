from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest

from ekans.applicative import Applicative
from ekans.apply import Apply
from ekans.pointed import Pointed

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


def test_cannot_instantiate_applicative_directly() -> None:
    with pytest.raises(TypeError):
        Applicative()  # type: ignore[abstract]


def test_pointed_is_in_the_mro() -> None:
    assert issubclass(Applicative, Pointed)


def test_apply_is_in_the_mro() -> None:
    assert issubclass(Applicative, Apply)


def test_concrete_subclass_implements_both_point_and_ap() -> None:
    box = _Box.point(5)
    wrapped_fn: _Box[Callable[[int], str]] = _Box.point(str)
    assert box.ap(wrapped_fn) == _Box(value="5")


def test_immutability_still_holds_through_applicative() -> None:
    box = _Box(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_fmap_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    with pytest.raises(NotImplementedError):
        Applicative.fmap(box, str)


def test_abstract_ap_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    wrapped_fn = _Box(value=str)
    with pytest.raises(NotImplementedError):
        Applicative.ap(box, wrapped_fn)
