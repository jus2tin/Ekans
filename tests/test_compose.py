import pytest

from ekans.compose import Compose
from ekans.foldable import Foldable, toList
from ekans.functor import fmap
from ekans.identity import Identity
from ekans.maybe import Just, Nothing


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
