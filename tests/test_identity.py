import pytest

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
        identity.value = 2  # type: ignore[misc]
