from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from ekans.extractable import Extractable
from ekans.functional import Functional

A = TypeVar("A")


@dataclass(frozen=True, eq=False)
class _Box(Extractable[A], Generic[A]):
    value: A

    def extract(self) -> A:
        return self.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and bool(self.value == other.value)

    def __hash__(self) -> int:
        return hash(self.value)


def test_cannot_instantiate_extractable_directly() -> None:
    with pytest.raises(TypeError):
        Extractable()  # type: ignore[abstract]


def test_functional_is_in_the_mro() -> None:
    assert issubclass(Extractable, Functional)


def test_concrete_subclass_implements_extract() -> None:
    assert _Box(value=5).extract() == 5


def test_immutability_still_holds_through_extractable() -> None:
    box = _Box(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        box.value = 2  # type: ignore[misc]


def test_abstract_extract_raises_if_not_overridden() -> None:
    box = _Box(value=1)
    with pytest.raises(NotImplementedError):
        Extractable.extract(box)
