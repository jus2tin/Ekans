import pytest
from functor_laws import assert_functor_laws
from hypothesis import strategies as st

from ekans.const import Const
from ekans.functor import fmap


def test_holds_the_value() -> None:
    assert Const(value=1).value == 1


def test_fmap_ignores_the_function_and_keeps_the_value() -> None:
    assert Const(value=1).fmap(str) == Const(value=1)


def test_free_fmap_delegates_to_the_method() -> None:
    assert fmap(str, Const(value=1)) == Const(value=1)


def test_equal_when_values_are_equal() -> None:
    assert Const(value=1) == Const(value=1)


def test_not_equal_when_values_differ() -> None:
    assert Const(value=1) != Const(value=2)


def test_not_equal_to_an_unrelated_type() -> None:
    assert Const(value=1) != "not a Const"


def test_equal_values_hash_the_same() -> None:
    assert hash(Const(value=1)) == hash(Const(value=1))


def test_is_immutable() -> None:
    const = Const(value=1)
    with pytest.raises(AttributeError):
        const.value = 2  # type: ignore[misc]


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(Const, st.integers())
