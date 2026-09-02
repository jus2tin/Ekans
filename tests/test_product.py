import pytest
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.product import Product
from ekans.semigroup import Semigroup


def test_holds_the_wrapped_value() -> None:
    assert Product(value=2).value == 2


def test_mappend_multiplies_the_wrapped_values() -> None:
    assert Product(value=2).mappend(Product(value=3)) == Product(value=6)


def test_mappend_works_with_floats() -> None:
    assert Product(value=1.5).mappend(Product(value=2.0)) == Product(value=3.0)


def test_equal_when_values_are_equal() -> None:
    assert Product(value=2) == Product(value=2)


def test_not_equal_when_values_differ() -> None:
    assert Product(value=2) != Product(value=3)


def test_not_equal_to_an_unrelated_type() -> None:
    assert Product(value=2) != "not a Product"


def test_equal_values_hash_the_same() -> None:
    assert hash(Product(value=2)) == hash(Product(value=2))


def test_is_immutable() -> None:
    product = Product(value=2)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        product.value = 3  # type: ignore[misc]


def test_is_a_semigroup() -> None:
    assert isinstance(Product(value=2), Semigroup)


def test_satisfies_the_semigroup_law() -> None:
    # Python ints don't overflow, so correctness doesn't need bounding
    # -- this is purely to keep three chained multiplications of
    # Hypothesis-generated values from producing huge, slow-to-compare
    # numbers.
    assert_semigroup_law(Product, st.integers(min_value=-1000, max_value=1000))
