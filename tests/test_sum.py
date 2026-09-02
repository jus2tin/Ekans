import pytest
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.semigroup import Semigroup
from ekans.sum import Sum


def test_holds_the_wrapped_value() -> None:
    assert Sum(value=1).value == 1


def test_mappend_adds_the_wrapped_values() -> None:
    assert Sum(value=1).mappend(Sum(value=2)) == Sum(value=3)


def test_mappend_works_with_floats() -> None:
    assert Sum(value=1.5).mappend(Sum(value=2.5)) == Sum(value=4.0)


def test_equal_when_values_are_equal() -> None:
    assert Sum(value=1) == Sum(value=1)


def test_not_equal_when_values_differ() -> None:
    assert Sum(value=1) != Sum(value=2)


def test_not_equal_to_an_unrelated_type() -> None:
    assert Sum(value=1) != "not a Sum"


def test_equal_values_hash_the_same() -> None:
    assert hash(Sum(value=1)) == hash(Sum(value=1))


def test_is_immutable() -> None:
    total = Sum(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        total.value = 2  # type: ignore[misc]


def test_is_a_semigroup() -> None:
    assert isinstance(Sum(value=1), Semigroup)


def test_satisfies_the_semigroup_law() -> None:
    assert_semigroup_law(Sum, st.integers())
