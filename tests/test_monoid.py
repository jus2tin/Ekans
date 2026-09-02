from dataclasses import dataclass

import pytest

from ekans.monoid import Monoid
from ekans.semigroup import Semigroup


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


def test_cannot_instantiate_monoid_directly() -> None:
    with pytest.raises(TypeError):
        Monoid()  # type: ignore[abstract]


def test_semigroup_is_in_the_mro() -> None:
    assert issubclass(Monoid, Semigroup)


def test_concrete_subclass_implements_mempty() -> None:
    assert _Box.mempty() == _Box(value=0)


def test_abstract_mempty_raises_if_not_overridden() -> None:
    with pytest.raises(NotImplementedError):
        Monoid.mempty()
