from hypothesis import given
from hypothesis import strategies as st

from ekans.reader import const


def test_const_returns_the_value_ignoring_the_argument() -> None:
    assert const(1)("anything") == 1


@given(st.integers(), st.text())
def test_const_ignores_whatever_it_is_given(value: int, ignored: str) -> None:
    assert const(value)(ignored) == value
