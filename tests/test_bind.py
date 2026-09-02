from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest

from ekans.apply import Apply
from ekans.bind import Bind, bind

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


def test_cannot_instantiate_bind_directly() -> None:
    with pytest.raises(TypeError):
        Bind()  # type: ignore[abstract]


def test_apply_is_in_the_mro() -> None:
    assert issubclass(Bind, Apply)


def test_concrete_subclass_implements_bind() -> None:
    box = _Box(value=5)
    assert box.bind(lambda a: _Box(value=str(a))) == _Box(value="5")


def test_free_bind_delegates_to_the_method() -> None:
    box = _Box(value=5)
    assert bind(lambda a: _Box(value=str(a)), box) == _Box(value="5")


def test_immutability_still_holds_through_bind() -> None:
    box = _Box(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_bind_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    with pytest.raises(NotImplementedError):
        Bind.bind(box, lambda a: _Box(value=a))
