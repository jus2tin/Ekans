import pytest
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st

from ekans.functor import Functor, fmap
from ekans.reader import Reader, const


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
