from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

import pytest

from ekans.apply import Apply, ap
from ekans.functor import Functor

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


def test_cannot_instantiate_apply_directly() -> None:
    with pytest.raises(TypeError):
        Apply()  # type: ignore[abstract]


def test_functor_is_in_the_mro() -> None:
    assert issubclass(Apply, Functor)


def test_concrete_subclass_implements_ap() -> None:
    box = _Box(value=5)
    wrapped_fn: _Box[Callable[[int], str]] = _Box(value=str)
    assert box.ap(wrapped_fn) == _Box(value="5")


def test_free_ap_delegates_to_the_method() -> None:
    box = _Box(value=5)
    wrapped_fn: _Box[Callable[[int], str]] = _Box(value=str)
    assert ap(wrapped_fn, box) == _Box(value="5")


def test_immutability_still_holds_through_apply() -> None:
    box = _Box(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_ap_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    wrapped_fn = _Box(value=str)
    with pytest.raises(NotImplementedError):
        Apply.ap(box, wrapped_fn)


def test_abstract_fmap_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    with pytest.raises(NotImplementedError):
        Apply.fmap(box, str)
