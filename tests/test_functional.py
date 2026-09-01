import dataclasses

import pytest

from ekans.functional import Functional


def test_setattr_raises_attribute_error() -> None:
    obj = Functional()
    with pytest.raises(AttributeError):
        obj.value = 1


def test_delattr_raises_attribute_error() -> None:
    obj = Functional()
    with pytest.raises(AttributeError):
        del obj.value  # type: ignore[attr-defined]


def test_frozen_dataclass_subclass_can_be_constructed() -> None:
    @dataclasses.dataclass(frozen=True)
    class Box(Functional):
        value: int

    box = Box(value=1)
    assert box.value == 1


def test_frozen_dataclass_subclass_mutation_raises() -> None:
    @dataclasses.dataclass(frozen=True)
    class Box(Functional):
        value: int

    box = Box(value=1)
    with pytest.raises(AttributeError):
        box.value = 2  # type: ignore[misc]


def test_frozen_dataclass_subclass_deletion_raises() -> None:
    @dataclasses.dataclass(frozen=True)
    class Box(Functional):
        value: int

    box = Box(value=1)
    with pytest.raises(AttributeError):
        del box.value
