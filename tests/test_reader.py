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
from ekans.functor import Functor, fmap
from ekans.monoid import Monoid
from ekans.reader import Reader, const
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


def test_const_returns_the_value_ignoring_the_argument() -> None:
    assert const(1)("anything") == 1


@given(st.integers(), st.text())
def test_const_ignores_whatever_it_is_given(value: int, ignored: str) -> None:
    assert const(value)(ignored) == value


def test_run_applies_the_wrapped_function() -> None:
    reader: Reader[int, int] = Reader(run=lambda r: r + 1)
    assert reader.run(1) == 2


def test_fmap_composes_onto_the_wrapped_function() -> None:
    reader: Reader[int, int] = Reader(run=lambda r: r + 1)
    assert reader.fmap(str).run(1) == "2"


def test_free_fmap_delegates_to_the_method() -> None:
    reader: Reader[int, int] = Reader(run=lambda r: r + 1)
    assert fmap(str, reader).run(1) == "2"


def test_is_immutable() -> None:
    reader: Reader[int, int] = Reader(run=lambda r: r)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        reader.run = lambda r: r  # type: ignore[misc]


def _make_reader(value: int) -> Reader[int, int]:
    return Reader(run=const(value))


def _compare_readers(a: Functor[int], b: Functor[int]) -> bool:
    """Typed comparator for the `equal` parameter.

    Parameters are typed as the loose Functor[int] to match equal's
    own declared signature; narrows via isinstance since
    assert_functor_laws doesn't know the concrete type `make` will
    actually produce. Reader instances can't be compared via == since
    they wrap functions (no structural equality in Python) -- compare
    .run(env) outputs across several sampled environments instead
    (extensional equality).
    """
    assert isinstance(a, Reader) and isinstance(b, Reader)
    return all(a.run(env) == b.run(env) for env in range(-5, 5))


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(_make_reader, st.integers(), equal=_compare_readers)


def test_point_constructs_a_reader_ignoring_its_environment() -> None:
    reader: Reader[str, int] = Reader.point(5)
    assert reader.run("anything") == 5
    assert reader.run("something else") == 5


def test_point_then_fmap_chains_correctly() -> None:
    reader: Reader[str, str] = Reader.point(5).fmap(str)
    assert reader.run("anything") == "5"


def test_call_delegates_to_run() -> None:
    reader: Reader[int, int] = Reader(run=lambda r: r + 1)
    assert reader(1) == 2


def test_ap_threads_the_same_environment_into_both_sides() -> None:
    add_r: Reader[int, int] = Reader(run=lambda r: r)
    multiply_by_r: Reader[int, Callable[[int], int]] = Reader(
        run=lambda r: (lambda x: x * r)
    )
    threaded = add_r.ap(multiply_by_r)
    assert threaded.run(3) == 9
    assert threaded.run(4) == 16


def test_free_ap_delegates_to_the_method() -> None:
    add_r: Reader[int, int] = Reader(run=lambda r: r)
    multiply_by_r: Reader[int, Callable[[int], int]] = Reader(
        run=lambda r: (lambda x: x * r)
    )
    assert ap(multiply_by_r, add_r).run(3) == 9


def test_satisfies_the_apply_law() -> None:
    assert_apply_law(_make_reader, st.integers(), equal=_compare_readers)


def test_is_an_applicative() -> None:
    assert isinstance(Reader(run=lambda r: r), Applicative)


def test_satisfies_the_applicative_laws() -> None:
    assert_applicative_law(Reader.point, st.integers(), equal=_compare_readers)


def test_mappend_combines_pointwise_across_the_environment() -> None:
    f: Reader[str, _Box] = Reader(run=lambda env: _Box(value=1))
    g: Reader[str, _Box] = Reader(run=lambda env: _Box(value=2))
    assert mappend(f, g).run("anything") == _Box(value=3)


@given(st.integers(), st.integers(), st.integers())
def test_free_mappend_is_associative(a: int, b: int, c: int) -> None:
    # Same reasoning as test_identity.py's/test_const.py's
    # test_free_mappend_is_associative: Reader doesn't nominally
    # implement Semigroup, so assert_semigroup_law doesn't apply here.
    # Can't reuse _compare_readers either -- it's typed Functor[int]
    # specifically, and these Readers produce _Box, not int.
    x: Reader[int, _Box] = Reader(run=lambda env: _Box(value=a + env))
    y: Reader[int, _Box] = Reader(run=lambda env: _Box(value=b + env))
    z: Reader[int, _Box] = Reader(run=lambda env: _Box(value=c + env))
    lhs = mappend(mappend(x, y), z)
    rhs = mappend(x, mappend(y, z))
    assert all(lhs.run(env) == rhs.run(env) for env in range(-5, 5))


def test_liftA2_lifts_a_two_argument_function() -> None:
    x: Reader[int, int] = Reader(run=lambda env: env + 1)
    y: Reader[int, int] = Reader(run=lambda env: env + 2)
    lifted = liftA2(lambda a, b: a + b, x, y)
    assert lifted.run(10) == 23


def test_mempty_constructs_the_identity_ignoring_the_environment() -> None:
    r: Reader[str, _MonoidBox] = Reader.mempty(_MonoidBox)
    assert r.run("anything") == _MonoidBox(value=0)
    assert r.run("something else") == _MonoidBox(value=0)


def test_is_not_a_monoid() -> None:
    # Reader can't nominally inherit Monoid -- same non-nominal
    # reasoning as its conditional Semigroup support.
    assert not isinstance(Reader(run=lambda r: r), Monoid)


def test_mempty_is_the_left_identity() -> None:
    x: Reader[int, _MonoidBox] = Reader(run=lambda env: _MonoidBox(value=env))
    a: Reader[int, _MonoidBox] = Reader.mempty(_MonoidBox)
    lhs = mappend(a, x)
    assert all(lhs.run(env) == x.run(env) for env in range(-5, 5))


def test_mempty_is_the_right_identity() -> None:
    x: Reader[int, _MonoidBox] = Reader(run=lambda env: _MonoidBox(value=env))
    a: Reader[int, _MonoidBox] = Reader.mempty(_MonoidBox)
    lhs = mappend(x, a)
    assert all(lhs.run(env) == x.run(env) for env in range(-5, 5))
