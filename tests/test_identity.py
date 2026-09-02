from dataclasses import dataclass
from typing import Callable

import pytest
from applicative_laws import assert_applicative_law
from apply_laws import assert_apply_law
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st

from ekans.applicative import Applicative, liftA2
from ekans.apply import ap
from ekans.extractable import Extractable
from ekans.functor import fmap
from ekans.identity import Identity
from ekans.monoid import Monoid
from ekans.semigroup import Semigroup, mappend


@dataclass(frozen=True, eq=False)
class _Box(Semigroup):
    value: int

    def mappend(self, other: "_Box") -> "_Box":
        return _Box(value=self.value + other.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Box) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _MonoidBox(Monoid):
    value: int

    def mappend(self, other: "_MonoidBox") -> "_MonoidBox":
        return _MonoidBox(value=self.value + other.value)

    @classmethod
    def mempty(cls) -> "_MonoidBox":
        return _MonoidBox(value=0)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _MonoidBox) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


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


def test_ap_applies_the_wrapped_function() -> None:
    wrapped_fn: Identity[Callable[[int], str]] = Identity(value=str)
    assert Identity(value=5).ap(wrapped_fn) == Identity(value="5")


def test_free_ap_delegates_to_the_method() -> None:
    wrapped_fn: Identity[Callable[[int], str]] = Identity(value=str)
    assert ap(wrapped_fn, Identity(value=5)) == Identity(value="5")


def test_satisfies_the_apply_law() -> None:
    assert_apply_law(Identity, st.integers())


def test_is_an_applicative() -> None:
    assert isinstance(Identity(value=1), Applicative)


def test_satisfies_the_applicative_laws() -> None:
    assert_applicative_law(Identity.point, st.integers())


def test_mappend_combines_the_wrapped_semigroup_values() -> None:
    a = Identity(value=_Box(value=1))
    b = Identity(value=_Box(value=2))
    assert mappend(a, b) == Identity(value=_Box(value=3))


@given(st.integers(), st.integers(), st.integers())
def test_free_mappend_is_associative(a: int, b: int, c: int) -> None:
    # assert_semigroup_law assumes a nominal `.mappend()` method, which
    # Identity deliberately doesn't have (see the spec's Design section
    # -- Identity's Semigroup instance is free-function-only); testing
    # the same associativity law directly against the free function
    # instead.
    x = Identity(value=_Box(value=a))
    y = Identity(value=_Box(value=b))
    z = Identity(value=_Box(value=c))
    assert mappend(mappend(x, y), z) == mappend(x, mappend(y, z))


def test_liftA2_lifts_a_two_argument_function() -> None:
    x: Identity[int] = Identity(value=2)
    y: Identity[int] = Identity(value=3)
    assert liftA2(lambda a, b: a + b, x, y) == Identity(value=5)


def test_extract_returns_the_wrapped_value() -> None:
    assert Identity(value=5).extract() == 5


def test_is_extractable() -> None:
    assert isinstance(Identity(value=5), Extractable)


@given(st.integers())
def test_extract_after_point_is_identity(value: int) -> None:
    # A real law connecting Pointed and Extractable when a type
    # implements both: extract . point == id. Only Identity does,
    # of the six Extractable types in this round -- see the spec's
    # Testing strategy section correction note.
    assert Identity.point(value).extract() == value


@given(st.integers())
def test_fmap_extract_naturality(value: int) -> None:
    # Functor/Extractable naturality: extract(w.fmap(f)) == f(w.extract()).
    # Only meaningful when fmap and extract operate on the same type
    # parameter -- true for Identity, but structurally not for Const
    # (fmap touches B, extract returns A) -- see
    # docs/specs/invariance-audit.md.
    f = str
    box = Identity(value=value)
    assert box.fmap(f).extract() == f(box.extract())


def test_ap_extract_commutes() -> None:
    # Apply/Extractable commutation: x.ap(f).extract() ==
    # f.extract()(x.extract()) -- extract behaves as an Applicative
    # homomorphism down to plain function application when both
    # instances share the same type parameter.
    wrapped_fn: Identity[Callable[[int], str]] = Identity(value=str)
    x = Identity(value=5)
    assert x.ap(wrapped_fn).extract() == wrapped_fn.extract()(x.extract())


def test_mappend_extract_homomorphism() -> None:
    # Semigroup/Extractable homomorphism: mappend(x, y).extract() ==
    # x.extract().mappend(y.extract()) -- extract distributes over
    # the free mappend function.
    x = Identity(value=_Box(value=2))
    y = Identity(value=_Box(value=3))
    assert mappend(x, y).extract() == x.extract().mappend(y.extract())


def test_mempty_constructs_the_identity_for_a_monoid_type() -> None:
    assert Identity.mempty(_MonoidBox) == Identity(value=_MonoidBox(value=0))


def test_is_not_a_monoid() -> None:
    # Identity can't nominally inherit Monoid -- same non-nominal
    # reasoning as its conditional Semigroup support.
    assert not isinstance(Identity(value=1), Monoid)


def test_mempty_is_the_left_identity() -> None:
    x = Identity(value=_MonoidBox(value=5))
    assert mappend(Identity.mempty(_MonoidBox), x) == x


def test_mempty_is_the_right_identity() -> None:
    x = Identity(value=_MonoidBox(value=5))
    assert mappend(x, Identity.mempty(_MonoidBox)) == x


def test_mempty_extract_equals_the_value_types_own_mempty() -> None:
    # Monoid/Extractable, non-nominal form -- per the spec's
    # Cross-Product audit section.
    assert Identity.mempty(_MonoidBox).extract() == _MonoidBox.mempty()
