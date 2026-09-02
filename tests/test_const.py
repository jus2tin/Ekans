from dataclasses import dataclass
from typing import Callable

import pytest
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st

from ekans.apply import ap
from ekans.const import Const
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
    const: Const[int, object] = Const(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        const.value = 2  # type: ignore[misc]


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(Const, st.integers())


def test_mappend_combines_the_held_semigroup_values() -> None:
    a: Const[_Box, str] = Const(value=_Box(value=1))
    b: Const[_Box, str] = Const(value=_Box(value=2))
    assert mappend(a, b) == Const(value=_Box(value=3))


@given(st.integers(), st.integers(), st.integers())
def test_free_mappend_is_associative(a: int, b: int, c: int) -> None:
    # Same reasoning as test_identity.py's test_free_mappend_is_associative:
    # Const doesn't nominally implement Semigroup, so assert_semigroup_law
    # (which assumes a `.mappend()` method) doesn't apply here.
    x: Const[_Box, str] = Const(value=_Box(value=a))
    y: Const[_Box, str] = Const(value=_Box(value=b))
    z: Const[_Box, str] = Const(value=_Box(value=c))
    assert mappend(mappend(x, y), z) == mappend(x, mappend(y, z))


def test_mappend_rejects_mismatched_container_types_at_runtime() -> None:
    const: Const[_Box, str] = Const(value=_Box(value=1))
    identity: Identity[_Box] = Identity(value=_Box(value=1))
    with pytest.raises(TypeError):
        # No @overload admits a mixed Identity/Const call -- mypy
        # correctly rejects this at the call site ([call-overload]),
        # so this deliberately bypasses that with type: ignore to
        # exercise the runtime isinstance dispatch's fallback branch,
        # which the Union-typed implementation signature still has to
        # guard even though no typed caller can ever reach it.
        mappend(const, identity)  # type: ignore[call-overload]


def test_extract_returns_the_held_value() -> None:
    assert Const(value=5).extract() == 5


def test_is_extractable() -> None:
    assert isinstance(Const(value=5), Extractable)


def test_mappend_extract_homomorphism() -> None:
    # Semigroup/Extractable homomorphism: mappend(x, y).extract() ==
    # x.extract().mappend(y.extract()) -- same law as Identity's, via
    # the free mappend function. Functor/Extractable naturality is
    # deliberately NOT tested here -- fmap touches B, extract returns
    # A, genuinely different type parameters -- see
    # docs/specs/invariance-audit.md for the structural justification.
    x: Const[_Box, str] = Const(value=_Box(value=2))
    y: Const[_Box, str] = Const(value=_Box(value=3))
    assert mappend(x, y).extract() == x.extract().mappend(y.extract())


def test_mempty_constructs_the_identity_for_a_monoid_type() -> None:
    a: Const[_MonoidBox, str] = Const.mempty(_MonoidBox)
    assert a == Const(value=_MonoidBox(value=0))


def test_is_not_a_monoid() -> None:
    # Const can't nominally inherit Monoid -- same non-nominal
    # reasoning as its conditional Semigroup support.
    assert not isinstance(Const(value=1), Monoid)


def test_mempty_is_the_left_identity() -> None:
    x: Const[_MonoidBox, str] = Const(value=_MonoidBox(value=5))
    a: Const[_MonoidBox, str] = Const.mempty(_MonoidBox)
    assert mappend(a, x) == x


def test_mempty_is_the_right_identity() -> None:
    x: Const[_MonoidBox, str] = Const(value=_MonoidBox(value=5))
    a: Const[_MonoidBox, str] = Const.mempty(_MonoidBox)
    assert mappend(x, a) == x


def test_mempty_extract_equals_the_value_types_own_mempty() -> None:
    # Monoid/Extractable, non-nominal form -- per the spec's
    # Cross-Product audit section.
    a: Const[_MonoidBox, str] = Const.mempty(_MonoidBox)
    assert a.extract() == _MonoidBox.mempty()


def test_point_constructs_a_const_wrapping_the_identity_element() -> None:
    a: Const[_MonoidBox, str] = Const.point(_MonoidBox, "ignored")
    assert a == Const(value=_MonoidBox(value=0))


@given(st.text(), st.text())
def test_point_discards_the_passed_value(first: str, second: str) -> None:
    # docs/specs/const-applicative.md's Design section: `value` is
    # accepted purely for Pointed.point's conventional shape, then
    # unconditionally discarded -- the result never depends on it.
    a: Const[_MonoidBox, str] = Const.point(_MonoidBox, first)
    b: Const[_MonoidBox, str] = Const.point(_MonoidBox, second)
    assert a == b


def test_ap_combines_the_held_semigroup_values() -> None:
    x: Const[_Box, int] = Const(value=_Box(value=1))
    f: Const[_Box, Callable[[int], str]] = Const(value=_Box(value=2))
    assert ap(f, x) == Const(value=_Box(value=3))


def test_ap_rejects_a_non_semigroup_value_type_at_runtime() -> None:
    x: Const[int, int] = Const(value=1)
    f: Const[int, Callable[[int], str]] = Const(value=2)
    with pytest.raises(AttributeError):
        # No overload admits a Const held-value type without a
        # Semigroup bound -- mypy correctly rejects this at the call
        # site ([type-var]), so the ignore comment below deliberately
        # bypasses that to exercise the runtime failure: plain `int`
        # has no `.mappend()` method to combine the two sides with.
        ap(f, x)  # type: ignore[type-var]


@given(st.integers(), st.integers())
def test_ap_extract_homomorphism(a: int, b: int) -> None:
    # Apply/Extractable, non-nominal form -- per the spec's
    # Cross-Product audit section: extract(ap(f, x)) ==
    # x.extract().mappend(f.extract()). Const's ap never applies a
    # function (there's no B value to apply anything to); it's a
    # mappend homomorphism instead, directly by construction.
    x: Const[_Box, int] = Const(value=_Box(value=a))
    f: Const[_Box, Callable[[int], str]] = Const(value=_Box(value=b))
    assert ap(f, x).extract() == x.extract().mappend(f.extract())
