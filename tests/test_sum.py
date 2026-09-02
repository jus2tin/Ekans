from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.extractable import Extractable
from ekans.monoid import Monoid
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


def test_extract_returns_the_wrapped_value() -> None:
    assert Sum(value=5).extract() == 5


def test_is_extractable() -> None:
    assert isinstance(Sum(value=5), Extractable)


@given(st.integers(), st.integers())
def test_mappend_extract_distributes_over_addition(a: int, b: int) -> None:
    # Semigroup/Extractable homomorphism, operator form: Sum's held
    # type is bound by SupportsAdd, not Semigroup, so there's no
    # `.mappend()` on the extracted value to compare against -- the
    # law is stated against `+` directly, the operation mappend
    # itself delegates to. See docs/specs/invariance-audit.md.
    assert Sum(value=a).mappend(Sum(value=b)).extract() == a + b


def test_mempty_constructs_the_additive_identity_for_int() -> None:
    assert Sum.mempty(int) == Sum(value=0)


def test_mempty_constructs_the_additive_identity_for_float() -> None:
    assert Sum.mempty(float) == Sum(value=0.0)


@dataclass(frozen=True, eq=False)
class _ZeroableBox:
    n: int

    def __add__(self, other: "_ZeroableBox") -> "_ZeroableBox":
        return _ZeroableBox(n=self.n + other.n)

    @classmethod
    def zero(cls) -> "_ZeroableBox":
        return _ZeroableBox(n=0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _ZeroableBox) and self.n == other.n


def test_mempty_constructs_the_additive_identity_for_a_custom_type() -> None:
    assert Sum.mempty(_ZeroableBox) == Sum(value=_ZeroableBox(n=0))


def test_is_not_a_monoid() -> None:
    # Sum can't nominally inherit Monoid -- see the spec's Design
    # section. mempty still works via the explicit Type[X] argument.
    assert not isinstance(Sum(value=1), Monoid)


@given(st.integers())
def test_mempty_is_the_left_identity(a: int) -> None:
    assert Sum.mempty(int).mappend(Sum(value=a)) == Sum(value=a)


@given(st.integers())
def test_mempty_is_the_right_identity(a: int) -> None:
    assert Sum(value=a).mappend(Sum.mempty(int)) == Sum(value=a)


def test_mempty_extract_is_the_additive_identity() -> None:
    # Monoid/Extractable, non-nominal form -- per the spec's
    # Cross-Product audit section.
    assert Sum.mempty(int).extract() == 0
