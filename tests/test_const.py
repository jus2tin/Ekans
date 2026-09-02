from dataclasses import dataclass

import pytest
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st

from ekans.const import Const
from ekans.functor import fmap
from ekans.identity import Identity
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
