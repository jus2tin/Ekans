from dataclasses import dataclass
from typing import Callable, Generic, Iterator, List, TypeVar, Union

import pytest
from applicative_laws import assert_applicative_law
from apply_laws import assert_apply_law
from bind_laws import assert_bind_law
from functor_laws import assert_functor_laws
from hypothesis import given
from hypothesis import strategies as st
from monad_laws import assert_monad_law

from ekans.applicative import Applicative
from ekans.apply import ap
from ekans.bind import Bind, bind
from ekans.foldable import Foldable, toList
from ekans.functor import fmap
from ekans.maybe import Just, Maybe, Nothing
from ekans.monad import Monad
from ekans.monoid import Monoid
from ekans.semigroup import Semigroup, mappend

_A = TypeVar("_A")
_B = TypeVar("_B")


@dataclass(frozen=True, eq=False)
class _SemiBox(Semigroup):
    """A Semigroup that is deliberately NOT a Monoid -- concrete proof
    that Maybe.mempty only needs A: Semigroup, not A: Monoid, per the
    spec's central Semigroup-not-Monoid finding.
    """

    value: int

    def mappend(self, other: "_SemiBox") -> "_SemiBox":
        return _SemiBox(value=self.value + other.value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _SemiBox) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True, eq=False)
class _RogueMaybe(Maybe[_A], Generic[_A]):
    """A third Maybe variant, existing only to prove the `ap`/`bind`
    `case _: raise AssertionError` fallback (docs/specs/maybe.md's
    Design section) is a real safety net, not dead code -- mypy can't
    prove a match over the abstract Maybe handle is exhaustive, so
    both methods guard against exactly this kind of unrecognized
    subclass at runtime.
    """

    def fmap(self, f: Callable[[_A], _B]) -> "Just[_B]":
        raise NotImplementedError

    def ap(  # type: ignore[override]
        self, f: "Maybe[Callable[[_A], _B]]"
    ) -> "Union[Just[_B], Nothing[_B]]":
        raise NotImplementedError

    def bind(  # type: ignore[override]
        self, f: Callable[[_A], "Maybe[_B]"]
    ) -> "Union[Just[_B], Nothing[_B]]":
        raise NotImplementedError

    def __eq__(self, other: "Maybe[_A]") -> bool:  # type: ignore[override]
        return isinstance(other, _RogueMaybe)

    def __hash__(self) -> int:
        return 0

    def __iter__(self) -> "Iterator[_A]":
        raise NotImplementedError


def test_just_holds_the_value() -> None:
    assert Just(value=1).value == 1


def test_just_equal_when_values_are_equal() -> None:
    assert Just(value=1) == Just(value=1)


def test_just_not_equal_when_values_differ() -> None:
    assert Just(value=1) != Just(value=2)


def test_nothing_equal_to_nothing() -> None:
    a: Maybe[int] = Nothing()
    b: Maybe[int] = Nothing()
    assert a == b


def test_just_not_equal_to_nothing() -> None:
    just: Maybe[int] = Just(value=1)
    nothing: Maybe[int] = Nothing()
    assert just != nothing
    assert nothing != just


def test_not_equal_to_an_unrelated_type() -> None:
    assert Just(value=1) != "not a Maybe"
    assert Nothing[int]() != "not a Maybe"


def test_just_equal_values_hash_the_same() -> None:
    assert hash(Just(value=1)) == hash(Just(value=1))


def test_nothing_instances_hash_the_same() -> None:
    assert hash(Nothing[int]()) == hash(Nothing[str]())


def test_is_usable_as_a_set_member() -> None:
    assert {Just(value=1), Just(value=1), Just(value=2)} == {
        Just(value=1),
        Just(value=2),
    }


def test_just_is_immutable() -> None:
    just = Just(value=1)
    with pytest.raises(AttributeError):
        # mypy statically knows this frozen field is read-only ([misc]);
        # we're deliberately testing the runtime FrozenInstanceError it raises.
        just.value = 2  # type: ignore[misc]


def test_nothing_is_immutable() -> None:
    nothing: Maybe[int] = Nothing()
    with pytest.raises(AttributeError):
        nothing.extra = 2


def test_just_fmap_applies_the_function_to_the_wrapped_value() -> None:
    assert Just(value=1).fmap(str) == Just(value="1")


def test_free_fmap_delegates_to_the_method_for_just() -> None:
    assert fmap(str, Just(value=1)) == Just(value="1")


def test_nothing_fmap_returns_nothing_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> str:
        calls.append(a)
        return str(a)

    nothing: Maybe[int] = Nothing()
    assert nothing.fmap(f) == Nothing()
    assert calls == []


def test_free_fmap_delegates_to_the_method_for_nothing() -> None:
    nothing: Maybe[int] = Nothing()
    assert fmap(str, nothing) == Nothing()


def test_satisfies_the_functor_laws() -> None:
    assert_functor_laws(Just, st.integers())


def test_abstract_fmap_raises_if_not_overridden() -> None:
    just = Just(value=1)
    with pytest.raises(NotImplementedError):
        Maybe.fmap(just, str)


def test_point_constructs_a_just_wrapping_the_value() -> None:
    assert Maybe.point(1) == Just(value=1)


def test_point_then_fmap_chains_correctly() -> None:
    assert Maybe.point(1).fmap(str) == Just(value="1")


def test_just_ap_applies_the_wrapped_function() -> None:
    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=str)
    assert Just(value=5).ap(wrapped_fn) == Just(value="5")


def test_just_ap_with_nothing_function_returns_nothing() -> None:
    wrapped_fn: Maybe[Callable[[int], str]] = Nothing()
    assert Just(value=5).ap(wrapped_fn) == Nothing()


def test_nothing_ap_returns_nothing_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> str:
        calls.append(a)
        return str(a)

    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=f)
    nothing: Maybe[int] = Nothing()
    assert nothing.ap(wrapped_fn) == Nothing()
    assert calls == []


def test_free_ap_delegates_to_the_method() -> None:
    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=str)
    assert ap(wrapped_fn, Just(value=5)) == Just(value="5")


def test_satisfies_the_apply_law() -> None:
    assert_apply_law(Just, st.integers())


def test_abstract_ap_raises_if_not_overridden() -> None:
    just = Just(value=1)
    wrapped_fn: Maybe[Callable[[int], str]] = Just(value=str)
    with pytest.raises(NotImplementedError):
        Maybe.ap(just, wrapped_fn)


def test_just_ap_raises_for_an_unrecognized_maybe_subclass() -> None:
    rogue: Maybe[Callable[[int], str]] = _RogueMaybe()
    with pytest.raises(AssertionError):
        Just(value=1).ap(rogue)


def test_is_an_applicative() -> None:
    assert isinstance(Just(value=1), Applicative)
    nothing: Maybe[int] = Nothing()
    assert isinstance(nothing, Applicative)


def test_satisfies_the_applicative_laws() -> None:
    assert_applicative_law(Maybe.point, st.integers())


def test_just_bind_applies_f_and_flattens() -> None:
    assert Just(value=5).bind(lambda a: Just(value=str(a))) == Just(value="5")


def test_just_bind_with_f_returning_nothing() -> None:
    def f(a: int) -> "Maybe[str]":
        return Nothing()

    assert Just(value=5).bind(f) == Nothing()


def test_nothing_bind_returns_nothing_and_never_calls_f() -> None:
    calls: List[int] = []

    def f(a: int) -> "Maybe[str]":
        calls.append(a)
        return Just(value=str(a))

    nothing: Maybe[int] = Nothing()
    assert nothing.bind(f) == Nothing()
    assert calls == []


def test_free_bind_delegates_to_the_method() -> None:
    assert bind(lambda a: Just(value=str(a)), Just(value=5)) == Just(value="5")


def test_is_a_bind() -> None:
    assert isinstance(Just(value=5), Bind)
    nothing: Maybe[int] = Nothing()
    assert isinstance(nothing, Bind)


def test_satisfies_the_bind_law() -> None:
    assert_bind_law(Just, st.integers())


def test_abstract_bind_raises_if_not_overridden() -> None:
    just = Just(value=1)
    with pytest.raises(NotImplementedError):
        Maybe.bind(just, lambda a: Just(value=a))


def test_just_bind_raises_for_an_unrecognized_maybe_subclass() -> None:
    def f(a: int) -> "Maybe[str]":
        return _RogueMaybe()

    with pytest.raises(AssertionError):
        Just(value=1).bind(f)


def test_is_a_monad() -> None:
    assert isinstance(Just(value=1), Monad)
    nothing: Maybe[int] = Nothing()
    assert isinstance(nothing, Monad)


def test_satisfies_the_monad_law() -> None:
    assert_monad_law(Maybe.point, st.integers())


def _describe(m: "Union[Just[int], Nothing[int]]") -> str:
    # No fallback `case _:` -- this is only exhaustive, and therefore
    # only type-checks under `mypy --strict`, because `m` is typed as
    # the Union of both variants rather than the abstract Maybe[int].
    match m:
        case Just(value=v):
            return f"got {v}"
        case Nothing():
            return "nothing"


def test_match_case_is_exhaustive_over_just() -> None:
    assert _describe(Just(value=5)) == "got 5"


def test_match_case_is_exhaustive_over_nothing() -> None:
    assert _describe(Nothing()) == "nothing"


@given(st.integers())
def test_match_case_narrows_justs_value_precisely(value: int) -> None:
    assert _describe(Just(value=value)) == f"got {value}"


def test_mappend_combines_two_justs_semigroup_values() -> None:
    a: Maybe[_SemiBox] = Just(value=_SemiBox(value=1))
    b: Maybe[_SemiBox] = Just(value=_SemiBox(value=2))
    assert mappend(a, b) == Just(value=_SemiBox(value=3))


def test_mappend_nothing_is_the_left_identity() -> None:
    x: Maybe[_SemiBox] = Just(value=_SemiBox(value=5))
    nothing: Maybe[_SemiBox] = Nothing()
    assert mappend(nothing, x) == x


def test_mappend_nothing_is_the_right_identity() -> None:
    x: Maybe[_SemiBox] = Just(value=_SemiBox(value=5))
    nothing: Maybe[_SemiBox] = Nothing()
    assert mappend(x, nothing) == x


def test_mappend_both_nothing_is_nothing() -> None:
    a: Maybe[_SemiBox] = Nothing()
    b: Maybe[_SemiBox] = Nothing()
    assert mappend(a, b) == Nothing()


@given(st.integers(), st.integers(), st.integers())
def test_free_mappend_is_associative(a: int, b: int, c: int) -> None:
    # Maybe doesn't nominally implement Semigroup (same non-nominal
    # reasoning as Identity/Const/Reader's own conditional support),
    # so assert_semigroup_law (which assumes a `.mappend()` method)
    # doesn't apply here -- testing the law directly against the free
    # function instead, same pattern test_identity.py/test_const.py use.
    x: Maybe[_SemiBox] = Just(value=_SemiBox(value=a))
    y: Maybe[_SemiBox] = Just(value=_SemiBox(value=b))
    z: Maybe[_SemiBox] = Just(value=_SemiBox(value=c))
    assert mappend(mappend(x, y), z) == mappend(x, mappend(y, z))


def test_mempty_constructs_nothing_for_a_semigroup_type() -> None:
    # _SemiBox is a Semigroup but deliberately NOT a Monoid -- the
    # concrete verification of the spec's central claim that
    # Maybe.mempty only needs A: Semigroup, not A: Monoid.
    assert Maybe.mempty(_SemiBox) == Nothing()


def test_is_not_a_monoid() -> None:
    # Maybe can't nominally inherit Monoid -- same non-nominal
    # reasoning as its conditional Semigroup support.
    assert not isinstance(Just(value=1), Monoid)
    assert not isinstance(Nothing(), Monoid)


def test_mempty_is_the_left_identity() -> None:
    x: Maybe[_SemiBox] = Just(value=_SemiBox(value=5))
    assert mappend(Maybe.mempty(_SemiBox), x) == x


def test_mempty_is_the_right_identity() -> None:
    x: Maybe[_SemiBox] = Just(value=_SemiBox(value=5))
    assert mappend(x, Maybe.mempty(_SemiBox)) == x


def test_free_mappend_raises_for_an_unrecognized_maybe_subclass() -> None:
    just: Maybe[_SemiBox] = Just(value=_SemiBox(value=1))
    rogue: Maybe[_SemiBox] = _RogueMaybe()
    with pytest.raises(AssertionError):
        mappend(just, rogue)


def test_just_is_a_foldable() -> None:
    assert isinstance(Just(value=1), Foldable)


def test_nothing_is_a_foldable() -> None:
    assert isinstance(Nothing(), Foldable)


def test_just_iterates_the_wrapped_value() -> None:
    assert toList(Just(value=1)) == [1]


def test_nothing_iterates_nothing() -> None:
    just_or_nothing: Maybe[int] = Nothing()
    assert toList(just_or_nothing) == []


@given(st.integers())
def test_just_functor_foldable_coherence(value: int) -> None:
    # toList(fmap(f, xs)) == [f(y) for y in toList(xs)] -- see
    # docs/specs/foldable.md's retrofit Cross-Product audit.
    f = str
    box: Maybe[int] = Just(value=value)
    assert toList(box.fmap(f)) == [f(y) for y in toList(box)]


def test_nothing_functor_foldable_coherence() -> None:
    f = str
    box: Maybe[int] = Nothing()
    assert toList(box.fmap(f)) == [f(y) for y in toList(box)]


@given(st.integers())
def test_pointed_foldable_coherence(value: int) -> None:
    # toList(point(x)) == [x] -- same section; Maybe.point always
    # produces a Just.
    assert toList(Maybe.point(value)) == [value]


def test_abstract_iter_raises_if_not_overridden() -> None:
    just = Just(value=1)
    with pytest.raises(NotImplementedError):
        Maybe.__iter__(just)
