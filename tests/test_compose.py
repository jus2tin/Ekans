from itertools import product
from typing import Any, Callable, List, Tuple

import pytest
from functor_laws import assert_functor_laws
from hypothesis import strategies as st

from ekans.compose import Compose
from ekans.const import Const
from ekans.either import Right
from ekans.foldable import Foldable, toList
from ekans.functor import fmap
from ekans.identity import Identity
from ekans.maybe import Just, Nothing
from ekans.tuple2 import Tuple2


def test_holds_the_value() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert c.value == Just(value=Identity(value=1))


def test_fmap_maps_through_both_layers() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert c.fmap(str) == Compose(value=Just(value=Identity(value="1")))


def test_fmap_on_an_empty_outer_layer_touches_nothing() -> None:
    c: Compose[Nothing[Identity[int]], int] = Compose(value=Nothing())
    assert c.fmap(str) == Compose(value=Nothing())


def test_free_fmap_delegates_to_the_method() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert fmap(str, c) == Compose(value=Just(value=Identity(value="1")))


def test_equal_when_values_are_equal() -> None:
    a: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    b: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert a == b


def test_not_equal_when_values_differ() -> None:
    a: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    b: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=2)))
    assert a != b


def test_not_equal_to_an_unrelated_type() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert c != "not a Compose"


def test_equal_values_hash_the_same() -> None:
    a: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    b: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert hash(a) == hash(b)


def test_is_immutable() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        c.value = Just(value=Identity(value=2))  # type: ignore[misc]


def test_is_a_foldable() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=1)))
    assert isinstance(c, Foldable)


def test_iterates_the_innermost_value_flattening_both_layers() -> None:
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=5)))
    assert toList(c) == [5]


def test_iterates_nothing_when_the_outer_layer_is_empty() -> None:
    c: Compose[Nothing[Identity[int]], int] = Compose(value=Nothing())
    assert toList(c) == []


def test_functor_foldable_coherence() -> None:
    # toList(fmap(f, xs)) == [f(y) for y in toList(xs)] -- spot-checked
    # per the spec's note that this isn't a formal Cross-Product law
    # (Functor and Foldable aren't superclasses of each other in
    # Haskell's own hierarchy either), but it's still a real property
    # worth confirming for this instance.
    c: Compose[Just[Identity[int]], int] = Compose(value=Just(value=Identity(value=5)))
    assert toList(c.fmap(str)) == [str(y) for y in toList(c)]


def _wrap_identity(x: Any) -> Any:
    return Identity(value=x)


def _wrap_const(x: Any) -> Any:
    return Const(value="const-fixed")


def _wrap_maybe(x: Any) -> Any:
    return Just(value=x)


def _wrap_either(x: Any) -> Any:
    return Right(value=x)


def _wrap_tuple2(x: Any) -> Any:
    return Tuple2(first="h", second=x)


_WRAPS: List[Tuple[str, Callable[[Any], Any]]] = [
    ("Identity", _wrap_identity),
    ("Const", _wrap_const),
    ("Maybe", _wrap_maybe),
    ("Either", _wrap_either),
    ("Tuple2", _wrap_tuple2),
]

_PAIRS = list(product(_WRAPS, _WRAPS))


def _make(
    outer_wrap: Callable[[Any], Any], inner_wrap: Callable[[Any], Any]
) -> Callable[[Any], "Compose[Any, Any]"]:
    return lambda a: Compose(value=outer_wrap(inner_wrap(a)))


@pytest.mark.parametrize(
    "outer_name,outer_wrap,inner_name,inner_wrap",
    [
        (outer_name, outer_wrap, inner_name, inner_wrap)
        for (outer_name, outer_wrap), (inner_name, inner_wrap) in _PAIRS
    ],
    ids=[f"{o}-over-{i}" for (o, _), (i, _) in _PAIRS],
)
def test_all_25_pairs_satisfy_the_functor_laws(
    outer_name: str,
    outer_wrap: Callable[[Any], Any],
    inner_name: str,
    inner_wrap: Callable[[Any], Any],
) -> None:
    assert_functor_laws(_make(outer_wrap, inner_wrap), st.integers())


@pytest.mark.parametrize(
    "outer_name,outer_wrap,inner_name,inner_wrap",
    [
        (outer_name, outer_wrap, inner_name, inner_wrap)
        for (outer_name, outer_wrap), (inner_name, inner_wrap) in _PAIRS
    ],
    ids=[f"{o}-over-{i}" for (o, _), (i, _) in _PAIRS],
)
def test_all_25_pairs_functor_foldable_coherence(
    outer_name: str,
    outer_wrap: Callable[[Any], Any],
    inner_name: str,
    inner_wrap: Callable[[Any], Any],
) -> None:
    # toList(fmap(f, xs)) == [f(y) for y in toList(xs)] -- spot-checked
    # for every pair, same non-formal-law reasoning as
    # test_functor_foldable_coherence above.
    x = _make(outer_wrap, inner_wrap)(5)
    assert toList(fmap(str, x)) == [str(y) for y in toList(x)]


@pytest.mark.parametrize(
    "outer_name,outer_wrap,inner_name,inner_wrap",
    [
        (outer_name, outer_wrap, inner_name, inner_wrap)
        for (outer_name, outer_wrap), (inner_name, inner_wrap) in _PAIRS
    ],
    ids=[f"{o}-over-{i}" for (o, _), (i, _) in _PAIRS],
)
def test_all_25_pairs_toList_matches_expected_flattening(
    outer_name: str,
    outer_wrap: Callable[[Any], Any],
    inner_name: str,
    inner_wrap: Callable[[Any], Any],
) -> None:
    # Const, at either layer, iterates zero (it folds over its phantom
    # B, never actually held); every other pairing flattens to exactly
    # the one wrapped value.
    x = _make(outer_wrap, inner_wrap)(5)
    expected = [] if "Const" in (outer_name, inner_name) else [5]
    assert toList(x) == expected
