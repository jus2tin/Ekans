from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st
from semigroup_laws import assert_semigroup_law

from ekans.extractable import Extractable
from ekans.foldable import Foldable, toList
from ekans.monoid import Monoid
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


def test_extract_returns_the_wrapped_value() -> None:
    assert Product(value=6).extract() == 6


def test_is_extractable() -> None:
    assert isinstance(Product(value=6), Extractable)


@given(
    st.integers(min_value=-1000, max_value=1000),
    st.integers(min_value=-1000, max_value=1000),
)
def test_mappend_extract_distributes_over_multiplication(a: int, b: int) -> None:
    # Semigroup/Extractable homomorphism, operator form -- same
    # reasoning as Sum's. See docs/specs/invariance-audit.md.
    assert Product(value=a).mappend(Product(value=b)).extract() == a * b


def test_mempty_constructs_the_multiplicative_identity_for_int() -> None:
    assert Product.mempty(int) == Product(value=1)


def test_mempty_constructs_the_multiplicative_identity_for_float() -> None:
    assert Product.mempty(float) == Product(value=1.0)


@dataclass(frozen=True, eq=False)
class _OneableBox:
    n: int

    def __mul__(self, other: "_OneableBox") -> "_OneableBox":
        return _OneableBox(n=self.n * other.n)

    @classmethod
    def one(cls) -> "_OneableBox":
        return _OneableBox(n=1)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _OneableBox) and self.n == other.n


def test_mempty_constructs_the_multiplicative_identity_for_a_custom_type() -> None:
    assert Product.mempty(_OneableBox) == Product(value=_OneableBox(n=1))


def test_is_not_a_monoid() -> None:
    # Product can't nominally inherit Monoid -- see the spec's Design
    # section. mempty still works via the explicit Type[X] argument.
    assert not isinstance(Product(value=1), Monoid)


@given(st.integers(min_value=-1000, max_value=1000))
def test_mempty_is_the_left_identity(a: int) -> None:
    assert Product.mempty(int).mappend(Product(value=a)) == Product(value=a)


@given(st.integers(min_value=-1000, max_value=1000))
def test_mempty_is_the_right_identity(a: int) -> None:
    assert Product(value=a).mappend(Product.mempty(int)) == Product(value=a)


def test_mempty_extract_is_the_multiplicative_identity() -> None:
    # Monoid/Extractable, non-nominal form -- per the spec's
    # Cross-Product audit section.
    assert Product.mempty(int).extract() == 1


def test_is_a_foldable() -> None:
    assert isinstance(Product(value=2), Foldable)


def test_iterates_the_wrapped_value() -> None:
    assert toList(Product(value=2)) == [2]


def test_extractable_foldable_coherence() -> None:
    # toList(xs) == [extract(xs)] -- see docs/specs/foldable.md's
    # retrofit Cross-Product audit.
    product = Product(value=6)
    assert toList(product) == [product.extract()]
