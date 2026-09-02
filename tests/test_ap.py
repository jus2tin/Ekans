from dataclasses import dataclass

import pytest
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.ap import Ap
from ekans.extractable import Extractable
from ekans.identity import Identity
from ekans.semigroup import Semigroup


@dataclass(frozen=True, eq=False)
class _Box(Semigroup):
    value: int

    def mappend(self, other: "_Box") -> "_Box":
        return _Box(value=self.value + other.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


def _make_ap(value: int) -> Ap[_Box]:
    return Ap(value=Identity(value=_Box(value=value)))


def test_holds_the_wrapped_identity() -> None:
    assert Ap(value=Identity(value=_Box(value=1))).value == Identity(
        value=_Box(value=1)
    )


def test_mappend_combines_via_the_underlying_semigroup() -> None:
    a = Ap(value=Identity(value=_Box(value=1)))
    b = Ap(value=Identity(value=_Box(value=2)))
    assert a.mappend(b) == Ap(value=Identity(value=_Box(value=3)))


def test_equal_when_values_are_equal() -> None:
    assert _make_ap(1) == _make_ap(1)


def test_not_equal_when_values_differ() -> None:
    assert _make_ap(1) != _make_ap(2)


def test_not_equal_to_an_unrelated_type() -> None:
    assert _make_ap(1) != "not an Ap"


def test_equal_values_hash_the_same() -> None:
    assert hash(_make_ap(1)) == hash(_make_ap(1))


def test_is_immutable() -> None:
    wrapped = _make_ap(1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        wrapped.value = Identity(value=_Box(value=2))  # type: ignore[misc]


def test_is_a_semigroup() -> None:
    assert isinstance(_make_ap(1), Semigroup)


def test_satisfies_the_semigroup_law() -> None:
    assert_semigroup_law(_make_ap, st.integers())


def test_extract_fully_unwraps_to_the_held_value() -> None:
    ap = Ap(value=Identity(value=_Box(value=5)))
    assert ap.extract() == _Box(value=5)


def test_is_extractable() -> None:
    assert isinstance(_make_ap(1), Extractable)
