import pytest
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.all import All
from ekans.extractable import Extractable
from ekans.semigroup import Semigroup


def test_holds_the_wrapped_value() -> None:
    assert All(value=True).value is True


def test_mappend_ands_the_wrapped_values() -> None:
    assert All(value=True).mappend(All(value=True)) == All(value=True)
    assert All(value=True).mappend(All(value=False)) == All(value=False)
    assert All(value=False).mappend(All(value=True)) == All(value=False)
    assert All(value=False).mappend(All(value=False)) == All(value=False)


def test_equal_when_values_are_equal() -> None:
    assert All(value=True) == All(value=True)


def test_not_equal_when_values_differ() -> None:
    assert All(value=True) != All(value=False)


def test_not_equal_to_an_unrelated_type() -> None:
    assert All(value=True) != "not an All"


def test_equal_values_hash_the_same() -> None:
    assert hash(All(value=True)) == hash(All(value=True))


def test_is_immutable() -> None:
    flag = All(value=True)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        flag.value = False  # type: ignore[misc]


def test_is_a_semigroup() -> None:
    assert isinstance(All(value=True), Semigroup)


def test_satisfies_the_semigroup_law() -> None:
    assert_semigroup_law(All, st.booleans())


def test_extract_returns_the_wrapped_value() -> None:
    assert All(value=True).extract() is True


def test_is_extractable() -> None:
    assert isinstance(All(value=True), Extractable)
