import pytest
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st

from ekans.functor import fmap
from ekans.identity import Identity


def test_holds_the_wrapped_value() -> None:
    assert Identity(value=1).value == 1


def test_equal_when_values_are_equal() -> None:
    assert Identity(value=1) == Identity(value=1)


def test_not_equal_when_values_differ() -> None:
    assert Identity(value=1) != Identity(value=2)


def test_is_immutable() -> None:
    identity = Identity(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        identity.value = 2  # type: ignore[misc]


def test_not_equal_to_an_unrelated_type() -> None:
    assert Identity(value=1) != "not an Identity"


def test_equal_values_hash_the_same() -> None:
    assert hash(Identity(value=1)) == hash(Identity(value=1))


def test_is_usable_as_a_set_member() -> None:
    assert {Identity(value=1), Identity(value=1), Identity(value=2)} == {
        Identity(value=1),
        Identity(value=2),
    }


def test_fmap_applies_the_function_to_the_wrapped_value() -> None:
    assert Identity(value=1).fmap(str) == Identity(value="1")


def test_free_fmap_delegates_to_the_method() -> None:
    assert fmap(str, Identity(value=1)) == Identity(value="1")


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(Identity, st.integers())


def test_point_constructs_an_identity_wrapping_the_value() -> None:
    assert Identity.point(1) == Identity(value=1)


def test_point_then_fmap_chains_correctly() -> None:
    assert Identity.point(1).fmap(str) == Identity(value="1")


@given(st.integers())
def test_point_wraps_the_value_unchanged(value: int) -> None:
    assert Identity.point(value).value == value
