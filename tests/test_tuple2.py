from dataclasses import dataclass
from typing import Callable

import pytest
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st

from ekans.applicative import Applicative, liftA2
from ekans.apply import Apply, ap
from ekans.bind import Bind, bind
from ekans.extractable import Extractable
from ekans.functor import fmap
from ekans.monad import Monad
from ekans.monoid import Monoid
from ekans.semigroup import Semigroup
from ekans.tuple2 import Tuple2


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


def test_holds_the_values() -> None:
    t = Tuple2(first=1, second="x")
    assert t.first == 1
    assert t.second == "x"


def test_equal_when_values_are_equal() -> None:
    assert Tuple2(first=1, second="x") == Tuple2(first=1, second="x")


def test_not_equal_when_first_differs() -> None:
    assert Tuple2(first=1, second="x") != Tuple2(first=2, second="x")


def test_not_equal_when_second_differs() -> None:
    assert Tuple2(first=1, second="x") != Tuple2(first=1, second="y")


def test_not_equal_to_an_unrelated_type() -> None:
    assert Tuple2(first=1, second="x") != "not a Tuple2"


def test_equal_values_hash_the_same() -> None:
    assert hash(Tuple2(first=1, second="x")) == hash(Tuple2(first=1, second="x"))


def test_is_immutable() -> None:
    t = Tuple2(first=1, second="x")
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        t.second = "y"  # type: ignore[misc]


def test_fmap_applies_the_function_to_second_only() -> None:
    assert Tuple2(first=1, second=2).fmap(str) == Tuple2(first=1, second="2")


def test_free_fmap_delegates_to_the_method() -> None:
    assert fmap(str, Tuple2(first=1, second=2)) == Tuple2(first=1, second="2")


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(lambda value: Tuple2(first=1, second=value), st.integers())


def test_extract_returns_second() -> None:
    assert Tuple2(first=1, second=2).extract() == 2


def test_is_extractable() -> None:
    assert isinstance(Tuple2(first=1, second=2), Extractable)


def test_point_constructs_a_tuple2_pairing_the_identity_with_the_value() -> None:
    assert Tuple2.point(_MonoidBox, 5) == Tuple2(first=_MonoidBox(value=0), second=5)


@given(st.integers())
def test_point_genuinely_uses_the_value_unlike_const_point(value: int) -> None:
    # Contrast with Const.point, which discards its `value` argument
    # entirely -- Tuple2.point's `value` becomes the real `second`
    # field, per the spec's Design section.
    assert Tuple2.point(_MonoidBox, value).second == value


@given(st.integers())
def test_extract_after_point_is_identity(value: int) -> None:
    # Pointed/Extractable round-trip, holding in its full form here --
    # unlike Const.point, which breaks this law by discarding `value`.
    assert Tuple2.point(_MonoidBox, value).extract() == value


def test_is_not_a_pointed() -> None:
    # Tuple2 can't nominally inherit Pointed/Apply/Applicative/Bind/
    # Monad -- same non-nominal reasoning as Const's conditional
    # Applicative-shaped support.
    assert not isinstance(Tuple2(first=1, second=2), Applicative)
    assert not isinstance(Tuple2(first=1, second=2), Apply)
    assert not isinstance(Tuple2(first=1, second=2), Bind)
    assert not isinstance(Tuple2(first=1, second=2), Monad)


def test_ap_combines_first_via_mappend_and_applies_the_function() -> None:
    x: Tuple2[_Box, int] = Tuple2(first=_Box(value=1), second=5)
    f: Tuple2[_Box, Callable[[int], str]] = Tuple2(first=_Box(value=2), second=str)
    assert ap(f, x) == Tuple2(first=_Box(value=3), second="5")


def test_ap_extract_commutation() -> None:
    # Apply/Extractable commutation, in its full form -- unlike
    # Const's degenerate mappend-only substitute, Tuple2's ap really
    # applies the function, so this is the real law, matching
    # Identity's: x.ap(f).extract() == f.extract()(x.extract()).
    x: Tuple2[_Box, int] = Tuple2(first=_Box(value=1), second=5)
    f: Tuple2[_Box, Callable[[int], str]] = Tuple2(first=_Box(value=2), second=str)
    assert ap(f, x).extract() == f.extract()(x.extract())


def test_bind_combines_first_via_mappend_and_applies_f() -> None:
    x: Tuple2[_Box, int] = Tuple2(first=_Box(value=1), second=5)

    def f(a: int) -> "Tuple2[_Box, str]":
        return Tuple2(first=_Box(value=10), second=str(a))

    assert bind(f, x) == Tuple2(first=_Box(value=11), second="5")


def test_bind_extract_law() -> None:
    # Bind/Extractable, in its full form -- matching Identity's:
    # m.bind(f).extract() == f(m.extract()).extract()
    x: Tuple2[_Box, int] = Tuple2(first=_Box(value=1), second=5)

    def f(a: int) -> "Tuple2[_Box, str]":
        return Tuple2(first=_Box(value=10), second=str(a))

    assert bind(f, x).extract() == f(x.extract()).extract()


def test_liftA2_lifts_a_two_argument_function() -> None:
    x: Tuple2[_Box, int] = Tuple2(first=_Box(value=1), second=2)
    y: Tuple2[_Box, int] = Tuple2(first=_Box(value=3), second=4)
    assert liftA2(lambda a, b: a + b, x, y) == Tuple2(first=_Box(value=4), second=6)


# --- Applicative laws, hand-written against the free point/ap
# functions -- Tuple2 doesn't nominally implement Applicative, so
# assert_applicative_law (which assumes a real instance) doesn't
# apply; per the spec, these are meaningful here since ap does real
# work, unlike Const's degenerate case which left this unbuilt. ---


def _identity(a: int) -> int:
    return a


@given(st.integers())
def test_applicative_identity_law(value: int) -> None:
    v: Tuple2[_MonoidBox, int] = Tuple2(first=_MonoidBox(value=7), second=value)
    id_wrapped: Tuple2[_MonoidBox, Callable[[int], int]] = Tuple2.point(
        _MonoidBox, _identity
    )
    assert ap(id_wrapped, v) == v


@given(st.integers(), st.functions(like=_identity, returns=st.integers(), pure=True))
def test_applicative_homomorphism_law(value: int, f: Callable[[int], int]) -> None:
    lhs = ap(Tuple2.point(_MonoidBox, f), Tuple2.point(_MonoidBox, value))
    rhs = Tuple2.point(_MonoidBox, f(value))
    assert lhs == rhs


@given(st.integers(), st.functions(like=_identity, returns=st.integers(), pure=True))
def test_applicative_interchange_law(value: int, f: Callable[[int], int]) -> None:
    u = Tuple2.point(_MonoidBox, f)
    applied: Tuple2[_MonoidBox, Callable[[Callable[[int], int]], int]] = Tuple2.point(
        _MonoidBox, lambda fn: fn(value)
    )
    lhs = ap(u, Tuple2.point(_MonoidBox, value))
    rhs = ap(applied, u)
    assert lhs == rhs


@given(
    st.integers(),
    st.functions(like=_identity, returns=st.integers(), pure=True),
    st.functions(like=_identity, returns=st.integers(), pure=True),
)
def test_applicative_composition_law(
    value: int, f: Callable[[int], int], g: Callable[[int], int]
) -> None:
    w: Tuple2[_MonoidBox, int] = Tuple2(first=_MonoidBox(value=1), second=value)
    v: Tuple2[_MonoidBox, Callable[[int], int]] = Tuple2(
        first=_MonoidBox(value=2), second=f
    )
    u: Tuple2[_MonoidBox, Callable[[int], int]] = Tuple2(
        first=_MonoidBox(value=3), second=g
    )

    def compose(
        g: Callable[[int], int],
    ) -> Callable[[Callable[[int], int]], Callable[[int], int]]:
        def compose_with(f: Callable[[int], int]) -> Callable[[int], int]:
            def composed(a: int) -> int:
                return g(f(a))

            return composed

        return compose_with

    lhs = ap(ap(fmap(compose, u), v), w)
    rhs = ap(v, w)
    rhs = ap(u, rhs)
    assert lhs == rhs
